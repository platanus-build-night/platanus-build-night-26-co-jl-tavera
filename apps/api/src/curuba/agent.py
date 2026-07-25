"""El agente de Pydantic AI.

Slice 2: las tres tools que leen datos. Faltan `guardar_dato_tutela` y `generar_tutela`.

Un solo agente con tools, no tres endpoints: WhatsApp es una sola conversación y el
modelo decide qué consultar. El orden importa y está en el prompt — la cobertura del PBS
va primero, porque si el medicamento está financiado con la UPC el precio es casi
irrelevante: la ruta es el dispensador de la EPS.

Las tools devuelven `encontrado` y `nota` aparte de los candidatos. No es adorno: es la
forma de que "no lo encontré" no se pueda confundir con "la respuesta es no". El
significado de cada estado se traduce acá en Python, no se deja a interpretación del
modelo.
"""

from typing import Any

from pydantic_ai import Agent, ModelMessagesTypeAdapter

from curuba import db
from curuba.config import settings

# Qué significa cada cobertura del PBS, en palabras que el modelo pueda repetir. La
# distinción que importa: `mipres` NO es "no cubierto" — son 420 filas y leerlas al revés
# manda a alguien a pagar de su bolsillo algo a lo que tiene derecho.
COBERTURAS = {
    "upc": "Financiado con la UPC: la EPS tiene que entregarlo en su dispensador. "
           "El paciente solo paga la cuota moderadora.",
    "condicionada": "Financiado con la UPC solo si se cumple el criterio que está en "
                    "'aclaracion'. Hay que leerle ese criterio al paciente tal cual.",
    "mipres": "No se financia con la UPC, pero NO significa que le toque comprarlo: se "
              "prescribe por la vía MIPRES y la EPS igual debe entregarlo. El paciente "
              "tiene que pedirle al médico que se lo formule por MIPRES.",
    "excluido": "Excluido de la financiación con recursos públicos. Este sí le toca "
                "comprarlo, salvo que un juez ordene lo contrario.",
    None: "La fuente no trae el dato de cobertura para este medicamento.",
}

ESTADOS = {
    "monitorizacion": "El INVIMA lo tiene en monitorización: hay señales de problemas de "
                      "abastecimiento pero todavía no está declarado desabastecido.",
    "riesgo": "En riesgo de desabastecimiento según el INVIMA.",
    "desabastecido": "Declarado DESABASTECIDO por el INVIMA.",
    "no_desabastecido": "El INVIMA le hizo seguimiento y CERRÓ el caso: hoy no está "
                        "desabastecido. Ojo, esto no es lo mismo que 'no hay reportes'.",
    None: "La fuente no trae el estado de esta fila.",
}

PROMPT = """\
Eres Curuba, un asistente de WhatsApp para pacientes en Colombia que tienen problemas
para que les entreguen sus medicamentos.

Hablas siempre en español, en el tono de alguien que le explica algo a un vecino: claro,
cálido y sin tecnicismos. Las respuestas van por WhatsApp, así que son cortas — dos o
tres frases. Si necesitas varios datos, pregunta uno por mensaje, nunca una lista.

## El orden en que consultas

Cuando alguien te nombra un medicamento, lo primero es `consultar_cobertura`, no el
precio. Si está financiado con la UPC, el paciente tiene derecho a reclamarlo en el
dispensador de su EPS pagando solo la cuota moderadora — decirle cuánto cuesta en la
droguería antes de eso lo manda a gastar plata que no tiene que gastar.

Solo si le toca comprarlo, o si él insiste en saber el precio, usas `buscar_medicamento`.
`consultar_desabastecimiento` va cuando pregunta por qué no se lo entregan o si va a
conseguirlo.

## Lo que no puedes decir nunca

1. **Que algo no está cubierto porque no lo encontraste.** Si `consultar_cobertura` viene
   con `encontrado: false`, el listado simplemente no lo tiene — y no es exhaustivo. Se
   dice "no lo encontré en el listado, confírmalo con tu EPS antes de comprarlo". Nunca
   "no está cubierto". Equivocarse hacia ese lado hace que alguien pague $200.000 por
   algo gratis; equivocarse hacia el otro solo cuesta un viaje al dispensador.

2. **Que MIPRES quiere decir que le toca comprarlo.** No lo es. La EPS igual tiene que
   entregarlo; lo que cambia es que el médico debe formularlo por esa vía.

3. **Que se cambie de medicamento.** Que dos presentaciones tengan el mismo principio
   activo y la misma concentración NO quiere decir que sean intercambiables. Puedes
   decir "esta otra presentación tiene la misma molécula y cuesta $X, pregúntale a tu
   médico o a tu farmaceuta si te sirve", nunca "cámbiate a esta".

4. **Que un precio de droguería es ilegal o un abuso.** Los precios que tú manejas son
   techos regulados del canal institucional, no lo que cobra un mostrador: la venta al
   consumidor final casi nunca está regulada. Puedes decir cuál es el techo institucional
   y que lo compare, pero no que le están cobrando por encima de la ley.

5. **Que le van a entregar el medicamento en 48 horas.** La Resolución 1604 de 2013 dice
   que si no hay existencias la EPS debe entregarlo a domicilio en 48 horas, y eso sí se
   lo puedes contar como lo que dice la norma y puede exigir. Pero no se lo prometas: se
   incumple mucho.

## Cómo usas los resultados

Las búsquedas son por parecido, así que te devuelven varios candidatos con un `score`.
**Nunca escojas el primero en silencio.** Si hay varios y son cosas distintas —
`ACETAMINOFÉN` y `ACETAMINOFÉN + CODEINA` son medicamentos diferentes y pueden tener
coberturas diferentes — pregúntale al paciente cuál es el suyo antes de responder.

Si un candidato trae `aclaracion`, léesela tal cual; ahí está el criterio que condiciona
la cobertura. No la resumas ni la interpretes.

Un dato equivocado en salud es peor que no dar ningún dato. Si no estás seguro, dilo.

Curuba no da asesoría médica ni jurídica. No diagnosticas, no recomiendas tratamientos y
no reemplazas a un abogado.
"""

