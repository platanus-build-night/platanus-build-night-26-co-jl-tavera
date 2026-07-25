"""Las dos tools de la ruta legal: la entrevista y la generación del escrito.

La lógica no está acá — está en el paquete `curuba.legal`. Este módulo es la capa de
traducción entre el agente y esa lógica: valida, llama, y convierte los resultados en
algo que el modelo pueda usar sin reinterpretarlo.

El bloqueo del triage se hace con `ModelRetry` a propósito: le devuelve el porqué al
modelo para que lo explique en sus palabras, en vez de reventar la corrida.
"""

from __future__ import annotations

from typing import Any

from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.toolsets import FunctionToolset

from curuba import db, legal
from curuba.config import settings
from curuba.tools.deps import Deps

ruta_legal = FunctionToolset()


def _preguntas(nombres: list[str]) -> list[dict[str, Any]]:
    """Los campos que faltan, con la pregunta ya redactada para el paciente.

    La pregunta va literal para que el modelo no la reinvente: están escritas para que
    las entienda alguien que no sabe de leyes, y "¿corre riesgo tu vida?" no es lo mismo
    que "¿configura un perjuicio irremediable?".
    """
    salida = []
    for nombre in nombres:
        campo = legal.CAMPOS[nombre]
        entrada: dict[str, Any] = {"campo": nombre, "pregunta": campo.pregunta}
        if campo.opciones:
            entrada["valores_validos"] = list(campo.opciones)
        elif campo.tipo == "si_no":
            entrada["valores_validos"] = ["sí", "no"]
        salida.append(entrada)
    return salida


@ruta_legal.tool
async def guardar_dato_caso(
    ctx: RunContext[Deps], campo: str, valor: str
) -> dict[str, Any]:
    """Guarda un dato de la entrevista legal y dice qué mecanismo procede.

    Es también el triage: con cada dato recalcula la ruta (derecho de petición, tutela,
    desacato o Supersalud) y te devuelve qué falta preguntar. Úsala apenas alguien cuente
    que no le entregan un medicamento o que quiere reclamar.

    Args:
        campo: el nombre exacto del campo. Si no sabes cuál es, mira
            `preguntas_pendientes` de la llamada anterior.
        valor: lo que respondió el paciente, tal cual. Para los de sí/no, "sí" o "no".
    """
    problema = legal.validar(campo, valor)
    if problema:
        raise ModelRetry(problema)

    campos = await db.guardar_campo_caso(ctx.deps.wa_id, campo, valor)
    ruta, por_que = legal.decidir_ruta(campos)
    obligatorios, opcionales = legal.pendientes(campos, ruta)

    respuesta: dict[str, Any] = {
        "guardado": {"campo": campo, "valor": valor},
        "ruta": ruta,
        "que_es": legal.RUTAS[ruta],
        "por_que": por_que,
        "preguntas_pendientes": _preguntas(obligatorios),
        "opcionales_que_ayudarian": _preguntas(opcionales),
        "listo_para_generar": ruta in legal.DOCUMENTOS and not obligatorios,
    }
    if ruta == "esperar":
        respuesta["canales_supersalud"] = legal.SUPERSALUD_CANALES

    # Va AL LADO de la ruta, no en su lugar: son cosas que se suman. Radicar un escrito
    # no le quita a nadie el derecho al domicilio en 48 horas, y la constancia es la
    # prueba de la que después va a depender ese mismo escrito.
    mostrador = legal.accion_inmediata(campos)
    if mostrador:
        respuesta["accion_inmediata"] = mostrador
        respuesta["nota_accion_inmediata"] = (
            "Dile ESTO primero, antes de seguir con las preguntas. Si está en el "
            "dispensador ahora mismo, es lo único que importa en este momento: son dos "
            "minutos de pie y sin esa constancia el escrito que sigue llega sin prueba."
        )
    return respuesta


