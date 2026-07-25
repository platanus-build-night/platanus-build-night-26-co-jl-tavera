"""Lo que las tools necesitan saber de la conversación.

Vive en su propio módulo para romper el ciclo: `agent.py` importa las tools, así que las
tools no pueden importar de `agent.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Deps:
    """El contexto de una corrida del agente.

    `adjunto` sale al revés que el resto: lo escribe `generar_documento` y lo lee
    `agent.responder()` cuando la corrida termina. Es la forma de que el PDF viaje como
    archivo adjunto de WhatsApp y no como un enlace pelado dentro del texto.

    `coberturas_consultadas` es el candado del orden de consulta: `consultar_cobertura`
    anota lo que buscó y `precio_en_drogueria` se niega si el conjunto está vacío. Está
    en código y no solo en el prompt porque es la regla que más plata ahorra —
    "¿cuánto vale el adalimumab?" contestado de frente manda a alguien a gastar $800.000
    que la EPS tenía que ponerle.
    """

    wa_id: str
    adjunto: str | None = None
    coberturas_consultadas: set[str] = field(default_factory=set)
