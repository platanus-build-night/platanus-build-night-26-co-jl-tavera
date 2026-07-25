"""Fechas y días hábiles.

Dos cosas que parecen utilidades y son reglas de negocio: **de qué fecha se cuenta** y
**cuántos días hábiles lleva la EPS**, porque de eso depende que `decidir_ruta` sepa si
ya está en mora.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from curuba.legal.texto import normalizar

# Los meses van en una constante y no salen de strftime('%B'): esa sigue el locale del
# sistema y en el contenedor de Railway devuelve inglés — "24 de July de 2026".
MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

# Ley 1755 de 2015, art. 14: 15 días hábiles para resolver de fondo, 10 para peticiones
# de documentos e información.
PLAZO_PETICION = 15

_FORMATOS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d")

# "2 de julio de 2026", "2 de julio del 2026", "2 julio 2026".
_EN_LETRAS = re.compile(r"\b(\d{1,2})\s*(?:de\s+)?([a-záéíóú]+)\s*(?:de[l]?\s+)?(\d{4})\b")


def leer_fecha(texto: str) -> date | None:
    """Parsea las fechas que escribe la gente. None si no se entiende.

    Tiene que entender **las fechas en letras**, no solo las numéricas: por WhatsApp
    nadie escribe "2026-07-02", escriben "el 2 de julio". Y no es cosmético — de
    `peticion_fecha` depende que el ruteo sepa si la EPS ya está en mora, así que una
    fecha que no se parsea deja el triage colgado repreguntando lo mismo.
    """
    limpio = normalizar(texto)
    if not limpio:
        return None

    for formato in _FORMATOS:
        try:
            return datetime.strptime(limpio, formato).date()
        except ValueError:
            continue

    coincidencia = _EN_LETRAS.search(limpio)
    if coincidencia:
        dia, mes, anio = coincidencia.groups()
        # Cuatro caracteres alcanzan para distinguir los doce meses (marz/mayo,
        # juni/juli) y sobreviven a que el usuario escriba con tilde o sin ella.
        for indice, nombre in enumerate(MESES, start=1):
            if mes.startswith(nombre[:4]) or nombre.startswith(mes[:4]):
                try:
                    return date(int(anio), indice, int(dia))
                except ValueError:
                    return None
    return None


def fecha_larga(dia: date | None = None) -> str:
    """'24 de julio de 2026', siempre en español pase lo que pase con el locale."""
    dia = dia or date.today()
    return f"{dia.day} de {MESES[dia.month - 1]} de {dia.year}"


def corridos_desde(inicio: date, hasta: date | None = None) -> int:
    """Días CORRIDOS transcurridos. Fines de semana incluidos.

    Hermana de `habiles_desde` y hay que tener claro cuál va en cada caso, porque
    mezclarlas es el error fácil de este archivo:

        corridos  -> las 48 horas del domicilio (Resolución 1604 de 2013)
        hábiles   -> los 15 días de la petición (art. 14 de la Ley 1755 de 2015)

    Las 48 h de la Res. 1604 no se suspenden el fin de semana: a alguien que reclamó un
    viernes le vencen el domingo, no el martes. Contarlas como hábiles le regalaría a la
    EPS dos días que la norma no le da.
    """
    hasta = hasta or date.today()
    return max(0, (hasta - inicio).days)


def habiles_desde(inicio: date, hasta: date | None = None) -> int:
    """Días hábiles transcurridos, contando de lunes a viernes.

    OJO: **no tiene el calendario de festivos de Colombia**, que son ~18 al año y se
    mueven con la Ley Emiliani. Sin ellos la cuenta sobreestima: un festivo dentro de la
    ventana se cuenta como hábil y el plazo parece vencido un día antes de lo real. Por
    eso quien la usa compara con `>` y no con `>=`, que deja un día de colchón.
    """
    hasta = hasta or date.today()
    if hasta <= inicio:
        return 0
    dias = 0
    cursor = inicio
    while cursor < hasta:
        cursor = date.fromordinal(cursor.toordinal() + 1)
        if cursor.weekday() < 5:
            dias += 1
    return dias
