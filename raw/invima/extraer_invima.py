"""Convierte el listado de abastecimiento del INVIMA (PDF) a CSV.

    uv run --with pdfplumber python raw/invima/extraer_invima.py --paginas 0-2 --verificar
    uv run --with pdfplumber python raw/invima/extraer_invima.py            # todo

Script de un solo uso: el PDF se reemplaza cada mes y esto se vuelve a correr. Vive
aqui, al lado del PDF, para que la API nunca tenga que instalar pdfplumber.

El PDF no es una tabla sino tres, con columnas y estados distintos:

    tabla A   ~72 paginas   En monitorizacion / En riesgo / Desabastecido   -> activo
    tabla B   ~18 paginas   No desabastecido (casos cerrados)               -> cerrado
    tabla C    ~3 paginas   No comercializado / Descontinuado               -> se ignora

La A empieza en la pagina 0, debajo de las notas aclaratorias. Cada tabla renumera
desde 1, asi que `No.` no es llave.
"""

import argparse
import collections
import csv
import re
import sys
from pathlib import Path

import pdfplumber

AQUI = Path(__file__).resolve().parent
PDF = AQUI / "LISTADO DE ABASTECIMIENTO MAYO 2026.pdf"
SALIDA = AQUI / "desabastecimiento.csv"

# Cortes de columna de la tabla A, verificados contra los `rect` de las paginas 0-71.
# Las dos columnas RESUMEN (280 -> 527) son parrafos largos sobre unidades disponibles
# y no aportan a lo que Curuba responde: se descartan enteras.
COLS_A = {
    "no":     (70.5,  88.0),
    "nombre": (88.0,  136.0),
    "atc":    (136.0, 152.5),
    "f_ini":  (152.5, 181.5),
    "f_ult":  (181.5, 208.0),
    "estado": (208.0, 239.5),
    "causa":  (239.5, 280.0),
}

# Firmas en x de los `rect` de cada tabla. Se clasifica por geometria y no por numero
# de pagina porque el listado se republica cada mes con otra paginacion.
FIRMAS = {
    "A": (70.0, 88.0, 136.0, 152.0, 181.0, 208.0, 240.0, 280.0, 407.0, 527.0),
    "B": (65.0, 75.0, 166.0, 203.0, 248.0, 298.0, 335.0, 464.0, 582.0),
    "C": (84.0, 98.0, 180.0, 210.0, 246.0, 296.0, 334.0, 499.0, 563.0),
}

# El encabezado que se repite ocupa hasta top=76.9 y la primera fila de datos arranca en
# 77.7, asi que el corte va justo en medio. Hay poco margen y no es negociable por dos
# lados:
#   - subirlo a 95 se come el medicamento que abre la pagina (empieza en 77.7, no en
#     109.8 -- la 109.8 de la pagina 1 es una sub-fila de continuacion, no una cabecera);
#   - bajarlo mete texto del encabezado en las celdas, y ademas deja entrar las celdas
#     combinadas que cruzan el salto de pagina: el exportador las dibuja centradas sobre
#     todo el rango combinado, asi que caen en top negativo o cerca de 0 (el "43
#     AZITROMICINA" de la pagina 8 sale en top=-370.9). Son un duplicado del medicamento
#     que ya se leyo en la pagina anterior y tienen que quedar afuera.
BODY_TOP = 76.0

ESTADOS = {
    "en monitorizacion":              "monitorizacion",
    "en riesgo de desabastecimiento": "riesgo",
    "desabastecido":                  "desabastecido",
    "no desabastecido":               "no_desabastecido",
}

RE_CID = re.compile(r"\(cid:\d+\)")
RE_FECHA = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
# Los dos ultimos digitos son opcionales: hay codigos legitimos de nivel 4 como V07AB
# (AGUA ESTERIL DE GRANDES VOLUMENES). No es un error de parseo.
RE_ATC = re.compile(r"\b[A-Z]\d{2}[A-Z]{2}\d{0,2}\b")
# El PDF trae espacios de ancho cero pegados a algunos ATC (S01ED51​). Invisibles,
# pero rompen cualquier comparacion o join contra el codigo.
# (el \xa0 no va aca: split() ya lo trata como espacio, borrarlo pegaria palabras)
INVISIBLES = str.maketrans("", "", "​‌‍﻿")


