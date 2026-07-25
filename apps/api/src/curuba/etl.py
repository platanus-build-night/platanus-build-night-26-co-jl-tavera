"""Carga las tres fuentes de resources/data/ a Postgres.

    cd apps/api
    uv run python -m curuba.etl                  # las tres
    uv run python -m curuba.etl --solo pbs       # una sola
    uv run python -m curuba.etl --limite 100     # las primeras N filas, para iterar

Se corre en local contra la URL PÚBLICA de Railway, no en el deploy. Lee **tres CSV y
nunca un PDF**: el del INVIMA ya viene convertido por
`resources/data/scripts/extraer_invima.py`, que es de un solo uso y no es dependencia de
la API. Por eso acá no se importa pdfplumber ni pandas — con `csv` de la stdlib basta.

Las tres fuentes y qué contesta cada una:

    pbs       2.067 filas   ¿te lo tienen que dar en el dispensador de tu EPS?
    sismed   38.731 filas   si te toca comprarlo, ¿cuál es el techo regulado?
    invima      783 filas   ¿está en seguimiento por desabastecimiento?

Todo el SQL vive en db.py (regla del CLAUDE.md). Acá solo se parsea y se arman tuplas.
Las trampas de cada archivo están comentadas en el punto donde muerden; el panorama
completo está en resources/data/README.md.
"""

import argparse
import asyncio
import collections
import csv
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from curuba import db

# Anclado en __file__, no en el cwd: corre igual desde apps/api o desde la raíz.
#   src/curuba/etl.py -> curuba -> src -> api -> apps -> raíz del repo
DATA = Path(__file__).resolve().parents[4] / "resources" / "data"

# Los nombres de los archivos traen tildes y fecha de corte, y cambian cuando se
# actualiza el corte. Se buscan por glob para no tener que tocar esto cada mes — y de
# paso se evita que una tilde compuesta (NFD) contra una precompuesta (NFC) rompa la
# ruta según el sistema de archivos.
DIR_SISMED = DATA / "raw" / "sismed"
DIR_PBS = DATA / "raw" / "pbs"
CSV_INVIMA = DATA / "clean" / "desabastecimiento.csv"

# `strptime` con %b lee el mes según el locale del sistema: en el contenedor de Railway
# sale en inglés y en una máquina en español falla. Es la misma trampa que obliga a
# poner los meses del PDF de la tutela en una constante. Mapa explícito, sin locale.
MESES = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), start=1)}
RE_FECHA = re.compile(r"^(\d{4})\s+([A-Za-z]{3})\s+(\d{1,2})")

# Las cinco coberturas del PBS, tal cual vienen. Se comparan por igualdad sobre la
# cadena COMPLETA en minúscula, nunca por `in`: "financiado" es subcadena de
# "no financiado", igual que "desabastecido" lo es de "no desabastecido" (la trampa que
# ya marcó 373 filas del INVIMA justo al revés). Con un `in` ingenuo las 420 filas de
# MIPRES quedarían como financiadas por UPC y pasarían todos los chequeos en silencio.
COBERTURAS = {
    "financiado con recursos de la unidad de pago por capitación (upc)": "upc",
    "financiación condicionada con recursos de la unidad de pago por capitación (upc)": "condicionada",
    "no financiado con recursos de la unidad de pago por capitación (mipres)": "mipres",
    "excluido de la financiación con recursos públicos asignados a la salud.": "excluido",
    "sin dato": None,
}

# Conteos del corte commiteado. Si un número no cuadra, el mapeo se rompió en silencio.
ESPERADO = {"medications": 38731, "shortages": 783, "coverage": 2067}
ESPERADO_COBERTURA = {"upc": 1447, "mipres": 420, "condicionada": 193, "excluido": 6}


