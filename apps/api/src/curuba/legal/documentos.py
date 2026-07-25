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

# Va al pie de las cuatro plantillas, en todas las páginas. No se quita.
AVISO = (
    "Documento generado por Curuba. Es un BORRADOR y debe revisarse antes de radicarse. "
    "Curuba no da asesoría jurídica ni médica."
)