# --------------------------------------------------------------------------- texto

def limpiar(txt):
    """Borra (cid:N), caracteres invisibles y colapsa espacios."""
    txt = RE_CID.sub(" ", txt.translate(INVISIBLES))
    # La fuente de las filas de vacunas mapea mal la mu: "2.50000 æg" es "2.50000 µg".
    txt = re.sub(r"(?<=\d)(\s*)æg\b", r"\1µg", txt)
    return " ".join(txt.split())


def texto_celda(chars, x0, x1, top, bot):
    """Texto de una celda, reconstruyendo las lineas a mano.

    `extract_table` no sirve en la tabla A: la fuente es de 2.4 pt con interlinea de
    2.9 pt y el y_tolerance por defecto de pdfplumber es 3, mayor que la interlinea.
    Colapsa las 9 lineas de una celda en una sola y las ordena por x, produciendo
    basura del tipo "2EUA(PVCE U 1NNB RE LA M / IR NO P 0 T ED D 4 T I AI M".
    Aca se agrupa por `top` con una tolerancia de 0.5 pt, que si separa las lineas.
    """
    sel = [
        c for c in chars
        if x0 - 0.5 <= c["x0"] < x1 - 0.5 and top - 0.5 <= c["top"] < bot - 0.5
    ]
    if not sel:
        return ""
    lineas = collections.defaultdict(list)
    for c in sel:
        lineas[round(c["top"] * 2) / 2].append(c)
    partes = [
        "".join(ch["text"] for ch in sorted(lineas[t], key=lambda c: c["x0"]))
        for t in sorted(lineas)
    ]
    return limpiar(" ".join(partes))


def a_iso(fechas):
    """De varias 'dd/mm/yyyy' en un texto devuelve la mas reciente como 'yyyy-mm-dd'."""
    iso = sorted(f"{a}-{m}-{d}" for d, m, a in RE_FECHA.findall(fechas))
    return iso[-1] if iso else ""


# Del mas largo al mas corto, y esto NO es cosmetico: "desabastecido" es subcadena de
# "no desabastecido" y de "en riesgo de desabastecimiento". Probando en orden de dict,
# toda la tabla B sale marcada como desabastecida -- exactamente al reves de lo que dice.
LITERALES = sorted(ESTADOS, key=len, reverse=True)


def normalizar_estado(txt, reporte):
    """Mapea el estado literal al del esquema. Nunca adivina: lo desconocido se reporta."""
    limpio = limpiar(txt)
    for literal in LITERALES:
        # el estado puede venir repetido una vez por sub-fila
        if literal in _sin_tildes(limpio):
            return ESTADOS[literal]
    if limpio:
        reporte["estado_desconocido"][limpio] += 1
    return ""


def _sin_tildes(txt):
    tabla = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")
    return txt.translate(tabla).lower()


# --------------------------------------------------------------------------- paginas

def clasificar_pagina(pg):
    """'A', 'B', 'C' o None, segun las coordenadas x de los rectangulos de la pagina."""
    xs = {round(v) for r in pg.rects for v in (r["x0"], r["x1"])}
    if not xs:
        return None
    mejor, mejor_puntaje = None, 0.0
    for etiqueta, firma in FIRMAS.items():
        aciertos = sum(1 for f in firma if any(abs(f - x) <= 1 for x in xs))
        puntaje = aciertos / len(firma)
        if puntaje > mejor_puntaje:
            mejor, mejor_puntaje = etiqueta, puntaje
    return mejor if mejor_puntaje >= 0.8 else None


