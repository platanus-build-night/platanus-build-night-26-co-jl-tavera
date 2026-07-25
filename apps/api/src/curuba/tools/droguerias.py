"""Los catálogos de las droguerías, por HTTP directo.

La misma pregunta que `web.py` —cuánto vale esto en el mostrador— pero sin pasar por un
buscador. Va aparte por lo mismo que `web.py` está aparte de `medicamentos.py`: es
maquinaria de transporte, no un toolset. La tool que usa esto sigue siendo
`precio_en_drogueria`.

**Por qué existe.** Preguntarle a un buscador cuánto cuesta un medicamento es apostarle a
lo que su crawler alcanzó a indexar de un SPA. Las dos cadenas de acá exponen su catálogo
en JSON, así que la respuesta es determinista y llega en menos de un segundo en vez de
5-25 s. Sonar no se botó: queda de respaldo en `precio_en_drogueria`, y es por donde Cruz
Verde todavía puede salir.

Tres cosas que se verificaron contra los endpoints y que mandan sobre el diseño:

1. **La Rebaja corre sobre VTEX** y su API de catálogo es pública, sin llave. Contesta
   `206 Partial Content`, no `200` — eso es normal en VTEX y `raise_for_status()` lo deja
   pasar. Ojo con el dominio: la tienda es `larebajavirtual.com`, no `larebaja.com.co`.

   Y los espacios de `ft` van como `%20`: con `+` —que es lo que arma `params=` de httpx,
   y lo que uno esperaría de un query string— VTEX contesta **400**. Por eso esa URL se
   construye a mano con `quote()` y no se le pasa `params`.

2. **Farmatodo busca contra un índice de Algolia.** El App ID va en MAYÚSCULAS
   (`VCOJEYD2PO`); en minúsculas el endpoint responde 403 aunque la llave esté bien.

3. **Los dos hacen match difuso y hay que filtrar acá.** `losartan 50 mg` en La Rebaja
   devuelve TRAZODONA y SILDENAFIL en las posiciones 2 y 3. Devolver eso es darle a un
   paciente el precio de otro medicamento, que es el peor error que puede cometer esto.
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from curuba import db
from curuba.config import settings
from curuba.tools.web import PRECIO_MAX, PRECIO_MIN, Oferta

log = logging.getLogger("curuba")

LAREBAJA = "https://www.larebajavirtual.com"

FARMATODO_HOST = "https://vcojeyd2po-dsn.algolia.net"
FARMATODO_APP_ID = "VCOJEYD2PO"
FARMATODO_INDICE = "products-colombia"
FARMATODO_FICHA = "https://www.farmatodo.com.co/producto/{id}"

# Cuántas ofertas de cada cadena se le pasan al modelo. Se piden 10 al catálogo y se
# recortan después de filtrar y ordenar: pedir menos deja por fuera la presentación
# correcta cuando el buscador la puso de quinta.
POR_CADENA = 3

# 8 s es de sobra: los dos catálogos contestan en ~300 ms y esto corre mientras alguien
# espera un WhatsApp.
#
# El cliente se abre y se cierra en cada `buscar()` a propósito. Uno a nivel de módulo
# reusaría la conexión, pero queda amarrado al event loop donde se usó primero y revienta
# con "Event loop is closed" en cualquier script que llame `asyncio.run()` más de una vez
# — que es justo como se prueba esto.
_HTTPX = {
    "timeout": 8.0,
    "follow_redirects": True,
    "headers": {"User-Agent": "Mozilla/5.0 (compatible; Curuba/1.0)"},
}


# ── El filtro de relevancia ───────────────────────────────────────────────

def _normalizar(texto: str) -> str:
    """Minúsculas y sin tildes: 'Losartán Potásico' y 'LOSARTAN POTASICO' son lo mismo."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _tokens(consulta: str) -> tuple[list[str], list[str]]:
    """Las palabras que el producto TIENE que traer, y los números que decide el orden.

    Se exigen las palabras de 4 letras o más para no filtrar por 'mg' ni por 'de'. Si la
    consulta no tiene ninguna tan larga ('ASA 100'), se baja a 3 antes de rendirse: quedarse
    sin tokens es quedarse sin filtro, y sin filtro sale trazodona donde iba losartán.
    """
    norm = _normalizar(consulta)
    palabras = re.findall(r"[a-z]{4,}", norm) or re.findall(r"[a-z]{3,}", norm)
    return palabras, re.findall(r"\d+", norm)


def _filtrar(ofertas: list[Oferta], consulta: str) -> list[Oferta]:
    """Deja lo que de verdad es el medicamento que preguntaron, con la dosis de primera.

    La dosis ORDENA pero no filtra. Exigirla borraba resultados buenos —cada catálogo
    escribe la concentración a su manera— y no exigirla dejaba 'losartán 100' de primero
    cuando preguntaron por el de 50. Ordenar resuelve las dos: la presentación exacta sube,
    y lo demás sigue ahí con su `presentacion` a la vista.
    """
    palabras, numeros = _tokens(consulta)
    if not palabras:
        return ofertas[:POR_CADENA]

    buenas = [o for o in ofertas if all(p in _normalizar(o.producto) for p in palabras)]
    if numeros:
        buenas.sort(
            key=lambda o: sum(n in _normalizar(o.producto) for n in numeros), reverse=True
        )
    return buenas[:POR_CADENA]