def _unico(carpeta: Path, patron: str = "*.csv") -> Path:
    encontrados = sorted(carpeta.glob(patron))
    if not encontrados:
        raise FileNotFoundError(f"no hay ningún {patron} en {carpeta}")
    if len(encontrados) > 1:
        raise RuntimeError(
            f"hay {len(encontrados)} archivos {patron} en {carpeta} y no se sabe cuál "
            f"cargar: {[f.name for f in encontrados]}. Dejar solo el corte vigente."
        )
    return encontrados[0]


def _leer(ruta: Path, limite: int | None) -> list[dict]:
    with open(ruta, encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))
    return filas[:limite] if limite else filas


def _numero(txt: str) -> Decimal | None:
    """Precio a Decimal. Devuelve None para 'No regulado' y para los vacíos.

    Dos detalles de la fuente: los números vienen en formato gringo, con coma de miles
    (`10,152` es diez mil ciento cincuenta y dos, no 10,152); y `No regulado` aparece con
    dos capitalizaciones distintas según la columna (`No Regulado` en la 10, `No regulado`
    en la 11), así que se compara en minúscula.
    """
    txt = (txt or "").strip()
    if not txt or txt.lower() == "no regulado":
        return None
    try:
        return Decimal(txt.replace(",", ""))
    except InvalidOperation:
        return None


def _fecha_sismed(txt: str) -> date | None:
    """`2024 Jul 31 12:00:00 AM` -> date(2024, 7, 31). Sin locale, ver MESES."""
    m = RE_FECHA.match((txt or "").strip())
    if not m:
        return None
    anio, mes, dia = m.groups()
    if (numero := MESES.get(mes.title())) is None:
        return None
    return date(int(anio), numero, int(dia))


def _fecha_iso(txt: str) -> date | None:
    txt = (txt or "").strip()
    try:
        return date.fromisoformat(txt) if txt else None
    except ValueError:
        return None


# ---- sismed

COLS_MEDICATIONS = [
    "cum", "id_mr", "principio_activo", "forma", "via", "nombre_comercial",
    "laboratorio", "descripcion", "cantidad", "unidad", "precio_institucional",
    "precio_comercial", "circular", "vigencia_desde",
]

# La 11 (`... transacción final comercial`) NO se guarda a propósito: dice `No regulado`
# en 38.624 de 38.731 filas y solo 3 traen un número. La venta al consumidor final no
# está regulada, así que no hay ningún techo que mostrarle al paciente por ese lado.
# `Margen para IPS` tampoco: es margen de IPS, no de droguerías, y no sirve para razonar
# sobre lo que cobra un mostrador.
COL_INSTITUCIONAL = ("Precio máximo de venta transacción primaria, "
                     "secundaria y final Institucional")
COL_COMERCIAL = ("Precio máximo de venta transacción primaria y "
                 "secundaria comercial")


def filas_sismed(crudas: list[dict], reporte: dict) -> list[tuple]:
    filas = []
    for f in crudas:
        cum = f["CUM"].strip()

        # `Mercado Relevante` trae SIEMPRE 3 segmentos (verificado en las 38.731), así
        # que acá sí se puede partir por posición.
        mr = [p.strip() for p in f["Mercado Relevante"].split(" - ")]
        if len(mr) != 3:
            reporte["mr_raro"].append((cum, f["Mercado Relevante"][:60]))
        principio, forma, via = (mr + ["", "", ""])[:3]

        # `Medicamento` varía entre 2 y 6 segmentos (5 en el 98,6 %). Primero y último,
        # NUNCA por índice: partir por posición mete el laboratorio en la columna
        # equivocada en las 551 filas que no traen 5.
        # 349 filas traen espacios dobles (`Adalimumab 40mg/0,8ml  - Líquido`). Se
        # colapsan: es lo que se le muestra al usuario, y además así el DISTINCT ON de
        # buscar_medicamento sí junta las presentaciones que solo difieren en eso.
        descripcion = re.sub(r"\s+", " ", f["Medicamento"]).strip()
        partes = [p.strip() for p in descripcion.split(" - ")]
        nombre_comercial = partes[0]
        laboratorio = partes[-1] if len(partes) > 1 else ""

        precio = _numero(f[COL_INSTITUCIONAL])
        if precio is None:
            # La columna no tiene vacíos en el corte actual, pero es NOT NULL en el
            # esquema: si algún día llega una vacía, mejor perder la fila y que se vea
            # en el reporte que reventar la carga entera.
            reporte["sin_precio"].append(cum)
            continue

        filas.append((
            cum,
            f["ID MR"].strip(),
            principio, forma, via,
            nombre_comercial, laboratorio, descripcion,
            _numero(f["Cantidad por unidad de medida"]),
            f["Unidad de medida"].strip(),
            precio,
            _numero(f[COL_COMERCIAL]),
            f["Circular CNPMDM"].strip(),
            _fecha_sismed(f["Fecha de inicio vigencia precio máximo de venta"]),
        ))
    return filas


