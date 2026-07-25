"""Las tools de medicamentos: PBS, SISMED, INVIMA y la red de seguridad en la web.

Las tres primeras leen las bases y devuelven `encontrado` y `nota` aparte de los
candidatos. No es adorno: es la forma de que "no lo encontré" no se pueda confundir con
"la respuesta es no". Y el significado de cada estado se traduce **acá, en Python**, no
se deja a interpretación del modelo — `mipres` NO es "cómprelo usted".

El INVIMA no espera a que el modelo lo pida: `_con_invima` lo pega a la cobertura y al
precio, así que toda consulta de un medicamento trae su estado de abastecimiento. Quien
pregunta por la cobertura no sabe que el desabastecimiento se pregunta aparte, y es
justo lo que explica por qué no se lo entregan.

Las dos últimas salen a Perplexity Sonar cuando las bases no alcanzan. La maquinaria de
esa búsqueda vive en `web.py`; acá quedan las tools porque el tema es el mismo.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.toolsets import FunctionToolset

from curuba import db
from curuba.tools import web
from curuba.tools.deps import Deps

medicamentos = FunctionToolset()

# Qué significa cada cobertura del PBS, en palabras que el modelo pueda repetir. La
# distinción que importa: `mipres` NO es "no cubierto" — son 420 filas y leerlas al revés
# manda a alguien a pagar de su bolsillo algo a lo que tiene derecho.
COBERTURAS = {
    "upc": "Financiado con la UPC: la EPS tiene que entregarlo en su dispensador. "
           "El paciente solo paga la cuota moderadora.",
    "condicionada": "Financiado con la UPC solo si se cumple el criterio que está en "
                    "'aclaracion'. Hay que leerle ese criterio al paciente tal cual.",
    "mipres": "No se financia con la UPC, pero NO significa que le toque comprarlo: se "
              "prescribe por la vía MIPRES y la EPS igual debe entregarlo. El paciente "
              "tiene que pedirle al médico que se lo formule por MIPRES.",
    "excluido": "Excluido de la financiación con recursos públicos. Este sí le toca "
                "comprarlo, salvo que un juez ordene lo contrario.",
    None: "La fuente no trae el dato de cobertura para este medicamento.",
}

ESTADOS = {
    "monitorizacion": "El INVIMA lo tiene en monitorización: hay señales de problemas de "
                      "abastecimiento pero todavía no está declarado desabastecido.",
    "riesgo": "En riesgo de desabastecimiento según el INVIMA.",
    "desabastecido": "Declarado DESABASTECIDO por el INVIMA.",
    "no_desabastecido": "El INVIMA le hizo seguimiento y CERRÓ el caso: hoy no está "
                        "desabastecido. Ojo, esto no es lo mismo que 'no hay reportes'.",
    None: "La fuente no trae el estado de esta fila.",
}

# Cuáles de esos estados son noticia para el paciente. Se decide acá y no en el prompt
# porque ahora el INVIMA llega en TODAS las consultas: sin este filtro el modelo
# terminaría contándole a alguien que preguntó un precio que su medicamento tuvo un
# seguimiento cerrado hace ocho meses. `no_desabastecido` son 373 de las 783 filas.
ALERTAS = {"desabastecido", "riesgo", "monitorizacion"}


# Los tres cuerpos van en helpers y no dentro de las tools porque
# `identificar_medicamento` los vuelve a llamar con el nombre ya resuelto. Así el
# contrato de lo que devuelve cada fuente queda garantizado por construcción: no hay dos
# versiones del mismo diccionario que se puedan desincronizar.

async def _cobertura(nombre: str) -> dict[str, Any]:
    filas = await db.buscar_cobertura(nombre)
    if not filas:
        return {
            "encontrado": False,
            "nota": "No aparece en el listado del PBS. Eso NO quiere decir que no esté "
                    "cubierto: el listado no es exhaustivo. Dile que lo confirme con su "
                    "EPS antes de comprarlo. Y si lo que te dijeron parece una marca "
                    "comercial y no un principio activo, `identificar_medicamento` la "
                    "traduce y vuelve a buscar por ti.",
            "candidatos": [],
        }
    return {
        "encontrado": True,
        "candidatos": [
            {
                "principio_activo": f["principio_activo"],
                "cobertura": f["cobertura"],
                "significado": COBERTURAS.get(f["cobertura"], COBERTURAS[None]),
                "aclaracion": f["aclaracion"],
                "score": float(f["score"]),
            }
            for f in filas
        ],
    }


async def _precio(nombre: str) -> dict[str, Any]:
    filas = await db.buscar_medicamento(nombre)
    if not filas:
        return {
            "encontrado": False,
            "nota": "No está en la tabla de precios regulados. Eso significa que no está "
                    "bajo control directo de precios (la mayoría no lo está), no que no "
                    "exista ni que haya fallado la consulta. El acetaminofén, por "
                    "ejemplo, no está en SISMED.",
            "candidatos": [],
        }
    return {
        "encontrado": True,
        "advertencia": "Ninguno de estos dos precios es lo que cobra un mostrador. El "
                       "institucional es el techo para EPS e IPS; el comercial es el "
                       "techo mayorista hasta la droguería. La venta al consumidor final "
                       "no está regulada en Colombia.",
        "candidatos": [
            {
                "descripcion": f["descripcion"],
                "laboratorio": f["laboratorio"],
                "precio_maximo_institucional": int(f["precio_institucional"]),
                "precio_maximo_canal_comercial": (
                    int(f["precio_comercial"]) if f["precio_comercial"] else None
                ),
                "contenido": f"{f['cantidad']} {f['unidad']}" if f["cantidad"] else None,
                "score": float(f["score"]),
            }
            for f in filas
        ],
    }


async def _desabasto(nombre: str, limite: int = 8) -> dict[str, Any]:
    filas = await db.consultar_desabastecimiento(nombre, limite)
    if not filas:
        return {
            "encontrado": False,
            "hay_alerta": False,
            "nota": "No hay reportes del INVIMA sobre este medicamento. No es lo mismo "
                    "que el estado 'no desabastecido', que sí es un caso que el INVIMA "
                    "revisó y cerró. No es noticia: no se lo menciones si no preguntó.",
            "candidatos": [],
        }
    candidatos = [
        {
            "nombre": f["nombre"],
            "estado": f["estado"],
            "significado": ESTADOS.get(f["estado"], ESTADOS[None]),
            "fecha_ultimo_seguimiento": (
                f["fecha_seguimiento"].isoformat() if f["fecha_seguimiento"] else None
            ),
            "score": float(f["score"]),
        }
        for f in filas
    ]
    # `hay_alerta` es la señal de si esto se cuenta o no. Que el modelo no tenga que
    # deducir de `estado` cuál merece interrumpir la respuesta.
    #
    # Se mira SOLO el mejor score, no todos los candidatos: "acetaminofén 500 mg" trae
    # PARACETAMOL (ACETAMINOFÉN) TABLETA 500 mg en 0,74 con el caso cerrado, y detrás una
    # presentación distinta en 0,65 que sí está en monitorización. Con `any()` sobre los
    # tres, la alerta se prendía en casi toda consulta y el filtro no filtraba nada.
    mejor = max(c["score"] for c in candidatos)
    return {
        "encontrado": True,
        "hay_alerta": any(
            c["estado"] in ALERTAS for c in candidatos if c["score"] >= mejor
        ),
        "candidatos": candidatos,
    }


async def _con_invima(
    nombre: str, consulta: Callable[[str], Awaitable[dict[str, Any]]]
) -> dict[str, Any]:
    """Le pega el estado del INVIMA a una consulta de medicamento.

    Las dos van en paralelo — son dos conexiones del pool — así que el desabastecimiento
    no le cuesta tiempo a la respuesta. Va acá y no en el prompt porque el que pregunta
    "¿me lo cubre la EPS?" no sabe que el desabastecimiento se pregunta aparte, y es
    justo lo que explica por qué no se lo van a entregar.

    Pide solo 3 candidatos: esto viaja en cada turno de la conversación y 8 filas del
    INVIMA por medicamento —en una fórmula son cuatro— es ruido, no información.
    """
    base, invima = await asyncio.gather(consulta(nombre), _desabasto(nombre, limite=3))
    return base | {"desabastecimiento": invima}


# ── Las tools ─────────────────────────────────────────────────────────────

@medicamentos.tool
async def consultar_cobertura(ctx: RunContext[Deps], nombre: str) -> dict[str, Any]:
    """Dice si un medicamento lo financia la EPS con la UPC. ÚSALA PRIMERO.

    Es la pregunta que más plata le ahorra al paciente: si está financiado, lo reclama en
    el dispensador de su EPS en vez de comprarlo.

    Trae además el estado del INVIMA en `desabastecimiento`: no tienes que llamar
    `consultar_desabastecimiento` por este medicamento.

    Args:
        nombre: el principio activo o el nombre que dijo el paciente, tal cual.
    """
    # Queda anotado para que `precio_en_drogueria` sepa que ya se preguntó lo primero.
    ctx.deps.coberturas_consultadas.add(nombre.strip().lower())
    return await _con_invima(nombre, _cobertura)


@medicamentos.tool_plain
async def buscar_medicamento(nombre: str) -> dict[str, Any]:
    """Busca el precio máximo regulado de un medicamento en el SISMED.

    El precio es el techo del canal institucional, NO lo que cobra una droguería. Solo
    están los medicamentos bajo control directo de precios, que son una minoría.

    Trae además el estado del INVIMA en `desabastecimiento`: no tienes que llamar
    `consultar_desabastecimiento` por este medicamento.

    Args:
        nombre: el nombre o principio activo, como lo escribió el paciente.
    """
    return await _con_invima(nombre, _precio)


@medicamentos.tool_plain
async def consultar_desabastecimiento(nombre: str) -> dict[str, Any]:
    """Dice si el INVIMA tiene un medicamento en seguimiento por desabastecimiento.

    Úsala solo si el paciente pregunta directamente por el abastecimiento y todavía no
    has consultado ese medicamento: `consultar_cobertura` y `buscar_medicamento` ya te
    devuelven este mismo dato adentro.

    Args:
        nombre: el nombre o principio activo, como lo escribió el paciente.
    """
    return await _desabasto(nombre)


@medicamentos.tool
async def identificar_medicamento(ctx: RunContext[Deps], nombre: str) -> dict[str, Any]:
    """Traduce una marca comercial a su principio activo y vuelve a consultar las 3 bases.

    Úsala cuando `consultar_cobertura` no encontró nada y lo que dijo el paciente parece
    el nombre de una marca ("Dolex", "Noxpirin", "Winadeine") y no un principio activo.
    Busca en la web, y con lo que encuentra repite las tres consultas por ti: no tienes
    que volver a llamarlas.

    Args:
        nombre: la marca tal como la escribió el paciente.
    """
    ident = await web.identificar(nombre, usage=ctx.usage)
    if ident is None:
        return {
            "encontrado": False,
            "nota": "La búsqueda en la web falló o se demoró demasiado. No inventes el "
                    "principio activo: dile que no pudiste confirmarlo y pídele que te "
                    "lea la caja o la fórmula.",
        }
    if not ident.principio_activo:
        return {
            "encontrado": False,
            "nota": f"No se encontró ningún medicamento que se llame {nombre!r}. "
                    "Pregúntale si lo escribió como aparece en la caja.",
        }

    # Una marca del mismo nombre puede traer otra composición en otro país. Darle la
    # cobertura colombiana de un producto mexicano es peor que no darle nada.
    if "colombia" not in ident.pais.strip().lower():
        return {
            "encontrado": False,
            "principio_activo": ident.principio_activo,
            "pais": ident.pais,
            "nota": f"Esa marca se encontró en {ident.pais}, no en Colombia. Las marcas "
                    "se repiten entre países con composiciones distintas, así que NO uses "
                    "este principio activo. Pídele que te lea el principio activo de la "
                    "caja.",
        }

    activo = ident.principio_activo
    cobertura = await _cobertura(activo)

    # Los combinados a veces no matchean enteros pero sus componentes sí, y cada
    # componente puede tener una cobertura distinta. Partir es más útil que rendirse.
    componentes = {}
    if not cobertura["encontrado"] and " + " in activo:
        for parte in activo.split(" + "):
            if (sub := await _cobertura(parte.strip()))["encontrado"]:
                componentes[parte.strip()] = sub

    return {
        "encontrado": True,
        "principio_activo": activo,
        "marca": ident.marca,
        "pais": ident.pais,
        "confianza": ident.confianza,
        "fuentes": ident.fuentes,
        "nota": (
            "Esto salió de una búsqueda web, no del INVIMA. "
            + ("Con `confianza: baja` NO des la cobertura como un hecho: dile qué "
               "encontraste y pídele que te confirme el principio activo de la caja."
               if ident.confianza == "baja" else
               "Di de qué marca se trata cuando le contestes, para que él confirme que "
               "es la suya.")
        ),
        "cobertura": cobertura,
        "cobertura_por_componente": componentes or None,
        "precio_regulado": await _precio(activo),
        "desabastecimiento": await _desabasto(activo),
    }


@medicamentos.tool
async def precio_en_drogueria(ctx: RunContext[Deps], nombre: str) -> dict[str, Any]:
    """Busca en la web cuánto cuesta un medicamento en La Rebaja, Farmatodo y Cruz Verde.

    Es lo que una cadena publica hoy en su página, NO un precio regulado. Úsala solo
    cuando el paciente pregunte por el precio de la droguería, y siempre después de
    consultar la cobertura.

    Args:
        nombre: el medicamento con su concentración, por ejemplo "losartán 50 mg".
    """
    if not ctx.deps.coberturas_consultadas:
        raise ModelRetry(
            "Antes de un precio de mostrador tienes que consultar la cobertura con "
            "`consultar_cobertura`. Si está financiado con la UPC, darle el precio de la "
            "droguería lo manda a gastar plata que la EPS tenía que ponerle. Consulta la "
            "cobertura primero y después vuelve a llamarme."
        )

    ofertas = await web.precios_drogueria(nombre, usage=ctx.usage)
    if not ofertas:
        return {
            "encontrado": False,
            "nota": "No se encontró el producto en las páginas de las tres cadenas. Dile "
                    "que no lograste confirmar el precio y que llame a la droguería. NO "
                    "estimes un precio ni uses el techo regulado como si lo fuera.",
            "candidatos": [],
        }
    return {
        "encontrado": True,
        "advertencia": "Esto NO es un techo regulado: es lo que una cadena publica hoy en "
                       "su sitio, y cambia por sede, presentación y promoción. Va con el "
                       "nombre de la cadena y como referencia — nunca 'cuesta $X'. Y que "
                       "una droguería cobre más que el techo institucional NO es ilegal.",
        "candidatos": [
            {
                "cadena": o.cadena,
                # La presentación va SIEMPRE: sin ella el paciente no puede saber si el
                # precio es de su caja o de una de otro tamaño, que es la confusión más
                # fácil y la más cara.
                "presentacion": o.producto,
                "precio": o.precio,
                "fuente": o.fuente,
                **({} if o.precio is not None else {
                    "sin_precio": "La página no mostraba precio o el valor no era "
                                  "plausible. Di que ahí lo venden, sin cifra."
                }),
            }
            for o in ofertas
        ],
    }
