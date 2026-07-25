"""La red de seguridad: buscar en la web lo que no está en las tres bases.

No es un toolset. Acá vive solo la maquinaria de hablar con Perplexity Sonar —el
sub-agente, los esquemas, las preguntas y las validaciones— y las tools que la usan
están en `medicamentos.py`, que es donde va el tema. La razón de partirlo: nada de esto
tiene que ver con las queries a Postgres, y mezclarlo dejaba un módulo que hacía dos
cosas muy distintas.

**Python es dueño de la pregunta.** El modelo nunca redacta lo que se le pregunta a
Sonar: pasa un nombre de medicamento y estas funciones arman el resto. Es lo mismo que
hacen `COBERTURAS` y `ESTADOS` con el significado de cada estado — lo que tiene
consecuencia no se deja a interpretación.

Tres cosas que se verificaron contra el endpoint y que mandan sobre el diseño:

1. **`perplexity/sonar` no soporta tool calling ni `response_format`.** Sus
   `supported_parameters` en OpenRouter son solo `max_tokens`, `temperature`, `top_p`,
   `top_k`, `frequency_penalty`, `presence_penalty` y `web_search_options`. Y el default
   de Pydantic AI para ese slug es structured output en modo `tool`, así que un
   `output_type` pelado le manda `tools` a un endpoint que no los tiene. Por eso va
   `PromptedOutput`, que mete el esquema en el prompt y parsea el texto. No es el plan B.

2. **Las citas no se pueden sacar del transporte.** OpenRouter sí las manda como
   `annotations`, y `pydantic_ai` hasta las parsea en `_OpenRouterCompletionMessage`,
   pero no las propaga al `ModelResponse`. Así que las URL se le piden a Sonar DENTRO
   del esquema y se validan acá.

3. **Sonar devuelve índices si no se le insiste.** La primera versión de la pregunta
   sacó `fuentes: ['1', '4', '5']` — los numeritos de las citas, no las URL. De ahí que
   la pregunta diga "URL COMPLETAS empezando por https://, NUNCA números".
"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel
from pydantic_ai import Agent, PromptedOutput
from pydantic_ai.usage import RunUsage, UsageLimits

from curuba import db
from curuba.config import settings

log = logging.getLogger("curuba")


class Identificacion(BaseModel):
    """Lo que se le pide a Sonar cuando el paciente dice una marca comercial."""

    principio_activo: str | None
    marca: str | None
    pais: str
    confianza: Literal["alta", "media", "baja"]
    fuentes: list[str]


class Oferta(BaseModel):
    cadena: str
    producto: str
    precio: int | None
    fuente: str


class Precios(BaseModel):
    encontrado: bool
    ofertas: list[Oferta]


# El sub-agente. Va aparte y SIN tools: Sonar no las soporta, y reusar el agente
# principal con un `model=` override le arrastraría las siete al endpoint.
_sonar = Agent(
    settings.curuba_web_model,
    name="curuba-web",
    output_type=PromptedOutput(Identificacion),
    retries=1,
)

# Los precios van en DOS pasos y no en uno, y esto no es gratuito — se midió.
#
# `PromptedOutput` mete el esquema JSON dentro del mensaje del usuario, y Perplexity
# arma su búsqueda web a partir de ese mensaje. Con el esquema encima, la consulta que
# le llega al buscador queda diluida y Sonar contesta `encontrado: false` para losartán,
# acetaminofén e ibuprofeno — los tres. La MISMA pregunta en prosa, sin esquema, sí
# encuentra la ficha de Farmatodo con precio y URL.
#
# Así que el paso 1 le pregunta a Sonar en español plano (búsqueda limpia) y el paso 2
# le pasa esa prosa a Claude para estructurarla. Claude acá no busca nada ni decide
# nada: solo copia lo que ya está en el texto a los campos. Cuesta una llamada corta y
# ~1 s, y es la diferencia entre que la tool sirva y que no.
_sonar_plano = Agent(settings.curuba_web_model, name="curuba-web-precios")

_extractor = Agent(
    settings.curuba_model,
    name="curuba-extractor",
    output_type=Precios,
    retries=1,
    instructions="Copias datos de un texto a una estructura. No busques nada, no "
                 "completes lo que no esté y no conviertas monedas: si el texto no trae "
                 "el precio de una droguería, esa oferta no va o va con precio null.",
)

# Las tres cadenas que pidió el producto, en orden de prioridad. Se valida el host de
# cada URL contra esto: una "fuente" que no sea de una de las tres no se muestra.
# `larebaja` aparece con dos dominios según por dónde entre el buscador.
CADENAS = {
    "larebaja.com.co": "Drogas La Rebaja",
    "larebaja.co": "Drogas La Rebaja",
    "farmatodo.com.co": "Farmatodo",
    "cruzverde.com.co": "Cruz Verde",
}

# Banda de plausibilidad ABSOLUTA, en pesos. No se compara contra SISMED a propósito:
# el techo del SISMED es de OTRA presentación (la búsqueda es por similitud) y con otro
# tamaño de caja, así que el cruce da falsos positivos y falsos negativos por igual.
# Medido: "losartán 50" en SISMED solo trae ARAMAX, que es amlodipino + losartán, con
# cajas de 200/500/1500 mg — comparar eso contra una caja x30 de losartán solo no
# significa nada. Y "acetaminofén 500" no está en SISMED: cero filas.
#
# Lo que sí caza esta banda son los errores de orden de magnitud, que son los reales:
# un precio por tableta leído como precio de caja, o una cifra en otra moneda.
PRECIO_MIN = 500
PRECIO_MAX = 5_000_000

_PREGUNTA_IDENTIFICAR = """\
En COLOMBIA, ¿qué principio activo trae el medicamento de marca "{nombre}"?

