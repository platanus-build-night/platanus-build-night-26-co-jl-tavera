"""App de FastAPI: el webhook de Twilio y el healthcheck.

Las tres trampas de este archivo están comentadas donde ocurren.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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


def _enviar(a: str, texto: str) -> None:
    """Manda el mensaje por la API REST. Bloqueante — se llama en un thread."""
    if len(texto) > LIMITE_WHATSAPP:
        texto = texto[: LIMITE_WHATSAPP - 1] + "…"
    _cliente().messages.create(from_=settings.twilio_whatsapp_from, to=a, body=texto)


async def _procesar(wa_id: str, texto: str) -> None:
    """Corre el agente y manda la respuesta. Vive fuera del ciclo del webhook."""
    try:
        if texto.strip().lower() == "reiniciar":
            await agent.reiniciar(wa_id)
            respuesta = "Listo, borré nuestra conversación. Empecemos de nuevo 🙂"
        else:
            respuesta = await agent.responder(wa_id, texto)
    except Exception:
        # Un background task que revienta en silencio se ve idéntico a un
        # webhook colgado. Mejor loguear y avisarle al usuario.
        log.exception("falló procesando el mensaje de %s", wa_id)
        respuesta = "Uy, algo se me dañó procesando tu mensaje. ¿Lo intentas otra vez?"

    try:
        # El cliente de Twilio es bloqueante: llamarlo directo aquí congela el
        # event loop mientras dura el request HTTP.
        await to_thread.run_sync(_enviar, wa_id, respuesta)
    except Exception:
        log.exception("falló enviando la respuesta a %s", wa_id)


@app.post("/webhooks/twilio/whatsapp")
async def whatsapp(
    request: Request,
    bg: BackgroundTasks,
    From: str = Form(...),
    Body: str = Form(""),
) -> Response:
    if settings.validate_twilio_signature:
        firma = request.headers.get("X-Twilio-Signature", "")
        # Starlette cachea el form, así que volver a pedirlo no cuesta nada.
        campos = {k: v for k, v in (await request.form()).items() if isinstance(v, str)}
        if not _validador.validate(_url_publica(request), campos, firma):
            log.warning("firma de Twilio inválida para %s", From)
            raise HTTPException(status_code=403, detail="firma inválida")

    # Trampa 1: Twilio corta el webhook a los ~15s y una corrida del agente se
    # demora más. Respondemos 200 con TwiML vacío YA; el agente corre en
    # `_procesar` después de que esta respuesta salió, y la respuesta real se
    # manda aparte por la API REST. Si esto se rompe, Twilio reintenta en
    # silencio y al usuario le llegan mensajes duplicados.
    bg.add_task(_procesar, From, Body)
    return Response(content="<Response></Response>", media_type="application/xml")
