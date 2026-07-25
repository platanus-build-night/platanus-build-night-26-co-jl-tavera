"""Los datos de la entrevista: qué se pregunta, cómo se valida y qué falta.

`CAMPOS` es la fuente de verdad de la entrevista. El agente no lleva la lista en el
prompt: la tool se la va sacando de acá, con la pregunta ya redactada. Eso importa
porque las preguntas están escritas para alguien que no sabe de leyes — "¿corre riesgo
tu vida?" no es lo mismo que "¿configura un perjuicio irremediable?".
"""

from __future__ import annotations

from dataclasses import dataclass

from curuba.legal.documentos import DOCUMENTOS
from curuba.legal.texto import normalizar

TODOS = DOCUMENTOS


@dataclass(frozen=True)
class Campo:
    """Un dato de la entrevista.

    `obligatorio` son los documentos que NO se pueden generar sin él; `util_en`, los que
    cambian de contenido si está pero salen igual si falta. `solo_si` lo vuelve
    condicional: no se pregunta ni se exige mientras el otro campo no diga que sí.
    """

    pregunta: str
    marcador: str
    obligatorio: tuple[str, ...] = ()
    util_en: tuple[str, ...] = ()
    tipo: str = "texto"  # texto | si_no | fecha | opcion
    opciones: tuple[str, ...] = ()
    solo_si: str | None = None


CAMPOS: dict[str, Campo] = {
    # ── Identidad: la necesitan los cuatro escritos ───────────────────────
    "nombre": Campo("¿Cuál es tu nombre completo?", "nombre completo", TODOS),
    "cedula": Campo("¿Cuál es tu número de cédula?", "número de cédula", TODOS),
    "ciudad": Campo("¿En qué ciudad o municipio vives?", "ciudad", TODOS),
    "direccion": Campo(
        "¿Cuál es tu dirección? Es donde te tienen que notificar y a donde te pueden "
        "llevar el medicamento.",
        "dirección de notificaciones",
        TODOS,
    ),
    "telefono": Campo("¿Cuál es tu número de teléfono?", "teléfono", TODOS),
    "correo": Campo(
        "¿Tienes correo electrónico? Sirve para que te notifiquen más rápido.",
        "correo electrónico",
        util_en=TODOS,
    ),
    # ── El caso ───────────────────────────────────────────────────────────
    "eps": Campo("¿Cuál es tu EPS?", "nombre de la EPS", TODOS),
    "gestor_farmaceutico": Campo(
        "¿Sabes cómo se llama el operador logístico o la droguería donde te toca "
        "reclamar el medicamento?",
        "operador logístico o punto de dispensación",
        util_en=("peticion", "tutela"),
    ),
    "medicamento": Campo(
        "¿Qué medicamento es? Dime el nombre, la concentración y cuántos te formularon.",
        "medicamento, concentración y cantidad",
        TODOS,
    ),
    "enfermedad": Campo(
        "¿Para qué enfermedad o condición lo necesitas?",
        "enfermedad o condición",
        util_en=("tutela", "supersalud"),
    ),
    "fecha_prescripcion": Campo(
        "¿En qué fecha te lo formularon?",
        "fecha de la fórmula",
        util_en=TODOS,
        tipo="fecha",
    ),
    "fecha_reclamacion": Campo(
        "¿En qué fecha lo reclamaste por primera vez?",
        "fecha en que reclamó el medicamento",
        TODOS,
        tipo="fecha",
    ),
    # Opcional a propósito: no alarga la entrevista obligatoria. Pero cuando está, el
    # escrito puede alegar que se pidió constancia y no la dieron, que es un hecho
    # fuerte — y `accion_inmediata` deja de insistir con el paso del mostrador.
    "constancia": Campo(
        "¿Te dieron algo por escrito donde conste que no te lo entregaron?",
        "si le dieron constancia escrita de la no entrega",
        util_en=("peticion", "tutela"),
        tipo="si_no",
    ),
    # ── Triage: estos cuatro deciden la ruta ──────────────────────────────
    "riesgo_vital": Campo(
        "Si no lo recibes ya, ¿corre riesgo tu vida o tu salud de forma grave?",
        "riesgo para la vida",
        TODOS,
        tipo="si_no",
    ),
    "tipo_problema": Campo(
        "¿El problema es que no te lo entregan, que la EPS dice que no lo cubre, o que "
        "ya lo pagaste de tu bolsillo y quieres que te lo devuelvan?",
        "tipo de problema",
        TODOS,
        tipo="opcion",
        opciones=("entrega", "cobertura", "reembolso"),
    ),
    "peticion_radicada": Campo(
        "¿Ya radicaste un derecho de petición o una queja por escrito ante tu EPS?",
        "si radicó petición previa",
        TODOS,
        tipo="si_no",
    ),
    "peticion_radicado": Campo(
        "¿Cuál es el número de radicado de esa petición?",
        "número de radicado de la petición",
        ("tutela",),
        solo_si="peticion_radicada",
    ),
    "peticion_fecha": Campo(
        "¿En qué fecha la radicaste?",
        "fecha de radicación de la petición",
        ("tutela",),
        tipo="fecha",
        solo_si="peticion_radicada",
    ),
    "tutela_previa": Campo(
        "¿Ya pusiste una tutela por estos mismos hechos?",
        "si hubo tutela previa",
        TODOS,
        tipo="si_no",
    ),
    # ── Pretensiones que solo aparecen si el caso las toca ────────────────
    "otro_municipio": Campo(
        "¿Te toca viajar a otro municipio para reclamarlo?",
        "si le exigen desplazarse",
        util_en=("peticion", "tutela"),
        tipo="si_no",
    ),
    "copagos": Campo(
        "¿Te están cobrando cuota moderadora o copago que no puedes pagar?",
        "si le cobran copagos",
        util_en=("peticion", "tutela"),
        tipo="si_no",
    ),
    "sujeto_especial": Campo(
        "¿Eres menor de edad, adulto mayor, persona con discapacidad o estás en embarazo?",
        "si es sujeto de especial protección",
        util_en=("tutela", "supersalud"),
        tipo="si_no",
    ),
    # ── Solo desacato ─────────────────────────────────────────────────────
    "tutela_numero": Campo(
        "¿Cuál es el número o radicado de esa tutela?",
        "radicado de la tutela",
        ("desacato",),
    ),
    "tutela_juzgado": Campo(
        "¿Qué juzgado la falló?", "juzgado que falló la tutela", ("desacato",)
    ),
    "tutela_fecha_fallo": Campo(
        "¿En qué fecha salió el fallo?", "fecha del fallo", ("desacato",), tipo="fecha"
    ),
    "tutela_incumplimiento": Campo(
        "¿Qué fue exactamente lo que la EPS no cumplió del fallo?",
        "qué incumplió la EPS",
        ("desacato",),
    ),
    # ── Solo Supersalud ───────────────────────────────────────────────────
    "negativa_fecha": Campo(
        "¿En qué fecha te negaron la cobertura?",
        "fecha de la negativa",
        ("supersalud",),
        tipo="fecha",
    ),
    "negativa_medio": Campo(
        "¿Cómo te la negaron? ¿Por escrito, en ventanilla, por teléfono?",
        "cómo se comunicó la negativa",
        ("supersalud",),
    ),
    "monto_reembolso": Campo(
        "¿Cuánto pagaste de tu bolsillo?", "monto pagado", util_en=("supersalud",)
    ),
}