@ruta_legal.tool
async def generar_documento(ctx: RunContext[Deps], tipo: str) -> dict[str, Any]:
    """Arma el PDF del escrito y devuelve el enlace para mandárselo al paciente.

    Solo genera el que corresponde a la ruta del triage: si pides otro te dice cuál
    procede y por qué, para que se lo expliques.

    Args:
        tipo: peticion | tutela | desacato | supersalud.
    """
    if tipo not in legal.DOCUMENTOS:
        raise ModelRetry(
            f"'{tipo}' no es un documento que exista. Son: " + ", ".join(legal.DOCUMENTOS)
        )

    campos = await db.cargar_caso(ctx.deps.wa_id)
    ruta, por_que = legal.decidir_ruta(campos)

    if ruta != tipo:
        # El bloqueo del triage. No es un error del modelo que se arregle reintentando
        # el mismo tipo: es que ese escrito no procede y hay que explicarlo.
        raise ModelRetry(
            f"No se generó nada. En este caso NO procede '{tipo}' sino '{ruta}'. "
            f"{por_que} Explícaselo al paciente con tus palabras, ofrécele el que sí "
            f"procede y no vuelvas a pedir '{tipo}'."
        )

    obligatorios, _ = legal.faltantes(campos, tipo)
    if obligatorios:
        raise ModelRetry(
            "Todavía faltan datos obligatorios para ese escrito: "
            + "; ".join(f"{n} ({legal.CAMPOS[n].pregunta})" for n in obligatorios)
            + ". Pregúntaselos de a uno y guárdalos con guardar_dato_caso."
        )

    pdf, marcadores = legal.generar(campos, tipo)
    doc_id = await db.guardar_documento(ctx.deps.wa_id, tipo, pdf)

    if settings.public_base_url:
        url = f"{settings.public_base_url.rstrip('/')}/f/{doc_id}"
        ctx.deps.adjunto = url
    else:
        # Sin PUBLIC_BASE_URL no hay cómo armar el enlace (pasa en el REPL local). El
        # escrito SÍ quedó bien: hay que decírselo al modelo con todas las letras, o
        # lee esto como una falla y le dice al paciente que hubo un "problema técnico"
        # justo cuando su documento está listo y guardado.
        url = None

    if url is None:
        return {
            "generado": legal.NOMBRES[tipo],
            "documento_id": doc_id,
            "marcadores": marcadores,
            "nota": (
                "EL DOCUMENTO SE GENERÓ BIEN y quedó guardado. Lo único que falta es "
                "configuración del servidor (PUBLIC_BASE_URL) para poder enviarlo, así "
                "que no hay enlace todavía. NO le digas al paciente que hubo un problema "
                "técnico ni que falló algo suyo: dile que su documento ya está listo y "
                "que en un momento se lo haces llegar."
            ),
        }

    # El `url` NO se le devuelve al modelo, y eso es deliberado. Cuando lo veía, leía el
    # enlace como si fuera el entregable y le decía al paciente "te paso el link" — o
    # peor, "no puedo mandarte archivos por aquí, solo el enlace", que es exactamente lo
    # contrario de lo que pasa. El PDF ya viaja adjunto vía `ctx.deps.adjunto`, que lee
    # `agent.responder()` al terminar la corrida.
    #
    # Si el envío con adjunto llegara a fallar, `main._procesar` reintenta él mismo
    # pegando el enlace al final del texto. O sea que el modelo nunca necesita la URL:
    # no dársela le quita la posibilidad de equivocarse con ella.
    return {
        "generado": legal.NOMBRES[tipo],
        "se_adjunta_automaticamente": True,
        "marcadores": marcadores,
        "nota": (
            "El PDF YA VA ADJUNTO en este mismo mensaje de WhatsApp: sale solo, no "
            "tienes que hacer nada más y no tienes ningún enlace que pegar. NUNCA le "
            "digas que no puedes mandarle archivos por aquí, ni que la única forma es un "
            "enlace, ni le pidas un correo: sí puedes y ya está saliendo. "
            + (
                "Léele los marcadores: son los espacios que quedaron en blanco y los "
                "tiene que llenar a mano antes de radicar."
                if marcadores
                else "No quedaron espacios en blanco."
            )
        ),
    }
