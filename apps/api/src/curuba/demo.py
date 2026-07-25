"""El panel de /demo: el bus de eventos de la corrida y el stream SSE.

Cuelga tres cosas del camino que ya funciona —el webhook, la corrida del agente y la
tabla `documents`— y las convierte en un stream que el navegador puede pintar. No hay
tabla nueva: los eventos son efímeros, y lo que sobrevive una recarga se reconstruye de
`conversations.messages`, que ya se guardaba.

**La regla de este archivo: nada de acá puede romper una respuesta de WhatsApp.**
`emitir()` no bloquea nunca y no levanta nunca; `manejador_eventos()` se traga sus
propios errores. Un panel caído tiene que verse como un panel caído, no como un paciente
sin respuesta.

La allowlist es de UN número (`CURUBA_DEMO_WA`) y el filtro va en el emisor, no en el
cliente: así la conversación de otro paciente no entra al bus, no sale por el SSE, y no
le queda la foto de su fórmula guardada en la base.

El bus vive en memoria del proceso. Con un solo uvicorn —lo que hay en `railway.json`—
alcanza; con dos réplicas los eventos solo llegarían a los clientes conectados a la
misma instancia que atendió el webhook.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

from pydantic_ai import ModelMessagesTypeAdapter, RunContext
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    RetryPromptPart,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ThinkingPartDelta,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from curuba import db, legal
from curuba.config import settings
from curuba.tools import Deps

log = logging.getLogger("curuba.demo")

# El texto con el que `agent._sin_fotos` reemplaza la imagen antes de guardar el
# historial. Es la única señal de que en ese turno hubo una foto, así que es lo que
# usamos para saber a qué burbuja pegarle la URL.
MARCA_FOTO = "[foto de fórmula médica, ya leída]"

# Cuánto de los argumentos y del resultado de cada tool se manda al panel. Se muestran
# en mono al lado del nodo: más de esto no cabe y menos no dice nada.
LIMITE_ARGS = 160
LIMITE_RESULTADO = 420

# Si un cliente no alcanza a drenar, se descartan eventos en vez de frenar la corrida.
# Con los deltas de texto esto se llena rápido si el navegador está en otra pestaña.
TOPE_COLA = 2000

# Sin tráfico, el proxy de Railway corta una conexión SSE inactiva. Un comentario
# cada 15 s la mantiene viva y no le llega nada al `onmessage` del cliente.
LATIDO = 15.0

# Cada stream se corta solo a los 5 minutos y el navegador reconecta (`EventSource` lo hace
# sin que nadie se lo pida, y el primer evento de la conexión nueva es el estado completo,
# así que no se pierde nada). Es a propósito: un SSE que no termina nunca deja conexiones
# zombis y hace que el shutdown se quede esperándolas.
VIDA = 300.0

# Lo que se le mete a la cola para que un stream se vaya. Un str porque la cola es de str;
# el \x00 garantiza que no choca con un evento de verdad.
_FIN = "\x00fin"


def normalizar(valor: str) -> str:
    """El `wa_id` tal como lo escribe el webhook, a partir de lo que sea que pusieron.

    Twilio manda `From=whatsapp:+573001234567`, pero en Railway uno teclea el número
    pelado. Un valor que no es numérico se devuelve intacto para que
    `CURUBA_DEMO_WA=local` sirva con el wa_id del REPL.
    """
    v = valor.strip()
    if not v or v.startswith("whatsapp:"):
        return v

    crudo = v.replace(" ", "").replace("-", "")
    if not crudo.lstrip("+").isdigit():
        return v

    if not crudo.startswith("+"):
        # 10 dígitos es un celular colombiano sin indicativo; más que eso ya lo trae.
        crudo = "+57" + crudo if len(crudo) == 10 else "+" + crudo
    return f"whatsapp:{crudo}"


_DEMO = normalizar(settings.curuba_demo_wa)

# Una cola por cliente conectado.
_suscriptores: set[asyncio.Queue[str]] = set()


def es_demo(wa_id: str) -> bool:
    return bool(_DEMO) and wa_id == _DEMO


def _bonito(wa_id: str) -> str:
    """`whatsapp:+573001234567` → `+57 300 123 4567`, para el encabezado del chat."""
    n = wa_id.removeprefix("whatsapp:")
    if n.startswith("+57") and len(n) == 13:
        return f"+57 {n[3:6]} {n[6:9]} {n[9:]}"
    return n


def _compacto(valor: Any, limite: int) -> str:
    """Cualquier cosa a una línea de JSON cortada. Nunca levanta."""
    try:
        if isinstance(valor, str):
            texto = valor
        else:
            texto = json.dumps(valor, ensure_ascii=False, default=str)
    except Exception:
        texto = str(valor)
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


# ── El bus ────────────────────────────────────────────────────────────────

def emitir(wa_id: str, tipo: str, **datos: Any) -> None:
    """Le manda un evento a todos los paneles conectados. **No bloquea, no levanta.**

    Este es el único punto de entrada del bus, y su `except Exception` es toda la red de
    seguridad del panel: se llama desde el camino real de WhatsApp, así que un error acá
    —serializar algo raro, una cola llena, un cliente a medio desconectar— tiene que
    morir en silencio y dejar que la respuesta siga.
    """
    if not es_demo(wa_id) or not _suscriptores:
        return
    try:
        linea = "data: " + json.dumps({"tipo": tipo, **datos}, ensure_ascii=False) + "\n\n"
        for cola in list(_suscriptores):
            try:
                cola.put_nowait(linea)
            except asyncio.QueueFull:
                pass
    except Exception:
        log.debug("evento de demo descartado", exc_info=True)


# ── El handler que le pasamos a agente.run() ──────────────────────────────

async def manejador_eventos(
    ctx: RunContext[Deps], eventos: AsyncIterable[Any]
) -> None:
    """`event_stream_handler` de la corrida: traduce los eventos de Pydantic AI al panel.

    Tiene que consumir el iterador COMPLETO aunque el emisor falle — si sale temprano, la
    corrida se queda esperando a que alguien drene el stream del nodo.

    Ojo con el `except Exception`: es a propósito que no sea `BaseException`. Un
    `CancelledError` tiene que seguir su camino o la corrida no se puede cancelar.
    """
    wa_id = ctx.deps.wa_id
    async for evento in eventos:
        try:
            match evento:
                # Cualquier parte que arranca significa que el modelo está escribiendo.
                # Un TextPart nuevo reinicia la burbuja en curso: cuando el modelo narra
                # ("voy a revisar eso"), llama una tool y después contesta, lo que va a
                # WhatsApp es solo el último texto.
                case PartStartEvent(part=TextPart(content=inicial)):
                    emitir(wa_id, "parte", clase="texto", texto=inicial or "")
                case PartStartEvent(part=ThinkingPart()):
                    emitir(wa_id, "parte", clase="pensando")
                case PartStartEvent(part=ToolCallPart()):
                    emitir(wa_id, "parte", clase="tool")

                case PartDeltaEvent(delta=TextPartDelta(content_delta=trozo)):
                    emitir(wa_id, "texto", delta=trozo)
                case PartDeltaEvent(delta=ThinkingPartDelta()):
                    emitir(wa_id, "parte", clase="pensando")

                case FunctionToolCallEvent(part=ToolCallPart(tool_name=nombre) as parte):
                    emitir(
                        wa_id,
                        "tool_inicio",
                        tool=nombre,
                        args=_compacto(parte.args, LIMITE_ARGS),
                        id=parte.tool_call_id,
                    )

                # Un RetryPromptPart es un ModelRetry de la tool: el candado del orden de
                # `precio_en_drogueria`, o un tipo de documento que no procede. Se marca
                # distinto porque es la red de seguridad funcionando, no un error.
                case FunctionToolResultEvent(part=RetryPromptPart() as parte):
                    emitir(
                        wa_id,
                        "tool_fin",
                        tool=parte.tool_name or "?",
                        id=parte.tool_call_id,
                        resultado=_compacto(parte.content, LIMITE_RESULTADO),
                        reintento=True,
                    )
                case FunctionToolResultEvent(part=ToolReturnPart() as parte):
                    emitir(
                        wa_id,
                        "tool_fin",
                        tool=parte.tool_name,
                        id=parte.tool_call_id,
                        resultado=_compacto(parte.content, LIMITE_RESULTADO),
                    )
        except Exception:
            log.debug("evento de la corrida sin traducir", exc_info=True)


# ── Las fotos de las fórmulas ─────────────────────────────────────────────

async def guardar_foto(wa_id: str, imagen: bytes, mime: str) -> str | None:
    """Guarda la foto para poder mostrarla en el panel y devuelve su URL.

    Devuelve `None` —sin guardar nada— si el número no es el de la demo. Ese es el punto:
    `agent._sin_fotos` saca las imágenes del historial antes de persistirlo, así que hoy
    no queda rastro de la foto de nadie, y esto no cambia eso salvo para un número.
    """
    if not es_demo(wa_id):
        return None
    if not settings.public_base_url:
        log.warning("hay foto para el panel pero falta PUBLIC_BASE_URL: no hay URL que armar")
        return None
    try:
        doc_id = await db.guardar_documento(wa_id, "foto", imagen, mime)
        return f"{settings.public_base_url.rstrip('/')}/f/{doc_id}"
    except Exception:
        log.exception("no se pudo guardar la foto del panel")
        return None


# ── El estado inicial ─────────────────────────────────────────────────────

async def _burbujas(wa_id: str) -> tuple[list[dict], list[str]]:
    """Reconstruye el chat y las tools ya usadas desde `conversations.messages`.

    El historial es el formato de Pydantic AI serializado tal cual, así que acá se
    camina: `UserPromptPart` es una burbuja del paciente, `TextPart` una de Curuba, y los
    `ToolCallPart` son la traza que deja el camino del último turno pintado en el grafo.
    """
    crudo = await db.cargar_historial(wa_id)
    if not crudo:
        return [], []

    mensajes = ModelMessagesTypeAdapter.validate_json(crudo)
    burbujas: list[dict] = []
    tools: list[str] = []
    # Un `generar_documento` que devolvió —los que salen por ModelRetry dan un
    # RetryPromptPart y no guardaron nada— marca la siguiente burbuja de Curuba, que es
    # el mensaje con el que se mandó el PDF.
    pendiente_doc = 0

    for mensaje in mensajes:
        for parte in mensaje.parts:
            if isinstance(parte, UserPromptPart):
                trozos = (
                    [parte.content]
                    if isinstance(parte.content, str)
                    else [t for t in parte.content if isinstance(t, str)]
                )
                texto = " ".join(t for t in trozos if t != MARCA_FOTO).strip()
                burbuja: dict[str, Any] = {"de": "tu", "texto": texto}
                if any(t == MARCA_FOTO for t in trozos):
                    burbuja["foto"] = True
                burbujas.append(burbuja)
            elif isinstance(parte, TextPart):
                burbuja = {"de": "curuba", "texto": parte.content}
                if pendiente_doc:
                    burbuja["doc"] = True
                    pendiente_doc -= 1
                burbujas.append(burbuja)
            elif isinstance(parte, ToolCallPart):
                tools.append(parte.tool_name)
            elif isinstance(parte, ToolReturnPart) and parte.tool_name == "generar_documento":
                pendiente_doc += 1

    return burbujas, tools


async def snapshot() -> dict:
    """El primer evento del stream: la conversación que ya existía.

    Va como primer evento y no como endpoint aparte para que no haya ventana entre pedir
    el estado y suscribirse, y para que la reconexión automática del `EventSource` sea
    idempotente: cada vez que llega un `estado`, el cliente reemplaza todo.
    """
    base = {"tipo": "estado", "activo": bool(_DEMO), "numero": _bonito(_DEMO)}
    if not _DEMO:
        return base | {"burbujas": [], "tools_usadas": []}

    try:
        burbujas, tools = await _burbujas(_DEMO)
        fotos = [f["id"] for f in await db.documentos_de(_DEMO, "foto")]
        escritos = [
            (f["id"], f["tipo"]) for f in await db.documentos_de(_DEMO) if f["tipo"] != "foto"
        ]
    except Exception:
        log.exception("no se pudo armar el estado del panel")
        return base | {"burbujas": [], "tools_usadas": []}

    url = f"{settings.public_base_url.rstrip('/')}/f/" if settings.public_base_url else ""

    # Las dos correspondencias se hacen DE ATRÁS PARA ADELANTE, y esto no es un detalle:
    # `conversations` se borra con `reiniciar` pero las filas de `documents` se quedan para
    # siempre, así que el historial casi nunca tiene tantas marcas como filas hay. De
    # adelante hacia atrás, la burbuja del último PDF terminaba con el nombre de un escrito
    # de otra conversación —decía "Acción de tutela" en un derecho de petición—, y una foto
    # recién tomada aparecía pegada al mensaje más viejo del hilo.
    for burbuja, doc_id in zip(
        reversed([b for b in burbujas if b.get("foto")]), reversed(fotos)
    ):
        burbuja["foto"] = f"{url}{doc_id}" if url else None

    for burbuja, (doc_id, tipo) in zip(
        reversed([b for b in burbujas if b.get("doc")]), reversed(escritos)
    ):
        if url:
            burbuja["documento"] = {
                "url": f"{url}{doc_id}",
                "nombre": legal.NOMBRES.get(tipo, tipo or "documento"),
            }

    for burbuja in burbujas:
        burbuja.pop("doc", None)
        # `foto` queda solo cuando es una URL de verdad. Las marcas que no alcanzaron fila
        # —todo lo de antes de que existiera el panel— se van.
        if not isinstance(burbuja.get("foto"), str):
            burbuja.pop("foto", None)

    return base | {"burbujas": burbujas, "tools_usadas": sorted(set(tools))}


# ── El stream ─────────────────────────────────────────────────────────────

def cerrar_streams() -> None:
    """Despide a los SSE abiertos. Se llama desde el lifespan, al apagar.

    Sin esto el apagado se queda colgado: uvicorn espera a que terminen las respuestas en
    vuelo, y un generador SSE con un `while True` adentro no termina nunca. En local eso es
    un `--reload` que no vuelve; en Railway es un deploy que no arranca hasta que el proxy
    mate la conexión por su cuenta.
    """
    for cola in list(_suscriptores):
        try:
            cola.put_nowait(_FIN)
        except asyncio.QueueFull:
            pass


async def eventos() -> AsyncIterator[str]:
    """El generador del SSE. Primero el estado completo, después lo que vaya pasando."""
    cola: asyncio.Queue[str] = asyncio.Queue(maxsize=TOPE_COLA)
    # Suscribirse ANTES de leer el estado: si se hace después, los eventos que ocurran
    # mientras corre la query se pierden y el panel arranca con un turno a medias.
    _suscriptores.add(cola)
    limite = asyncio.get_running_loop().time() + VIDA
    try:
        estado = await snapshot()
        yield "data: " + json.dumps(estado, ensure_ascii=False) + "\n\n"
        while asyncio.get_running_loop().time() < limite:
            try:
                linea = await asyncio.wait_for(cola.get(), timeout=LATIDO)
            except TimeoutError:
                yield ": latido\n\n"
                continue
            if linea == _FIN:
                return
            yield linea
    finally:
        _suscriptores.discard(cola)
