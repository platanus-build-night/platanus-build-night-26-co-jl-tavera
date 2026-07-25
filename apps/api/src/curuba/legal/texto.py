"""Normalización de lo que escribe la gente.

Vive solo en un módulo porque lo usan las fechas, los campos, el ruteo y las
plantillas: es la raíz del paquete y no depende de nada.
"""

from __future__ import annotations


def normalizar(texto: object) -> str:
    """Minúsculas, sin espacios de sobra. **No quita tildes** a propósito.

    Las comparaciones contra tildes se hacen por prefijo (`"julio"[:4]`), que es más
    barato que arrastrar `unicodedata` acá — y en Postgres ya hay `curuba_norm` para
    lo que sí necesita quitarlas.
    """
    return " ".join(str(texto or "").strip().lower().split())