def _precio_plausible(precio: Any, producto: str) -> int | None:
    """La misma banda absoluta de `web.py`: caza los errores de orden de magnitud."""
    if not precio:
        return None
    entero = int(precio)
    if not (PRECIO_MIN <= entero <= PRECIO_MAX):
        log.warning("precio fuera de banda para %r: %s", producto, entero)
        return None
    return entero


# ── Las dos cadenas ───────────────────────────────────────────────────────

async def _larebaja(cliente: httpx.AsyncClient, consulta: str) -> list[Oferta]:
    # La URL se arma a mano: `params=` codifica los espacios como `+` y VTEX da 400.
    respuesta = await cliente.get(
        f"{LAREBAJA}/api/catalog_system/pub/products/search"
        f"?ft={quote(consulta, safe='')}&_from=0&_to=9"
    )
    respuesta.raise_for_status()

    ofertas = []
    for producto in respuesta.json():
        # Los "kit" son multipacks y traen EL MISMO `productName` que la caja suelta, con
        # diez veces el precio: acetaminofén 500 sale a $2.500 y su kit a $24.600, los dos
        # como "ACETAMINOFEN 500 MG (GENFAR)". Dejarlos entrar le pone al paciente dos
        # precios idénticos en presentación y muy distintos en cifra — la confusión más
        # cara que puede haber acá. Se reconocen por el `linkText`.
        if producto.get("linkText", "").startswith("kit-"):
            continue
        items = producto.get("items") or []
        vendedores = (items[0].get("sellers") or [{}]) if items else [{}]
        comercial = vendedores[0].get("commertialOffer") or {}
        # Sin existencias no es una oferta: mandar a alguien a una droguería por algo que
        # el catálogo ya dice que no tiene es peor que no darle el dato.
        if not comercial.get("AvailableQuantity"):
            continue
        nombre = producto.get("productName") or ""
        ofertas.append(
            Oferta(
                cadena="Drogas La Rebaja",
                producto=nombre,
                precio=_precio_plausible(comercial.get("Price"), nombre),
                fuente=f"{LAREBAJA}/{producto['linkText']}/p",
            )
        )
    return ofertas


async def _farmatodo(cliente: httpx.AsyncClient, consulta: str) -> list[Oferta]:
    respuesta = await cliente.post(
        f"{FARMATODO_HOST}/1/indexes/{FARMATODO_INDICE}/query",
        headers={
            "X-Algolia-Application-Id": FARMATODO_APP_ID,
            "X-Algolia-API-Key": settings.curuba_farmatodo_key,
        },
        # Algolia recibe sus parámetros como un query string DENTRO del JSON.
        json={"params": urlencode({"query": consulta, "hitsPerPage": 10})},
    )
    respuesta.raise_for_status()

    ofertas = []
    for hit in respuesta.json().get("hits", []):
        nombre = hit.get("mediaDescription") or hit.get("largeDescription") or ""
        # `offerPrice` viene en 0 cuando no hay promoción, no en null.
        precio = hit.get("offerPrice") or hit.get("fullPrice")
        ofertas.append(
            Oferta(
                cadena="Farmatodo",
                producto=nombre,
                precio=_precio_plausible(precio, nombre),
                fuente=FARMATODO_FICHA.format(id=hit.get("id") or hit.get("objectID")),
            )
        )
    return ofertas


# ── Lo que usa la tool ────────────────────────────────────────────────────

async def buscar(nombre: str) -> list[Oferta]:
    """Las ofertas de las dos cadenas, ya filtradas por relevancia y por plausibilidad.

    NUNCA levanta, por lo mismo que las funciones de `web.py`: una tool que revienta se
    convierte en el "Uy, algo se me dañó" del webhook, y perder la conversación entera
    porque un catálogo ajeno se cayó es inaceptable. Devuelve `[]` y la tool lo traduce.
    """
    clave = f"droguerias_api:{nombre.strip().lower()}"
    if (guardado := await _cache_leer(clave)) is not None:
        return [Oferta.model_validate(o) for o in guardado["ofertas"]]

    # `return_exceptions` para que una cadena caída no se lleve a la otra: son dos sitios
    # independientes y media respuesta sirve.
    async with httpx.AsyncClient(**_HTTPX) as cliente:
        resultados = await asyncio.gather(
            _larebaja(cliente, nombre), _farmatodo(cliente, nombre), return_exceptions=True
        )

    ofertas: list[Oferta] = []
    for cadena, resultado in zip(("La Rebaja", "Farmatodo"), resultados):
        if isinstance(resultado, BaseException):
            log.warning("falló el catálogo de %s para %r: %s", cadena, nombre, resultado)
            continue
        ofertas.extend(_filtrar(resultado, nombre))

    # Solo se cachea lo que encontró algo, igual que en `web.precios_drogueria`: guardar un
    # "no encontré" deja pegado por una semana lo que pudo ser un mal momento del catálogo.
    if ofertas:
        await _cache_guardar(clave, {"ofertas": [o.model_dump() for o in ofertas]})
    return ofertas


# La caché es un acelerador, no un requisito. Si Postgres no está —un script suelto
# probando los dos catálogos, por ejemplo— la búsqueda igual tiene que salir.

async def _cache_leer(clave: str) -> dict | None:
    try:
        return await db.leer_cache_web(clave)
    except Exception:
        log.debug("sin caché para %r", clave, exc_info=True)
        return None


async def _cache_guardar(clave: str, valor: dict) -> None:
    try:
        await db.guardar_cache_web(clave, valor)
    except Exception:
        log.debug("no se pudo cachear %r", clave, exc_info=True)
