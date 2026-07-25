"""Las cuatro plantillas, una por archivo.

Cada módulo expone `armar(campos) -> str` y devuelve texto con el marcado mínimo que
entiende `legal.pdf`. Agregar un escrito nuevo es: un archivo acá, una entrada en
`PLANTILLAS`, y una en `documentos.DOCUMENTOS` y `documentos.NOMBRES`.
"""

from __future__ import annotations

from collections.abc import Callable

from curuba.legal.plantillas import desacato, peticion, supersalud, tutela

PLANTILLAS: dict[str, Callable[[dict], str]] = {
    "peticion": peticion.armar,
    "tutela": tutela.armar,
    "desacato": desacato.armar,
    "supersalud": supersalud.armar,
}


def armar_texto(campos: dict, tipo: str) -> str:
    """El texto del escrito, ya con los bloques condicionales resueltos."""
    if tipo not in PLANTILLAS:
        raise ValueError(f"documento desconocido: {tipo}")
    return PLANTILLAS[tipo](campos)
