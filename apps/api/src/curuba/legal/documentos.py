"""Qué escritos existen y cómo se llaman de cara al usuario.

Es el módulo que define el vocabulario del paquete: todo lo demás —campos, ruteo,
plantillas— se cuelga de esta tupla de cuatro.
"""

from __future__ import annotations

# El orden es el de la ruta: de lo más liviano a lo más pesado.
DOCUMENTOS = ("peticion", "tutela", "desacato", "supersalud")

NOMBRES = {
    "peticion": "Derecho de petición",
    "tutela": "Acción de tutela",
    "desacato": "Incidente de desacato",
    "supersalud": "Demanda ante la Superintendencia Nacional de Salud",
}

# El PQRD ante la Supersalud NO es uno de los cuatro escritos porque no es un escrito:
# es una línea telefónica y un formulario web. Por eso está acá como dato y no como
# plantilla. Verificados el 2026-07-24 contra supersalud.gov.co; cuando cambien, se
# cambian en este solo lugar y no regados por el prompt.
SUPERSALUD_CANALES = (
    "Línea gratuita nacional 01 8000 513 700; en Bogotá 601 483 7000 opción 5; "
    "formulario web de PQRD en supersalud.gov.co; correo radicacion@supersalud.gov.co."
)

# ── El escalón anterior al primer escrito ─────────────────────────────────
#
# Resolución 1604 de 2013 (MinSalud), que reglamenta el art. 131 del Decreto-Ley 019 de
# 2012: cuando la EPS o el gestor farmacéutico no pueda entregar completo al momento de
# la reclamación, debe entregar lo pendiente en máximo 48 HORAS, en el lugar de
# residencia o trabajo, **si el afiliado lo autoriza**.
#
# Es el único derecho de este paquete que se ejerce DE PIE EN EL MOSTRADOR, en dos
# minutos, sin radicar nada — y el que produce la prueba de la que dependen los cuatro
# escritos. Perder ese momento es perder la constancia, y sin constancia la petición y la
# tutela llegan sin con qué acreditar los hechos.
#
# Son 48 horas CORRIDAS, no hábiles. No confundir con los 15 días hábiles del art. 14 de
# la Ley 1755, que es otro plazo, de otra norma y de otro escalón.
PLAZO_DOMICILIO_HORAS = 48

MOSTRADOR = (
    "1) Pide que te dejen POR ESCRITO que no te lo entregaron, con la fecha, qué "
    "medicamento faltó y por qué. Puede ser un papel sellado o un correo; sirve una foto. "
    "Esa constancia es la prueba de todo lo que venga después.\n"
    "2) Di que AUTORIZAS que te lo lleven a tu casa y que quede registrado. La "
    "autorización tiene que ser expresa: si no queda por escrito, después la EPS puede "
    "decir que nunca se activó el domicilio.\n"
    "3) Anota la fecha y la hora exactas en que reclamaste. El plazo corre desde que TÚ "
    "reclamas, no desde que la EPS decida."
)

# Va al pie de las cuatro plantillas, en todas las páginas. No se quita.
AVISO = (
    "Documento generado por Curuba. Es un BORRADOR y debe revisarse antes de radicarse. "
    "Curuba no da asesoría jurídica ni médica."
)
