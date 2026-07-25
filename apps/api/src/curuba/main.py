"""App de FastAPI: el webhook de Twilio y el healthcheck.

Las tres trampas de este archivo están comentadas donde ocurren.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from anyio import to_thread
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from curuba import agent, db, demo
from curuba.config import settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("curuba")


@asynccontextmanager
async def _ciclo(_: FastAPI) -> AsyncIterator[None]:
    try:
        await db.abrir()
        await db.aplicar_esquema()  # idempotente: el deploy se auto-migra
    except Exception:
        # El arranque TIENE que morir acá — es lo que hace que el healthcheck
        # grite en vez de descubrirlo en la primera query. Pero el traceback de
        # asyncpg no nombra ni una variable de entorno, así que dejamos una
        # línea legible antes de que se vaya.
        log.exception("no se pudo abrir Postgres — revisar DATABASE_URL y las extensiones")
        raise
    log.info("pool de Postgres abierto y esquema aplicado")

    # Sin PUBLIC_BASE_URL el servicio arranca perfecto y falla mucho más tarde, de la
    # peor forma posible: el PDF se genera, se guarda, y el mensaje sale SIN adjunto
    # porque no hay con qué armar el enlace. La tool le devuelve al modelo un texto en
    # vez de una URL y el modelo termina diciéndole al paciente que hubo un "problema
    # técnico" — después de una entrevista de doce preguntas. Nada en los logs dice por
    # qué. Esta línea es la que convierte ese misterio en un renglón.
    if not settings.public_base_url:
        log.warning(
            "FALTA PUBLIC_BASE_URL — los PDF se van a generar pero NO se van a poder "
            "adjuntar en WhatsApp. En Railway ponla como https://${{RAILWAY_PUBLIC_DOMAIN}}"
        )

    yield
    # Antes de cerrar el pool: los streams del panel viven en un `while` y uvicorn espera
    # a que las respuestas en vuelo terminen. Sin esto, apagar se queda colgado.
    demo.cerrar_streams()
    await db.cerrar()


app = FastAPI(title="Curuba API", lifespan=_ciclo)

# El panel de /demo corre en otro dominio (el servicio `curuba-web`), así que sin esto el
# EventSource del navegador no puede ni conectarse. Abierto a todos los orígenes a
# propósito: los únicos GET son `/health`, `/f/{id}` —que ya es público porque Twilio lo
# descarga— y `/demo/eventos`, que solo entrega la conversación de CURUBA_DEMO_WA. Los
# webhooks son POST de Twilio y no los llama un navegador.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # Con `*` en los orígenes esto TIENE que quedar en False o el navegador rechaza la
    # respuesta entera. No hay cookies ni sesión que mandar de todas formas.
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

_validador = RequestValidator(settings.twilio_auth_token)

# El cliente se construye tarde: Client("", "") revienta al instanciarse, y eso
# tumbaría el arranque de toda la app cuando solo quieres probar el agente.
_twilio: Client | None = None


def _cliente() -> Client:
    global _twilio
    if _twilio is None:
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            raise RuntimeError(
                "Faltan TWILIO_ACCOUNT_SID y/o TWILIO_AUTH_TOKEN en el entorno"
            )
        _twilio = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    return _twilio

# Trampa 3: Twilio rechaza cuerpos de WhatsApp de más de 1600 caracteres
# (error 21617) y al usuario no le llega NADA. Una respuesta de LLM los pasa
# sin esfuerzo. Cortamos con margen.
LIMITE_WHATSAPP = 1500

# Con `media_url` el body deja de ser un mensaje de texto y pasa a ser el CAPTION del
# adjunto, cuyo tope es bastante más corto (~1024). Y es justo el mensaje que más se
# alarga: el que le lee los marcadores del PDF. Con el corte de 1500 pasaba el filtro
# nuestro y lo rechazaba WhatsApp — con el documento adentro.
LIMITE_CAPTION = 900


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


# Para ponerle extensión al archivo que descarga el usuario. Si el mime no está
# acá cae a `.bin`, que es fea pero honesta.
EXTENSIONES = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


@app.get("/f/{doc_id}")
async def documento(doc_id: str) -> Response:
    """Sirve un archivo generado: los cuatro escritos, y las fotos del panel.

    **Tiene que ser público.** Twilio descarga esta URL desde sus servidores para
    adjuntar el archivo al mensaje de WhatsApp: si pide autenticación, al usuario le
    llega el texto sin el documento. El id es un UUID aleatorio y esa es toda la
    protección que tiene — es un enlace no adivinable, no un recurso privado.
    """
    fila = await db.leer_documento(doc_id)
    if fila is None:
        raise HTTPException(status_code=404, detail="documento no encontrado")
    # Las filas de antes de la columna `mime` son todas PDF.
    mime = fila["mime"] or "application/pdf"
    nombre = f"curuba-{fila['tipo'] or 'documento'}.{EXTENSIONES.get(mime, 'bin')}"
    return Response(
        content=bytes(fila["contenido"]),
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{nombre}"'},
    )


@app.get("/demo/eventos")
async def demo_eventos() -> StreamingResponse:
    """El stream que pinta el panel de /demo: el estado y después la corrida en vivo.

    Solo entrega la conversación de `CURUBA_DEMO_WA`; sin esa variable no entrega nada de
    nadie. El filtro no está acá sino en `demo.emitir()`, que es lo que garantiza que la
    conversación de otro paciente no llegue ni a existir como evento.
    """
    return StreamingResponse(
        demo.eventos(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Sin esto un proxy con buffering se guarda los eventos y los suelta de a
            # bloques: el panel se congela y salta en vez de ir en vivo.
            "X-Accel-Buffering": "no",
        },
    )


def _url_publica(request: Request) -> str:
    """La URL tal como Twilio la firmó.

    Trampa 2: detrás del proxy de Railway el esquema llega como `http`, pero
    Twilio firmó la URL `https`. Sin esta corrección la firma falla en TODOS
    los mensajes y el webhook responde 403 sin decir por qué.
    """
    url = str(request.url)
    if url.startswith("http://"):
        url = "https://" + url[len("http://") :]
    return url


def _alcanzable(url: str) -> bool:
    """Si Twilio puede llegarle a esa URL desde sus servidores.

    En local `PUBLIC_BASE_URL` apunta a localhost —hace falta para que las fotos del panel
    de /demo tengan URL—, y Twilio rechaza el mensaje COMPLETO con un 400 21609 ("The
    StatusCallback URL is not a valid URL") en cuanto se lo manda. O sea: poner esa
    variable en local rompía todos los envíos, incluidos los que no llevan adjunto.
    """
    return url.startswith("https://") and "localhost" not in url and "127.0.0.1" not in url


def _enviar(a: str, texto: str, adjunto: str | None = None) -> None:
    """Manda el mensaje por la API REST. Bloqueante — se llama en un thread.

    `adjunto` es la URL de un PDF generado. Twilio la descarga de nuestra propia API
    para adjuntarla, y por eso `GET /f/{id}` no puede pedir autenticación.
    """
    limite = LIMITE_CAPTION if adjunto else LIMITE_WHATSAPP
    if len(texto) > limite:
        texto = texto[: limite - 1] + "…"

    extra: dict[str, Any] = {"media_url": [adjunto]} if adjunto else {}
    if _alcanzable(settings.public_base_url):
        # Twilio contesta 201 `queued` y SOLO DESPUÉS intenta bajar el adjunto. Si eso
        # falla (11200 no pudo traer la URL, 12300 content-type raro, 21620 URL
        # inválida, 63005/63021 de WhatsApp) el error llega minutos más tarde, fuera
        # del `try` de `_procesar`: no lanza excepción, no dispara el reintento y no
        # deja ni una línea en los logs. Sin este callback, un PDF que no llegó es
        # indistinguible de uno que sí.
        extra["status_callback"] = (
            f"{settings.public_base_url.rstrip('/')}/webhooks/twilio/status"
        )

    _cliente().messages.create(
        from_=settings.twilio_whatsapp_from, to=a, body=texto, **extra
    )


# WhatsApp deja mandar hasta 16 MB, y eso se vuelve un data URI de ~21 MB en el
# request a OpenRouter. Una foto de fórmula legible no pasa de 2-3 MB.
LIMITE_FOTO = 5 * 1024 * 1024


async def _descargar_media(url: str) -> bytes | None:
    """Baja un adjunto de la API de Twilio. Devuelve None si no se pudo.

    La URL de media pide Basic auth con el Account SID y el Auth Token, y además
    redirige (307) a un CDN firmado. `follow_redirects=True` es obligatorio.

    Y hay una sutileza que ahorra una hora: httpx QUITA el header `Authorization`
    cuando el redirect cambia de host, que es justo lo que se necesita — el destino
    firmado rechaza un `Authorization` de más con un 403 que no explica nada. Un
    cliente que reenvíe el header falla acá y parece un problema de credenciales.
    """
    try:
        async with httpx.AsyncClient(
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            follow_redirects=True,
            timeout=30.0,
        ) as cx:
            r = await cx.get(url)
            r.raise_for_status()
    except Exception:
        log.exception("no se pudo descargar el adjunto %s", url)
        return None

    if len(r.content) > LIMITE_FOTO:
        log.warning("adjunto de %d bytes, por encima del límite", len(r.content))
        return None
    return r.content


async def _procesar(
    wa_id: str, texto: str, media_url: str = "", media_tipo: str = ""
) -> None:
    """Corre el agente y manda la respuesta. Vive fuera del ciclo del webhook."""
    adjunto = None
    imagen = None
    foto = None  # la URL de la foto, solo para el panel de /demo
    try:
        if media_url:
            if not media_tipo.startswith("image/"):
                # PDF, audio, sticker, contacto... El modelo solo lee imágenes, y
                # decirlo de una es mejor que intentarlo y fallar raro.
                await to_thread.run_sync(
                    _enviar, wa_id,
                    "Por ahora solo puedo leer fotos. Tómale una foto a la fórmula o a "
                    "la caja del medicamento y me la mandas 🙂",
                )
                return
            imagen = await _descargar_media(media_url)
            if imagen is None:
                await to_thread.run_sync(
                    _enviar, wa_id,
                    "No pude abrir esa foto. ¿Me la reenvías, o me escribes los "
                    "medicamentos que dice la fórmula?",
                )
                return
            # Solo para el número del panel, y solo para poder mostrarla: el historial
            # sigue guardándose sin la imagen (agent._sin_fotos).
            foto = await demo.guardar_foto(wa_id, imagen, media_tipo or "image/jpeg")

        demo.emitir(wa_id, "usuario", texto=texto, foto=foto)

        if texto.strip().lower() == "reiniciar":
            await agent.reiniciar(wa_id)
            demo.emitir(wa_id, "reiniciar")
            respuesta = "Listo, borré nuestra conversación. Empecemos de nuevo 🙂"
        else:
            respuesta, adjunto = await agent.responder(
                wa_id, texto, imagen=imagen, media_type=media_tipo
            )
    except Exception:
        # Un background task que revienta en silencio se ve idéntico a un
        # webhook colgado. Mejor loguear y avisarle al usuario.
        log.exception("falló procesando el mensaje de %s", wa_id)
        respuesta = "Uy, algo se me dañó procesando tu mensaje. ¿Lo intentas otra vez?"

    # ANTES de mandar, no después: así el panel queda completo aunque `_enviar` falle —
    # que en local es lo normal, porque Meta rechaza con el error 63016 si el número no le
    # escribió al sender en las últimas 24 h. Y esta es la burbuja definitiva: reemplaza
    # lo que el panel fue escribiendo con los deltas del modelo.
    demo.emitir(wa_id, "agente", texto=respuesta, adjunto=adjunto)

    try:
        # El cliente de Twilio es bloqueante: llamarlo directo aquí congela el
        # event loop mientras dura el request HTTP.
        await to_thread.run_sync(_enviar, wa_id, respuesta, adjunto)
    except Exception:
        log.exception("falló enviando la respuesta a %s", wa_id)
        if adjunto:
            # Si lo que falló fue el adjunto, el texto solo casi siempre sí pasa —
            # y quedarse callado después de una entrevista de diez preguntas es lo
            # peor que puede hacer.
            try:
                await to_thread.run_sync(
                    _enviar, wa_id, f"{respuesta}\n\nTu documento: {adjunto}"
                )
            except Exception:
                log.exception("falló también el reintento sin adjunto a %s", wa_id)


@app.post("/webhooks/twilio/whatsapp")
async def whatsapp(
    request: Request,
    bg: BackgroundTasks,
    From: str = Form(...),
    Body: str = Form(""),
    # Los adjuntos. `Body` llega VACÍO cuando la foto va sola, así que nada de
    # cortar temprano por texto vacío.
    NumMedia: str = Form("0"),
    MediaUrl0: str = Form(""),
    MediaContentType0: str = Form(""),
) -> Response:
    if settings.validate_twilio_signature:
        firma = request.headers.get("X-Twilio-Signature", "")
        # Starlette cachea el form, así que volver a pedirlo no cuesta nada. Y ojo:
        # esto relee el form COMPLETO, así que los campos de media entran solos al
        # cálculo de la firma. Si algún día se listan a mano, agregar un adjunto
        # rompe la validación de todos los mensajes con foto.
        campos = {k: v for k, v in (await request.form()).items() if isinstance(v, str)}
        if not _validador.validate(_url_publica(request), campos, firma):
            log.warning("firma de Twilio inválida para %s", From)
            raise HTTPException(status_code=403, detail="firma inválida")

    # Trampa 1: Twilio corta el webhook a los ~15s y una corrida del agente se
    # demora más. Respondemos 200 con TwiML vacío YA; el agente corre en
    # `_procesar` después de que esta respuesta salió, y la respuesta real se
    # manda aparte por la API REST. Si esto se rompe, Twilio reintenta en
    # silencio y al usuario le llegan mensajes duplicados.
    try:
        con_media = int(NumMedia or 0) > 0
    except ValueError:
        con_media = False

    bg.add_task(
        _procesar,
        From,
        Body,
        MediaUrl0 if con_media else "",
        MediaContentType0 if con_media else "",
    )
    return Response(content="<Response></Response>", media_type="application/xml")


@app.post("/webhooks/twilio/status")
async def estado(
    request: Request,
    MessageSid: str = Form(""),
    MessageStatus: str = Form(""),
    ErrorCode: str = Form(""),
) -> Response:
    """Cómo terminó cada mensaje que mandamos. Lo llama Twilio, no el usuario.

    Es el par de `status_callback` en `_enviar`, y existe para cerrar el único modo
    de falla que no se veía: el adjunto que Twilio acepta con un 201 y no logra
    descargar después. Acá no se reintenta nada — se deja el renglón que convierte
    ese silencio en algo que se puede buscar en los logs.
    """
    if settings.validate_twilio_signature:
        firma = request.headers.get("X-Twilio-Signature", "")
        campos = {k: v for k, v in (await request.form()).items() if isinstance(v, str)}
        if not _validador.validate(_url_publica(request), campos, firma):
            log.warning("firma inválida en el status callback de %s", MessageSid)
            raise HTTPException(status_code=403, detail="firma inválida")

    if MessageStatus in ("failed", "undelivered"):
        log.error(
            "mensaje %s quedó en '%s' (ErrorCode=%s). 11200/12300/21620 significan que "
            "Twilio NO pudo bajar el PDF de /f/{id}: revisar PUBLIC_BASE_URL y que ese "
            "endpoint responda 200 application/pdf sin pedir autenticación",
            MessageSid,
            MessageStatus,
            ErrorCode or "ninguno",
        )
    else:
        log.info("mensaje %s: %s", MessageSid, MessageStatus)

    return Response(status_code=204)