# ---- invima

COLS_SHORTAGES = ["nombre", "atc", "estado", "fecha_seguimiento", "listado"]


def filas_invima(crudas: list[dict], reporte: dict) -> list[tuple]:
    """El CSV ya viene normalizado por extraer_invima.py: mapea 1:1.

    No se deduplica por nombre: un mismo principio activo con formas distintas
    (`ÁCIDO VALPROICO CÁPSULA DURA` vs `... JARABE`) son filas legítimamente distintas.
    Y el `estado` vacío del No. 276 se respeta como vacío — rellenarlo sería inventarse
    un dato de salud.
    """
    filas = []
    for f in crudas:
        estado = f["estado"].strip() or None
        if estado is None:
            reporte["sin_estado"].append(f["nombre"][:50])
        filas.append((
            f["nombre"].strip(),
            f["atc"].strip() or None,
            estado,
            _fecha_iso(f["fecha_seguimiento"]),
            f["listado"].strip() or None,
        ))
    return filas


# ---- pbs

COLS_COVERAGE = ["atc", "principio_activo", "forma", "cobertura", "aclaracion"]


def filas_pbs(crudas: list[dict], reporte: dict) -> list[tuple]:
    """`Resumen` y `FormaFarmaceutica` son idénticas: se guarda una sola.

    Las columnas `_Min` tampoco se guardan — son la misma cadena en minúscula y
    `curuba_norm` normaliza mejor, porque además quita tildes.
    """
    filas = []
    for f in crudas:
        crudo = f["CoberturaPlanBeneficiosUPC"].strip()
        clave = crudo.lower()
        if clave not in COBERTURAS:
            # Nunca adivina: lo desconocido se reporta y queda NULL. Si la fuente cambia
            # el fraseo, el conteo de revisar() no cuadra y se ve de una.
            reporte["cobertura_desconocida"][crudo[:70]] += 1
            cobertura = None
        else:
            cobertura = COBERTURAS[clave]

        # 1.061 filas dicen literalmente "Sin dato": eso es un NULL, no un texto que
        # mostrarle a nadie. Las otras 137 traen el criterio que condiciona la cobertura
        # y el agente las cita textualmente.
        aclaracion = f["Aclaracion"].strip()
        if aclaracion.lower() == "sin dato":
            aclaracion = None

        filas.append((
            f["CodigoATC"].strip() or None,
            f["PrincipioActivo"].strip(),
            f["FormaFarmaceutica"].strip() or None,
            cobertura,
            aclaracion,
        ))
    return filas


# ---- carga

async def cargar_sismed(limite: int | None, reporte: dict) -> int:
    ruta = _unico(DIR_SISMED)
    filas = filas_sismed(_leer(ruta, limite), reporte)
    print(f"  sismed  {ruta.name}")
    return await db.reemplazar_tabla("medications", COLS_MEDICATIONS, filas)


async def cargar_invima(limite: int | None, reporte: dict) -> int:
    filas = filas_invima(_leer(CSV_INVIMA, limite), reporte)
    print(f"  invima  {CSV_INVIMA.name}")
    return await db.reemplazar_tabla("shortages", COLS_SHORTAGES, filas)


