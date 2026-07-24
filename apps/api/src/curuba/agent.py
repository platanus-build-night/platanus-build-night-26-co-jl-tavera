"""El agente de Pydantic AI.

Slice 1: sin tools. Solo conversa, en español, y se acuerda del hilo.
Las cuatro tools (`buscar_medicamento`, `consultar_desabastecimiento`,
`guardar_dato_tutela`, `generar_tutela`) llegan en el siguiente slice.
"""

from pydantic_ai import Agent, ModelMessagesTypeAdapter

from curuba import db
from curuba.config import settings

PROMPT = """\
Eres Curuba, un asistente de WhatsApp para pacientes en Colombia que tienen
problemas para que les entreguen sus medicamentos.

Hablas siempre en español, en el tono de alguien que le explica algo a un
vecino: claro, cálido y sin tecnicismos. Las respuestas van por WhatsApp, así
que son cortas — dos o tres frases. Si necesitas varios datos, pregunta uno
por mensaje, nunca una lista.

Todavía estás en construcción. Por ahora solo puedes conversar y explicar qué
vas a poder hacer:
1. Leer una fórmula médica y decir el precio máximo regulado de cada
   medicamento según el SISMED.
2. Consultar si un medicamento está desabastecido según el INVIMA.
3. Hacer las preguntas necesarias y armar el borrador de una tutela.

Si alguien te pide una de esas tres cosas, dile con honestidad que esa función
todavía no está lista, y ofrécele conversar mientras tanto. No inventes precios,
estados de desabastecimiento ni documentos: un dato equivocado en salud es peor
que no dar ningún dato.

Curuba no da asesoría médica ni jurídica. No diagnosticas, no recomiendas
tratamientos y no reemplazas a un abogado.
"""

agente = Agent(settings.curuba_model, system_prompt=PROMPT)


async def responder(wa_id: str, texto: str) -> str:
    """Corre el agente con el historial de ese número y lo guarda actualizado."""
    previo = await db.cargar_historial(wa_id)
    historial = ModelMessagesTypeAdapter.validate_json(previo) if previo else None

    resultado = await agente.run(texto, message_history=historial)

    await db.guardar_historial(wa_id, resultado.all_messages_json())
    return resultado.output


async def reiniciar(wa_id: str) -> None:
    """Borra la conversación de un número. Se usa muchísimo probando."""
    await db.borrar_historial(wa_id)


if __name__ == "__main__":
    # Probar el agente sin Twilio y sin WhatsApp, solo con OPENROUTER_API_KEY:
    #   cd apps/api && PYTHONPATH=src uv run python -m curuba.agent
    import asyncio
    import sys

    # La consola de Windows usa cp1252 y revienta con los emojis que manda
    # el modelo. Es problema solo del terminal — en WhatsApp y en Railway
    # (Linux, UTF-8) no pasa.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    async def _repl() -> None:
        await db.abrir()
        print("Curuba — solo el agente, sin WhatsApp. Ctrl-C para salir.\n")
        try:
            while True:
                texto = input("tú> ").strip()
                if texto:
                    print("curuba>", await responder("local", texto), "\n")
        finally:
            await db.cerrar()

    try:
        asyncio.run(_repl())
    except (KeyboardInterrupt, EOFError):
        print()
