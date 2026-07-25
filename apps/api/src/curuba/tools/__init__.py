"""Las tools del agente, agrupadas por tema.

Un `FunctionToolset` por grupo en vez de `@agente.tool` suelto en `agent.py`: así las
tools no importan al agente y el agente no importa a las tools de a una — se rompe el
ciclo y agregar un grupo nuevo es un archivo y un renglón en `TOOLSETS`.

    medicamentos   PBS, SISMED e INVIMA — leen datos, no tienen estado
    ruta_legal     la entrevista y la generación de los cuatro escritos

Para agregar un grupo: crear el módulo con su `FunctionToolset`, importarlo acá y
sumarlo a `TOOLSETS`. No hay que tocar `agent.py`.
"""

from __future__ import annotations

from curuba.tools.deps import Deps
from curuba.tools.medicamentos import medicamentos
from curuba.tools.ruta_legal import ruta_legal

TOOLSETS = [medicamentos, ruta_legal]

__all__ = ["Deps", "TOOLSETS", "medicamentos", "ruta_legal"]