async def cargar_pbs(limite: int | None, reporte: dict) -> int:
    ruta = _unico(DIR_PBS)
    filas = filas_pbs(_leer(ruta, limite), reporte)
    print(f"  pbs     {ruta.name}")
    return await db.reemplazar_tabla("coverage", COLS_COVERAGE, filas)


CARGADORES = {"pbs": cargar_pbs, "sismed": cargar_sismed, "invima": cargar_invima}
TABLA_DE = {"pbs": "coverage", "sismed": "medications", "invima": "shortages"}


# ---- revision

async def revisar(cargadas: list[str], reporte: dict, parcial: bool) -> None:
    """Reporta, no aborta. Mismo criterio que extraer_invima.py.

    Lo que vale acá es que los conteos cuadren contra ESPERADO: un mapeo roto no lanza
    excepción, entrega números distintos.
    """
    print("\n" + "=" * 68)
    print("REVISION")
    print("=" * 68)

    for fuente in cargadas:
        tabla = TABLA_DE[fuente]
        n = await db.contar(tabla)
        esperado = ESPERADO[tabla]
        if parcial:
            marca = f"(parcial, se esperan {esperado} en la carga completa)"
        else:
            marca = "ok" if n == esperado else f"<-- SE ESPERABAN {esperado}"
        print(f"  {tabla:<12} {n:>6} filas  {marca}")

    if "pbs" in cargadas:
        print("\n  cobertura:")
        vistos = {}
        for fila in await db.distribucion("coverage", "cobertura"):
            valor = fila["valor"] or "NULL (Sin dato)"
            vistos[fila["valor"]] = fila["n"]
            print(f"    {valor:<16} {fila['n']:>5}")
        if not parcial:
            # El chequeo que caza la trampa del substring: si `mipres` sale en 0 y `upc`
            # en 1.867, se comió las 420 de MIPRES y las marcó como financiadas.
            for clave, esperado in ESPERADO_COBERTURA.items():
                if vistos.get(clave) != esperado:
                    print(f"    <-- {clave}: {vistos.get(clave, 0)}, se esperaban {esperado}")

    if "invima" in cargadas:
        print("\n  estado:")
        for fila in await db.distribucion("shortages", "estado"):
            print(f"    {fila['valor'] or 'NULL':<18} {fila['n']:>5}")

    for etiqueta, valores in (
        ("filas sin precio institucional (descartadas)", reporte["sin_precio"]),
        ("mercado relevante sin 3 segmentos", reporte["mr_raro"]),
        ("filas del INVIMA sin estado", reporte["sin_estado"]),
    ):
        if valores:
            print(f"\n  {etiqueta}: {len(valores)}")
            for v in valores[:5]:
                print(f"    {v}")

    for literal, n in reporte["cobertura_desconocida"].most_common(10):
        print(f"\n  <-- cobertura no mapeada ({n}x): {literal!r}")


async def main() -> int:
    ap = argparse.ArgumentParser(description="Carga resources/data/ a Postgres.")
    ap.add_argument("--solo", choices=list(CARGADORES), action="append",
                    help="cargar solo esta fuente (se puede repetir). Default: las tres")
    ap.add_argument("--limite", type=int, help="solo las primeras N filas de cada CSV")
    args = ap.parse_args()

    # El PBS primero porque es el que contesta la pregunta de la raíz del árbol; el orden
    # no afecta la carga, pero deja el reporte en el orden en que se consultan.
    fuentes = args.solo or ["pbs", "sismed", "invima"]

    await db.abrir()
    try:
        await db.aplicar_esquema()
        reporte = {
            "sin_precio": [],
            "mr_raro": [],
            "sin_estado": [],
            "cobertura_desconocida": collections.Counter(),
        }
        print("cargando:")
        for fuente in fuentes:
            n = await CARGADORES[fuente](args.limite, reporte)
            print(f"          -> {n} filas")
        await revisar(fuentes, reporte, parcial=bool(args.limite))
    finally:
        await db.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
