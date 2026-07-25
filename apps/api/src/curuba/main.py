"""App de FastAPI: el webhook de Twilio y el healthcheck.

Las tres trampas de este archivo están comentadas donde ocurren.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from anyio import to_thread
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request, Response
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from curuba import agent, db
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
    await db.cerrar()


app = FastAPI(title="Curuba API", lifespan=_ciclo)

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


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/f/{doc_id}")
async def documento(doc_id: str) -> Response:
    """Sirve un PDF generado.

    **Tiene que ser público.** Twilio descarga esta URL desde sus servidores para
    adjuntar el archivo al mensaje de WhatsApp: si pide autenticación, al usuario le
    llega el texto sin el documento. El id es un UUID aleatorio y esa es toda la
    protección que tiene — es un enlace no adivinable, no un recurso privado.
    """
    fila = await db.leer_documento(doc_id)
    if fila is None:
        raise HTTPException(status_code=404, detail="documento no encontrado")
    nombre = f"curuba-{fila['tipo'] or 'documento'}.pdf"
    return Response(
        content=bytes(fila["contenido"]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nombre}"'},
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


def _enviar(a: str, texto: str, adjunto: str | None = None) -> None:
    """Manda el mensaje por la API REST. Bloqueante — se llama en un thread.

    `adjunto` es la URL de un PDF generado. Twilio la descarga de nuestra propia API
    para adjuntarla, y por eso `GET /f/{id}` no puede pedir autenticación.
    """
    if len(texto) > LIMITE_WHATSAPP:
        texto = texto[: LIMITE_WHATSAPP - 1] + "…"
    extra = {"media_url": [adjunto]} if adjunto else {}
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
    try:
        if media_url:
            if not media_tipo.startswith("image/"):
                # PDF, audio, sticker, contacto... El modelo solo lee imágenes, y
                # decirlo de una es mejor que intentarlo y fallar raro.
                await to_thread.run_sync(
                    _enviar, wa_id,
                    "Por ahora solo puedo leer fotos. Tómale una foto a la fórmula y "
                    "me la mandas 🙂",
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

        if texto.strip().lower() == "reiniciar":
            await agent.reiniciar(wa_id)
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