Reglas para tu respuesta:
- `principio_activo`: el nombre genérico COMO SE ESCRIBE EN COLOMBIA, el que usan el
  INVIMA y el vademécum colombiano. Esto importa: en Colombia se dice ACETAMINOFÉN, no
  "paracetamol"; DIPIRONA, no "metamizol". En singular y sin dosis. Si el producto trae
  varios principios activos, sepáralos con " + ".
- `pais`: el país del que estás hablando. Si esa marca no se vende en Colombia, escribe
  el país donde sí se vende.
- `confianza`: "alta" si lo confirmaste en el INVIMA, en el fabricante o en un vademécum;
  "media" si solo lo viste en droguerías; "baja" si no estás seguro.
- `fuentes`: las URL COMPLETAS de donde lo sacaste, empezando por https://. NUNCA números
  ni referencias tipo [1].

Si "{nombre}" no es una marca de medicamento, deja `principio_activo` en null."""

# En prosa y corta a propósito: es la consulta con la que Perplexity arma su búsqueda.
# Cada línea de más acá adentro es ruido en el buscador. Ver el comentario de
# `_sonar_plano` sobre por qué el esquema JSON no puede ir en este mensaje.
_PREGUNTA_PRECIO = """\
¿Cuánto cuesta {nombre} en Farmatodo Colombia, Cruz Verde Colombia y Drogas La Rebaja?

Dame el precio en pesos colombianos de cada cadena donde lo encuentres, con el nombre y
la presentación del producto (marca, mg y unidades por caja) y la URL de la ficha. Con
una sola cadena ya sirve. Si no encuentras un precio publicado, dilo — no lo estimes."""

_EXTRAER_PRECIO = """\
De este texto, saca las ofertas de droguerías colombianas que traigan precio publicado.

Solo cuentan Drogas La Rebaja, Farmatodo y Cruz Verde. `precio` va en pesos colombianos
como entero sin puntos. Si el texto dice que no encontró precio en una cadena, esa no va.
`fuente` es la URL completa de la ficha del producto.