agente = Agent(settings.curuba_model, system_prompt=PROMPT)


@agente.tool_plain
async def consultar_cobertura(nombre: str) -> dict[str, Any]:
    """Dice si un medicamento lo financia la EPS con la UPC. ÚSALA PRIMERO.

    Es la pregunta que más plata le ahorra al paciente: si está financiado, lo reclama en
    el dispensador de su EPS en vez de comprarlo.

    Args:
        nombre: el principio activo o el nombre que dijo el paciente, tal cual.
    """
    filas = await db.buscar_cobertura(nombre)
    if not filas:
        return {
            "encontrado": False,
            "nota": "No aparece en el listado del PBS. Eso NO quiere decir que no esté "
                    "cubierto: el listado no es exhaustivo. Dile que lo confirme con su "
                    "EPS antes de comprarlo.",
            "candidatos": [],
        }
    return {
        "encontrado": True,
        "candidatos": [
            {
                "principio_activo": f["principio_activo"],
                "cobertura": f["cobertura"],
                "significado": COBERTURAS.get(f["cobertura"], COBERTURAS[None]),
                "aclaracion": f["aclaracion"],
                "score": float(f["score"]),
            }
            for f in filas
        ],
    }


@agente.tool_plain
async def buscar_medicamento(nombre: str) -> dict[str, Any]:
    """Busca el precio máximo regulado de un medicamento en el SISMED.

    El precio es el techo del canal institucional, NO lo que cobra una droguería. Solo
    están los medicamentos bajo control directo de precios, que son una minoría.

    Args:
        nombre: el nombre o principio activo, como lo escribió el paciente.
    """
    filas = await db.buscar_medicamento(nombre)
    if not filas:
        return {
            "encontrado": False,
            "nota": "No está en la tabla de precios regulados. Eso significa que no está "
                    "bajo control directo de precios (la mayoría no lo está), no que no "
                    "exista ni que haya fallado la consulta.",
            "candidatos": [],
        }
    return {
        "encontrado": True,
        "advertencia": "Estos son techos regulados del canal institucional, no el precio "
                       "de una droguería.",
        "candidatos": [
            {
                "descripcion": f["descripcion"],
                "laboratorio": f["laboratorio"],
                "precio_maximo_institucional": int(f["precio_institucional"]),
                "contenido": f"{f['cantidad']} {f['unidad']}" if f["cantidad"] else None,
                "score": float(f["score"]),
            }
            for f in filas
        ],
    }


@agente.tool_plain
async def consultar_desabastecimiento(nombre: str) -> dict[str, Any]:
    """Dice si el INVIMA tiene un medicamento en seguimiento por desabastecimiento.

    Args:
        nombre: el nombre o principio activo, como lo escribió el paciente.
    """
    filas = await db.consultar_desabastecimiento(nombre)
    if not filas:
        return {
            "encontrado": False,
            "nota": "No hay reportes del INVIMA sobre este medicamento. No es lo mismo "
                    "que el estado 'no desabastecido', que sí es un caso que el INVIMA "
                    "revisó y cerró.",
            "candidatos": [],
        }
    return {
        "encontrado": True,
        "candidatos": [
            {
                "nombre": f["nombre"],
                "estado": f["estado"],
                "significado": ESTADOS.get(f["estado"], ESTADOS[None]),
                "fecha_ultimo_seguimiento": (
                    f["fecha_seguimiento"].isoformat() if f["fecha_seguimiento"] else None
                ),
                "score": float(f["score"]),
            }
            for f in filas
        ],
    }


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
