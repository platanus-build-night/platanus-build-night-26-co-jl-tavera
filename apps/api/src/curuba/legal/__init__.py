"""La ruta legal: qué mecanismo procede, con qué datos y con qué texto.

Cuatro escritos, no uno. La tutela es el último escalón de una ruta y **escoger mal el
escalón es el modo de falla real**: llevarle a la Supersalud un problema de entrega es
tocar una puerta que no tiene competencia (T-243/2016 y T-163/2018 excluyeron el
suministro y la entrega de medicamentos de su función jurisdiccional), y poner una tutela
sin haber reclamado nada antes la deja sin el radicado que la sostiene.

Por eso `decidir_ruta()` vive en Python y no en el prompt: lo que tiene consecuencia legal
se traduce acá y no se deja a interpretación del modelo.

El paquete se lee de abajo hacia arriba, cada módulo depende solo de los anteriores:

    texto        normalizar()
    documentos   los cuatro escritos, sus nombres, los canales de la Supersalud
    fechas       leer_fecha, habiles_desde  — el plazo que decide la ruta
    campos       CAMPOS, validar, qué falta
    ruteo        decidir_ruta  ← el corazón
    plantillas/  un archivo por escrito
    pdf          maquetación, no sabe de derecho

Quien lo usa desde afuera (las tools) importa de acá, no de los submódulos.
"""

from __future__ import annotations

from curuba.legal.campos import (
    CAMPOS,
    TRIAGE,
    Campo,
    aplica,
    es_no,
    es_si,
    faltantes,
    pendientes,
    respondido,
    validar,
)
from curuba.legal.documentos import (
    AVISO,
    DOCUMENTOS,
    NOMBRES,
    SUPERSALUD_CANALES,
)
from curuba.legal.fechas import (
    MESES,
    PLAZO_PETICION,
    fecha_larga,
    habiles_desde,
    leer_fecha,
)
from curuba.legal.pdf import marcadores, render_pdf
from curuba.legal.plantillas import PLANTILLAS, armar_texto
from curuba.legal.ruteo import RUTAS, decidir_ruta
from curuba.legal.texto import normalizar

__all__ = [
    "AVISO", "CAMPOS", "DOCUMENTOS", "MESES", "NOMBRES", "PLANTILLAS",
    "PLAZO_PETICION", "RUTAS", "SUPERSALUD_CANALES", "TRIAGE", "Campo",
    "aplica", "armar_texto", "decidir_ruta", "es_no", "es_si", "faltantes",
    "fecha_larga", "generar", "habiles_desde", "leer_fecha", "marcadores",
    "normalizar", "pendientes", "render_pdf", "respondido", "validar",
]


def generar(campos: dict, tipo: str) -> tuple[bytes, list[str]]:
    """El PDF y los marcadores que quedaron sin llenar.

    Es lo único que necesita la tool: arma el texto, lo maqueta y de paso reporta los
    huecos para que el agente los cante por chat.
    """
    texto = armar_texto(campos, tipo)
    return render_pdf(texto), marcadores(texto)
