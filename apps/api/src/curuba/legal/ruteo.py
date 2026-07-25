"""El triage: qué mecanismo procede y por qué.

Es el módulo más importante del paquete. Escoger mal el escalón de la ruta es el modo
de falla real del producto —llevarle a la Supersalud un problema de entrega es tocar una
puerta que no tiene competencia—, así que esta decisión vive en Python y no en el prompt.
Mismo principio que COBERTURAS y ESTADOS en las tools de medicamentos: lo que tiene
consecuencia legal se traduce acá y no se deja a interpretación del modelo.
"""

from __future__ import annotations

from curuba.legal.campos import TRIAGE, CAMPOS, es_si, respondido
from curuba.legal.documentos import (
    MOSTRADOR,
    PLAZO_DOMICILIO_HORAS,
    SUPERSALUD_CANALES,
)
from curuba.legal.fechas import (
    PLAZO_PETICION,
    corridos_desde,
    habiles_desde,
    leer_fecha,
)
from curuba.legal.texto import normalizar

RUTAS = {
    "indefinida": "Todavía no sé qué mecanismo procede: falta terminar el triage.",
    "peticion": "Derecho de petición ante la EPS.",
    "tutela": "Acción de tutela.",
    "desacato": "Incidente de desacato ante el juez que falló la tutela.",
    "supersalud": "Demanda ante la función jurisdiccional de la Superintendencia de Salud.",
    "esperar": "Todavía no procede un escrito nuevo: la EPS está dentro del plazo.",
}


def decidir_ruta(campos: dict) -> tuple[str, str]:
    """Qué mecanismo procede y por qué. El ORDEN de las reglas es el contenido.

    La regla del riesgo vital va de segunda a propósito: con riesgo la tutela procede
    directa y con medida provisional, sin agotar nada antes. Es la regla que nunca puede
    terminar mandando a alguien a esperar 15 días hábiles.
    """
    # 1. Ya hay un fallo de tutela. Volver a tutelar los mismos hechos es temeridad;
    #    lo que procede es el desacato ante el mismo juez.
    if es_si(campos, "tutela_previa"):
        return "desacato", (
            "Ya hubo una tutela por estos hechos. Poner otra por lo mismo es temeridad "
            "y se cae; lo que procede es el incidente de desacato ante el mismo juez "
            "que falló (art. 52 del Decreto 2591 de 1991)."
        )

    # 2. Riesgo vital. No hay nada que agotar antes.
    if es_si(campos, "riesgo_vital"):
        return "tutela", (
            "Hay riesgo para la vida o la integridad, así que la tutela procede directo "
            "y con solicitud de medida provisional (art. 7 del Decreto 2591 de 1991): el "
            "juez puede ordenar la entrega en horas, antes de fallar el fondo. No hay que "
            "radicar nada antes."
        )

    faltan = [c for c in TRIAGE if not respondido(campos, c)]
    if faltan:
        return "indefinida", (
            "Para saber qué mecanismo procede me falta: "
            + ", ".join(CAMPOS[c].marcador for c in faltan)
            + "."
        )

    # 3. El problema es de cobertura o de plata, no de entrega. Ahí sí la Supersalud
    #    tiene función jurisdiccional.
    problema = normalizar(campos.get("tipo_problema", ""))
    if problema in ("cobertura", "reembolso"):
        return "supersalud", (
            "El problema es de cobertura o de reembolso, no de entrega. Eso sí está en la "
            "función jurisdiccional de la Supersalud (art. 41 de la Ley 1122 de 2007), que "
            "falla en derecho y con carácter definitivo."
        )

    # 4/5. Es un problema de entrega y ya se radicó petición: la pregunta es si la EPS
    #      todavía está en plazo.
    if es_si(campos, "peticion_radicada"):
        radicada = leer_fecha(campos.get("peticion_fecha", ""))
        if radicada is None:
            return "indefinida", (
                "Falta la fecha en que radicó la petición: es lo que decide si la EPS "
                "ya está en mora o todavía tiene plazo."
            )
        transcurridos = habiles_desde(radicada)
        if transcurridos > PLAZO_PETICION:
            return "tutela", (
                f"La petición se radicó hace {transcurridos} días hábiles y el plazo del "
                f"art. 14 de la Ley 1755 de 2015 es de {PLAZO_PETICION}. La EPS está en "
                "mora, así que procede la tutela por violación del derecho de petición "
                "(art. 23 CP), que es más fácil de sustentar que la del derecho a la salud."
            )
        return "esperar", (
            f"La petición se radicó hace {transcurridos} días hábiles y la EPS tiene "
            f"{PLAZO_PETICION} (art. 14 de la Ley 1755 de 2015), así que todavía está en "
            "plazo. Mientras tanto se puede poner una queja ante la Supersalud. "
            + SUPERSALUD_CANALES
        )

    # 6. Entrega, sin riesgo y sin haber pedido nada. El primer escalón.
    return "peticion", (
        "Es un problema de entrega y todavía no se le ha pedido nada por escrito a la "
        "EPS. Arranca el derecho de petición: es gratis, no necesita abogado y deja el "
        "radicado con fecha que sostiene la tutela después si no responden."
    )


def accion_inmediata(campos: dict) -> str | None:
    """Lo que la persona puede hacer YA, antes de cualquier escrito. O None.

    **No es una ruta y a propósito no lo es.** Si `decidir_ruta` devolviera "mostrador",
    `generar_documento` se negaría a hacer la petición porque el tipo no coincidiría con
    la ruta — y estaríamos bloqueando justo lo que no queremos bloquear. Las dos cosas se
    suman: radicar una petición no le quita a nadie el derecho al domicilio, y es gratis.
    Por eso esto viaja al lado de la ruta, no en su lugar.

    Devuelve None cuando ya tiene la constancia (el paso está hecho) o cuando el problema
    no es de entrega — a quien le negaron la cobertura no le sirve pedir un domicilio.
    """
    problema = normalizar(campos.get("tipo_problema", ""))
    if problema in ("cobertura", "reembolso"):
        return None
    if es_si(campos, "constancia"):
        return None

    reclamo = leer_fecha(campos.get("fecha_reclamacion", ""))
    if reclamo is None:
        cierre = (
            "Si reclamaste hace menos de dos días, el plazo de las 48 horas todavía está "
            "corriendo. Si fue hace más, ya se venció y eso entra como un hecho en el "
            "escrito."
        )
    elif corridos_desde(reclamo) * 24 < PLAZO_DOMICILIO_HORAS:
        cierre = (
            f"Todavía estás dentro de las {PLAZO_DOMICILIO_HORAS} horas: la EPS está a "
            "tiempo de llevártelo a la casa, y por eso el paso 2 es el que más importa "
            "ahora."
        )
    else:
        dias = corridos_desde(reclamo)
        cierre = (
            f"Ya pasaron {dias} días desde que reclamaste, así que las "
            f"{PLAZO_DOMICILIO_HORAS} horas están vencidas. Eso ya no es una espera: es "
            "un incumplimiento, y entra como hecho en el escrito que sigue. La constancia "
            "te sirve igual, así que vale la pena pedirla aunque sea ahora."
        )

    return (
        "Antes de cualquier escrito, esto es lo que puede hacer HOY, apoyado en la "
        "Resolución 1604 de 2013:\n" + MOSTRADOR + "\n" + cierre
    )
