"""Lo que comparten los cuatro escritos.

El marcado que producen las plantillas es mínimo a propósito, para que `pdf.py` no
tenga que entender nada más:

    `# TÍTULO`    el título del documento, centrado
    `## SECCIÓN`  un encabezado
    resto         cuerpo justificado; los bloques con saltos simples van a la izquierda

Los párrafos se separan con una línea en blanco.
"""

from __future__ import annotations

from curuba.legal.campos import CAMPOS, es_no, respondido
from curuba.legal.documentos import PLAZO_DOMICILIO_HORAS
from curuba.legal.fechas import corridos_desde, fecha_larga, leer_fecha


def valor(campos: dict, nombre: str) -> str:
    """El valor del campo, o un marcador visible si falta.

    Que el hueco se vea es la mitad del diseño: el PDF sale igual con datos faltantes
    —para no trancar una entrevista de catorce preguntas— pero quien lo radique tiene
    que ver exactamente qué le falta llenar.
    """
    crudo = str(campos.get(nombre, "") or "").strip()
    return crudo or f"[COMPLETAR: {CAMPOS[nombre].marcador}]"


def fecha(campos: dict, nombre: str) -> str:
    """La fecha en letras. Si no se parsea va tal cual, que es mejor que borrarla."""
    dia = leer_fecha(campos.get(nombre, ""))
    if dia:
        return fecha_larga(dia)
    return valor(campos, nombre)


def bloques(*partes: str) -> str:
    """Junta párrafos saltándose los vacíos.

    Es lo que permite escribir los bloques condicionales como `"" if not es_si(...)`
    sin que el documento quede con huecos dobles donde no aplicaron.
    """
    return "\n\n".join(p.strip() for p in partes if p and p.strip())


def encabezado_persona(campos: dict) -> str:
    """La fórmula de comparecencia, idéntica en los cuatro escritos."""
    return (
        f"{valor(campos, 'nombre')}, mayor de edad, identificado(a) con cédula de "
        f"ciudadanía número {valor(campos, 'cedula')}, domiciliado(a) en "
        f"{valor(campos, 'ciudad')}, afiliado(a) a {valor(campos, 'eps')}"
    )


def notificaciones(campos: dict) -> str:
    """Bloque de notificaciones y firma. Cierra los cuatro escritos."""
    correo = str(campos.get("correo", "") or "").strip()
    linea_correo = f"Correo electrónico: {correo}\n" if correo else ""
    return (
        "## NOTIFICACIONES\n"
        f"Dirección: {valor(campos, 'direccion')}, {valor(campos, 'ciudad')}\n"
        f"Teléfono: {valor(campos, 'telefono')}\n"
        f"{linea_correo}"
        "\n\n\n"
        "_______________________________________\n"
        f"{valor(campos, 'nombre')}\n"
        f"C.C. {valor(campos, 'cedula')}"
    )


def dispensador(campos: dict) -> str:
    """Dónde le toca reclamar. Si no lo sabe, una fórmula genérica que igual sirve."""
    gestor = str(campos.get("gestor_farmaceutico", "") or "").strip()
    return gestor or "el punto de dispensación asignado por la EPS"


def hechos_del_mostrador(campos: dict) -> tuple[str, str]:
    """Los dos hechos que salen de la Resolución 1604: constancia y 48 horas.

    Van juntos porque salen del mismo momento y de la misma norma, y los usan tanto la
    petición como la tutela. Cada uno es "" cuando no aplica, para que `bloques` lo
    salte y el escrito no quede con huecos.
    """
    constancia = ""
    if es_no(campos, "constancia"):
        constancia = (
            "Solicité que se me expidiera constancia escrita de la no entrega y no me fue "
            "entregada, con lo cual la entidad dificulta la prueba de la propia falla que "
            "generó."
        )

    incumplimiento = ""
    reclamo = leer_fecha(campos.get("fecha_reclamacion", ""))
    if reclamo and corridos_desde(reclamo) * 24 >= PLAZO_DOMICILIO_HORAS:
        dias = corridos_desde(reclamo)
        incumplimiento = (
            f"Han transcurrido {dias} días calendario desde la reclamación, de modo que "
            f"el plazo máximo de {PLAZO_DOMICILIO_HORAS} horas previsto en la Resolución "
            "1604 de 2013 para la entrega de lo pendiente se encuentra ampliamente "
            "vencido, sin que la entidad haya cumplido."
        )

    return constancia, incumplimiento


def si_esta(campos: dict, nombre: str, plantilla: str) -> str:
    """El texto con el campo interpolado, o vacío si el campo no está respondido.

    Ahorra el `if respondido(...) else ""` repetido en las cuatro plantillas.
    """
    if not respondido(campos, nombre):
        return ""
    return plantilla.format(valor=campos[nombre])