TEXTO:
{texto}"""


def _urls_validas(fuentes: list[str], solo_cadenas: bool = False) -> list[str]:
    """Deja solo las URL absolutas de verdad, y opcionalmente solo las de las 3 cadenas.

    Sin esto se cuelan los índices de cita ('1', '4') y los dominios inventados. Una
    fuente que no se puede abrir no es una fuente.
    """
    limpias = []
    for f in fuentes:
        try:
            u = urlparse(f.strip())
        except ValueError:
            continue
        if u.scheme not in ("http", "https") or not u.netloc:
            continue
        host = u.netloc.lower().removeprefix("www.")
        if solo_cadenas and host not in CADENAS:
            continue
        limpias.append(f.strip())
    return limpias


# Las dos funciones de abajo NUNCA levantan: una tool que revienta se convierte en el
# "Uy, algo se me dañó" del webhook, y perder la conversación entera porque Perplexity se
# demoró 30 s es inaceptable. Devuelven None o lista vacía y la tool lo traduce.

async def identificar(nombre: str, usage: RunUsage | None = None) -> Identificacion | None:
    """Marca comercial -> principio activo, con las degradaciones ya aplicadas."""
    clave = f"identificar:{nombre.strip().lower()}"
    if (guardado := await db.leer_cache_web(clave)) is not None:
        return Identificacion.model_validate(guardado)

    try:
        resultado = await asyncio.wait_for(
            _sonar.run(
                _PREGUNTA_IDENTIFICAR.format(nombre=nombre),
                usage=usage,
                usage_limits=UsageLimits(request_limit=3),
            ),
            timeout=settings.curuba_web_timeout,
        )
    except TimeoutError:
        log.warning("Sonar se pasó de %ss identificando %r", settings.curuba_web_timeout, nombre)
        return None
    except Exception:
        log.exception("falló identificando %r en la web", nombre)
        return None

    ident = resultado.output
    ident.fuentes = _urls_validas(ident.fuentes)

    # Las dos degradaciones las decide Python, no el modelo. Sin fuente que se pueda
    # abrir, un principio activo "con confianza alta" es una afirmación sobre salud sin
    # respaldo — y de un principio activo equivocado sale una cobertura equivocada.
    if not ident.fuentes:
        ident.confianza = "baja"

    # Un "no lo identifiqué" no se cachea, por lo mismo que en precios_drogueria: puede
    # haber sido un mal momento del buscador y no una marca que no existe.
    if ident.principio_activo:
        await db.guardar_cache_web(clave, ident.model_dump())
    return ident


async def precios_drogueria(nombre: str, usage: RunUsage | None = None) -> list[Oferta]:
    """Ofertas de las tres cadenas, ya filtradas por host y por banda de plausibilidad."""
    clave = f"drogueria:{nombre.strip().lower()}"
    if (guardado := await db.leer_cache_web(clave)) is not None:
        return [Oferta.model_validate(o) for o in guardado["ofertas"]]

    try:
        # Paso 1: Sonar busca y contesta en prosa.
        crudo = await asyncio.wait_for(
            _sonar_plano.run(
                _PREGUNTA_PRECIO.format(nombre=nombre),
                usage=usage,
                usage_limits=UsageLimits(request_limit=3),
            ),
            timeout=settings.curuba_web_timeout,
        )
        # Paso 2: Claude pasa esa prosa a la estructura. No busca ni completa nada.
        resultado = await asyncio.wait_for(
            _extractor.run(
                _EXTRAER_PRECIO.format(texto=crudo.output),
                usage=usage,
                usage_limits=UsageLimits(request_limit=3),
            ),
            timeout=settings.curuba_web_timeout,
        )
    except TimeoutError:
        log.warning("Sonar se pasó de %ss buscando el precio de %r",
                    settings.curuba_web_timeout, nombre)
        return []
    except Exception:
        log.exception("falló buscando el precio de %r", nombre)
        return []

    buenas = []
    for oferta in resultado.output.ofertas:
        if not _urls_validas([oferta.fuente], solo_cadenas=True):
            # Una oferta sin URL de una de las tres cadenas no se puede verificar, y un
            # precio que nadie puede verificar no se le da a un paciente.
            continue
        if oferta.precio is not None and not (PRECIO_MIN <= oferta.precio <= PRECIO_MAX):
            log.warning("precio fuera de banda para %r: %s", nombre, oferta.precio)
            oferta.precio = None
        buenas.append(oferta)

    # Solo se cachea lo que encontró algo. Guardar un "no encontré" deja pegado por una
    # semana lo que pudo ser un timeout o un mal día del buscador, y el paciente que
    # vuelve a preguntar mañana recibe el mismo vacío sin que nadie haya vuelto a buscar.
    if buenas:
        await db.guardar_cache_web(clave, {"ofertas": [o.model_dump() for o in buenas]})
    return buenas