# ── Cómo se leen las respuestas ───────────────────────────────────────────

_SI = {"si", "sí", "s", "yes", "claro", "correcto", "afirmativo", "true", "1", "obvio"}
_NO = {"no", "n", "nunca", "negativo", "false", "0", "todavia no", "todavía no"}


def es_si(campos: dict, nombre: str) -> bool:
    """True solo si el campo dice que sí. Ausente o ambiguo cuenta como no."""
    return normalizar(campos.get(nombre, "")) in _SI


def es_no(campos: dict, nombre: str) -> bool:
    return normalizar(campos.get(nombre, "")) in _NO


def respondido(campos: dict, nombre: str) -> bool:
    """Si el campo tiene una respuesta utilizable.

    Un `si_no` sin sí ni no NO cuenta como respondido: "más o menos" no decide una ruta
    legal, y tratarlo como un no mandaría a esperar 15 días hábiles a alguien que quizá
    tiene una urgencia. Se repregunta.
    """
    valor = normalizar(campos.get(nombre, ""))
    if not valor:
        return False
    campo = CAMPOS[nombre]
    if campo.tipo == "si_no":
        return valor in _SI or valor in _NO
    if campo.tipo == "opcion":
        return valor in campo.opciones
    return True


def validar(campo: str, valor: str) -> str | None:
    """Revisa un dato antes de guardarlo. Devuelve el problema, o None si sirve.

    Vive acá y no en la tool porque lo que es válido para un campo es parte de la
    definición del campo, no del agente.
    """
    if campo not in CAMPOS:
        return f"'{campo}' no es un campo válido. Los que existen son: " + ", ".join(CAMPOS)
    definicion = CAMPOS[campo]
    if definicion.opciones and normalizar(valor) not in definicion.opciones:
        return (
            f"'{valor}' no sirve para '{campo}': tiene que ser uno de "
            + ", ".join(definicion.opciones)
            + "."
        )
    if definicion.tipo == "si_no" and normalizar(valor) not in _SI | _NO:
        return (
            f"'{valor}' no es un sí ni un no, y '{campo}' decide qué mecanismo legal "
            "procede. Vuelve a preguntárselo al paciente de forma que quede claro."
        )
    return None


def aplica(nombre: str, campos: dict) -> bool:
    """Si el campo tiene sentido en este caso. Los condicionales se saltan."""
    campo = CAMPOS[nombre]
    return campo.solo_si is None or es_si(campos, campo.solo_si)


# ── Qué falta ─────────────────────────────────────────────────────────────

# Los cuatro datos que deciden la ruta. Sin ellos no se puede escoger mecanismo, salvo
# que riesgo_vital o tutela_previa corten por lo sano antes.
TRIAGE = ("riesgo_vital", "tipo_problema", "peticion_radicada", "tutela_previa")


def faltantes(campos: dict, tipo: str) -> tuple[list[str], list[str]]:
    """(obligatorios que faltan, opcionales que faltan) para ese documento."""
    obligatorios = [
        n
        for n, c in CAMPOS.items()
        if tipo in c.obligatorio and aplica(n, campos) and not respondido(campos, n)
    ]
    opcionales = [
        n
        for n, c in CAMPOS.items()
        if tipo in c.util_en and aplica(n, campos) and not respondido(campos, n)
    ]
    return obligatorios, opcionales


def pendientes(campos: dict, ruta: str) -> tuple[list[str], list[str]]:
    """Qué falta preguntar, según dónde vaya el triage.

    Si todavía no hay mecanismo escogido, lo que falta no son los datos de un escrito
    sino cerrar el triage: preguntar por la cédula antes de saber si hay riesgo vital es
    preguntar en el orden equivocado.
    """
    if ruta in DOCUMENTOS:
        return faltantes(campos, ruta)
    return [c for c in TRIAGE if not respondido(campos, c)], []