def filas_tabla_a(pg, abierto, reporte):
    """Un registro por medicamento. Devuelve (registros, grupo_abierto).

    Cada medicamento ocupa N sub-filas, una por titular de Registro Sanitario, y solo
    la primera trae No./Nombre/Estado -- las demas solo ATC y fechas. Los `rect` de
    esas celdas combinadas tienen altura 0 (son bordes, no cajas), asi que la
    combinacion no se puede leer de la geometria: el ancla son los digitos de la
    columna `No.`.

    Los grupos ademas cruzan paginas, por eso `abierto` entra y sale de la funcion:
    las sub-filas huerfanas al comienzo de una pagina pertenecen al ultimo medicamento
    de la anterior y solo aportan fechas.
    """
    chars = [c for c in pg.chars if c["top"] > BODY_TOP]
    nx0, nx1 = COLS_A["no"]
    crudos = sorted({
        round(c["top"], 1) for c in chars
        if nx0 - 0.5 <= c["x0"] < nx1 - 0.5 and c["text"].strip().isdigit()
    })
    # un numero de varios digitos son varios chars con tops casi iguales
    inicios = [t for i, t in enumerate(crudos) if i == 0 or t - crudos[i - 1] > 2]

    # lo que quede arriba del primer inicio continua el grupo de la pagina anterior
    if abierto is not None:
        cola = inicios[0] if inicios else pg.height
        fechas = texto_celda(chars, *COLS_A["f_ult"], BODY_TOP, cola)
        if fechas:
            abierto["f_ult"] = f"{abierto['f_ult']} {fechas}"

    registros = []
    bordes = inicios + [pg.height]
    for a, b in zip(bordes, bordes[1:]):
        if abierto is not None:
            registros.append(abierto)
        celdas = {k: texto_celda(chars, *v, a, b) for k, v in COLS_A.items()}
        celdas["pagina"] = pg.page_number - 1
        abierto = celdas

    return registros, abierto


def cerrar_a(celdas, reporte):
    """Consolida las N sub-filas de un medicamento de la tabla A en una fila del CSV."""
    atcs = RE_ATC.findall(celdas["atc"])
    return {
        "nombre": celdas["nombre"],
        # un medicamento puede traer varios ATC legitimos entre sus titulares (el acido
        # acetilsalicilico sale como N02BA01 y B01AC06): vale el de la fila cabecera
        "atc": atcs[0] if atcs else limpiar(celdas["atc"]),
        "estado": normalizar_estado(celdas["estado"], reporte),
        # la mas reciente entre todos los titulares, que es lo que promete el nombre
        # de la columna ("fecha del ultimo seguimiento")
        "fecha_seguimiento": a_iso(celdas["f_ult"]),
        "listado": "activo",
        "_no": celdas["no"],
        "_pagina": celdas["pagina"],
    }


def filas_tabla_b(pg, reporte):
    """Filas planas, una por medicamento. Aca `extract_table` si funciona.

    La fuente es de 2.8 pt y no hay celdas combinadas, asi que la estrategia de lineas
    separa bien. La columna 7 es un separador vacio; la fecha que interesa es la 4
    ('Fecha de la ultima revision'), no la 8 ('Fecha de cierre').
    """
    tabla = pg.extract_table(
        {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
    ) or []
    registros = []
    for fila in tabla:
        if len(fila) < 6:
            continue
        no = limpiar(fila[0] or "")
        if not no.isdigit():  # las dos filas de encabezado
            continue
        # Las paginas de la tabla B no traen todas el mismo numero de columnas: unas
        # tienen 9 (con un separador vacio) y otras 8. Los indices 1, 2, 4 y 5 son
        # estables en ambas; el que se corre es el de 'Fecha de cierre', que queda de
        # ultimo. Solo se usa como respaldo: el INVIMA dejo la fecha de revision en
        # blanco en una fila (No. 352, los toxoides) y sin esto sale sin fecha.
        fecha = a_iso(fila[4] or "")
        if not fecha:
            fecha = a_iso(fila[-1] or "")
            if fecha:
                reporte["fecha_de_cierre"].append(f"No={no} p{pg.page_number - 1}")
        registros.append({
            "nombre": limpiar((fila[1] or "").replace("\n", " ")),
            "atc": limpiar(fila[2] or ""),
            "estado": normalizar_estado(fila[5] or "", reporte),
            "fecha_seguimiento": fecha,
            "listado": "cerrado",
            "_no": no,
            "_pagina": pg.page_number - 1,
        })
    return registros


# --------------------------------------------------------------------------- salida

def revisar(filas, reporte):
    """Chequeos que corren en cada corrida. Reportan, no abortan."""
    print("\n" + "=" * 72)
    print("REVISION")
    print("=" * 72)

    for listado in ("activo", "cerrado"):
        nums = [int(f["_no"]) for f in filas if f["listado"] == listado and f["_no"].isdigit()]
        if not nums:
            continue
        huecos = sorted(set(range(min(nums), max(nums) + 1)) - set(nums))
        print(f"  {listado:8} No. {min(nums)}..{max(nums)}  ({len(nums)} filas)", end="")
        print(f"  HUECOS: {huecos}" if huecos else "  sin huecos")
        if min(nums) != 1:
            print(f"    OJO: {listado} no empieza en 1")
        # una celda combinada que cruza el salto de pagina se vuelve a dibujar fuera de
        # la hoja: si se cuela, el medicamento sale dos veces
        repes = [n for n, k in collections.Counter(nums).items() if k > 1]
        if repes:
            print(f"    REPETIDOS: {sorted(repes)}")

    malos_atc = [f for f in filas if not RE_ATC.fullmatch(f["atc"])]
    print(f"  atc con formato raro: {len(malos_atc)}")
    for f in malos_atc[:5]:
        print(f"    p{f['_pagina']} No={f['_no']} atc={f['atc']!r} {f['nombre'][:45]}")

    for etiqueta, campo in (("sin estado", "estado"), ("sin nombre", "nombre"),
                            ("sin fecha", "fecha_seguimiento")):
        vacias = [f for f in filas if not f[campo]]
        print(f"  {etiqueta}: {len(vacias)}")
        for f in vacias[:5]:
            print(f"    p{f['_pagina']} No={f['_no']} {f['nombre'][:55]}")
    for literal, n in reporte["estado_desconocido"].most_common(10):
        print(f"    estado no mapeado ({n}x): {literal[:70]!r}")

    if reporte["fecha_de_cierre"]:
        print(f"  fecha tomada de 'Fecha de cierre': {reporte['fecha_de_cierre']}")

    print(f"\n  estados: {dict(collections.Counter(f['estado'] for f in filas))}")
    print(f"  listado: {dict(collections.Counter(f['listado'] for f in filas))}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--paginas", help="rango 0-indexado, ej '0-2' o '72-74'. Default: todas")
    ap.add_argument("--verificar", action="store_true", help="imprime cada fila para comparar")
    ap.add_argument("--salida", type=Path, default=SALIDA)
    ap.add_argument("--pdf", type=Path, default=PDF)
    args = ap.parse_args()

    if args.paginas:
        desde, _, hasta = args.paginas.partition("-")
        rango = range(int(desde), int(hasta or desde) + 1)
    else:
        rango = None

    reporte = {"estado_desconocido": collections.Counter(), "fecha_de_cierre": []}
    filas = []
    conteo_paginas = collections.Counter()

    with pdfplumber.open(args.pdf) as pdf:
        indices = list(rango) if rango else range(len(pdf.pages))
        abierto = None
        for i in indices:
            if i >= len(pdf.pages):
                break
            pg = pdf.pages[i]
            tabla = clasificar_pagina(pg)
            conteo_paginas[tabla] += 1
            if tabla == "A":
                registros, abierto = filas_tabla_a(pg, abierto, reporte)
                filas.extend(cerrar_a(r, reporte) for r in registros)
            else:
                if abierto is not None:  # se acabo la tabla A
                    filas.append(cerrar_a(abierto, reporte))
                    abierto = None
                if tabla == "B":
                    filas.extend(filas_tabla_b(pg, reporte))
                # la tabla C (No comercializado / Descontinuado) se ignora a proposito
        if abierto is not None:
            filas.append(cerrar_a(abierto, reporte))

    print(f"paginas por tabla: {dict(conteo_paginas)}")

    if args.verificar:
        print("\n" + "=" * 72)
        print("FILAS")
        print("=" * 72)
        for f in filas:
            print(
                f"  p{f['_pagina']:<3} No={f['_no']:>4} | {f['atc']:<9} | "
                f"{f['fecha_seguimiento'] or '?':<10} | {f['estado'] or '?':<17} | "
                f"{f['listado']:<7} | {f['nombre'][:70]}"
            )

    revisar(filas, reporte)

    campos = ["nombre", "atc", "estado", "fecha_seguimiento", "listado"]
    with open(args.salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    print(f"\n  -> {args.salida}  ({len(filas)} filas)")


if __name__ == "__main__":
    sys.exit(main())
