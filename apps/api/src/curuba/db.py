"""Pool de asyncpg y **todo** el SQL del proyecto.

Regla del CLAUDE.md: ninguna query suelta en agent.py ni en main.py.
"""

from pathlib import Path

import asyncpg

from curuba.config import settings

_pool: asyncpg.Pool | None = None

ESQUEMA = Path(__file__).with_name("schema.sql")


async def abrir() -> None:
    """Abre el pool. Se llama desde el lifespan de FastAPI."""
    global _pool
    if _pool is None:
        if not settings.database_url:
            # asyncpg con un DSN vacío no falla de una: lo ignora, cae a los
            # defaults de libpq y termina intentando localhost:5432. El error
            # que sale ("Connect call failed ('127.0.0.1', 5432)") no menciona
            # ninguna variable de entorno y parece un Postgres caído.
            raise RuntimeError(
                "Falta DATABASE_URL. En Railway va en las variables del SERVICIO "
                "DE LA API como ${{Postgres.DATABASE_URL}} — no basta con que "
                "exista el servicio de Postgres, Railway no comparte variables "
                "entre servicios. En local va la URL PÚBLICA "
                "(DATABASE_PUBLIC_URL): la privada solo resuelve dentro de Railway."
            )
        _pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)


async def cerrar() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _p() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("el pool no está abierto — falta db.abrir()")
    return _pool


async def aplicar_esquema() -> None:
    """Corre schema.sql. Idempotente."""
    await _p().execute(ESQUEMA.read_text(encoding="utf-8"))


# ── Carga masiva (la usa etl.py) ──────────────────────────────────────────

async def reemplazar_tabla(tabla: str, columnas: list[str], registros: list[tuple]) -> int:
    """Vacía la tabla y la vuelve a llenar con COPY, en una transacción.

    Vive acá y no en etl.py por la regla del CLAUDE.md: todo el SQL en db.py. El ETL
    solo parsea y arma tuplas.

    TRUNCATE y no DELETE porque reinicia el `serial` de shortages y coverage: si no,
    cada recarga deja los ids corridos. `RESTART IDENTITY` es lo que lo hace.
    """
    async with _p().acquire() as cx, cx.transaction():
        await cx.execute(f"TRUNCATE {tabla} RESTART IDENTITY")
        await cx.copy_records_to_table(tabla, records=registros, columns=columnas)
    return len(registros)


async def contar(tabla: str) -> int:
    return await _p().fetchval(f"SELECT count(*) FROM {tabla}")


async def distribucion(tabla: str, columna: str) -> list[asyncpg.Record]:
    """Conteo por valor de una columna. Para los chequeos de revisar() del ETL."""
    return await _p().fetch(
        f"SELECT {columna} AS valor, count(*) AS n FROM {tabla} "
        f"GROUP BY {columna} ORDER BY n DESC"
    )


# ── Conversaciones ────────────────────────────────────────────────────────

async def cargar_historial(wa_id: str) -> bytes | None:
    """Devuelve los bytes que espera ModelMessagesTypeAdapter, o None."""
    crudo = await _p().fetchval(
        "SELECT messages::text FROM conversations WHERE wa_id = $1", wa_id
    )
    return crudo.encode("utf-8") if crudo else None


async def guardar_historial(wa_id: str, mensajes: bytes) -> None:
    await _p().execute(
        """
        INSERT INTO conversations (wa_id, messages, actualizado)
        VALUES ($1, $2::jsonb, now())
        ON CONFLICT (wa_id) DO UPDATE
            SET messages = EXCLUDED.messages, actualizado = now()
        """,
        wa_id,
        mensajes.decode("utf-8"),
    )


async def borrar_historial(wa_id: str) -> None:
    await _p().execute("DELETE FROM conversations WHERE wa_id = $1", wa_id)


# ── Búsqueda por similitud ────────────────────────────────────────────────
#
# Las tres búsquedas usan `<%` (word_similarity) y NO `%` (similarity), que es lo que
# decía el spec. La diferencia no es de matiz: **con `%` las tres devuelven cero filas
# siempre.**
#
# `similarity(a, b)` divide los trigramas en común sobre la unión de los dos, así que
# castiga la diferencia de longitud. `search_text` de medications promedia 103 caracteres
# (junta principio activo, marca y descripción entera) y la consulta del usuario son dos
# palabras, así que el puntaje se hunde muy por debajo del umbral de 0.3:
#
#     similarity('omeprazol', 'esomeprazol nexium nexium - esomeprazol 40mg/1u ...')
#       -> 0.1194   (no pasa el umbral: 0 resultados)
#     word_similarity('omeprazol', <lo mismo>)
#       -> 0.8000   (pasa)
#
# `word_similarity(a, b)` mide qué tan bien encaja `a` dentro de un pedazo de `b`, que es
# justo lo que se necesita cuando alguien escribe "losartan 50" y la fila dice
# "ARAMAX - Amlodipino 2,5mg/1U + Losartan 50mg/1U - Sólido - Oral x 30 - MEGALABS".
#
# El `similarity` sí se usa, pero solo para desempatar: sin él, buscar "losartan" deja
# LOSARTÁN, LOSARTÁN + AMLODIPINA y LOSARTÁN + HIDROCLOROTIAZIDA empatados en 1.00 y el
# orden queda al azar. Con el desempate, la molécula sola queda de primera.

_BUSCAR_MEDICAMENTO = """
SELECT * FROM (
    SELECT DISTINCT ON (descripcion, precio_institucional)
           cum, id_mr, principio_activo, forma, via, descripcion, laboratorio,
           cantidad, unidad, precio_institucional,
           round(word_similarity(curuba_norm($1), search_text)::numeric, 2) AS score
    FROM medications
    WHERE curuba_norm($1) <% search_text
    ORDER BY descripcion, precio_institucional,
             word_similarity(curuba_norm($1), search_text) DESC
) c
ORDER BY score DESC,
         similarity(curuba_norm(principio_activo), curuba_norm($1)) DESC
LIMIT $2
"""

_CONSULTAR_DESABASTECIMIENTO = """
SELECT nombre, atc, estado, fecha_seguimiento, listado,
       round(word_similarity(curuba_norm($1), search_text)::numeric, 2) AS score
FROM shortages
WHERE curuba_norm($1) <% search_text
ORDER BY score DESC,
         similarity(curuba_norm(nombre), curuba_norm($1)) DESC
LIMIT $2
"""

_BUSCAR_COBERTURA = """
SELECT * FROM (
    SELECT DISTINCT ON (principio_activo, cobertura)
           principio_activo, atc, forma, cobertura, aclaracion,
           round(word_similarity(curuba_norm($1), search_text)::numeric, 2) AS score
    FROM coverage
    WHERE curuba_norm($1) <% search_text
    ORDER BY principio_activo, cobertura,
             word_similarity(curuba_norm($1), search_text) DESC
) c
ORDER BY score DESC,
         similarity(curuba_norm(principio_activo), curuba_norm($1)) DESC
LIMIT $2
"""


async def buscar_medicamento(nombre: str, limite: int = 8) -> list[asyncpg.Record]:
    """Candidatos de SISMED con su score. Cero filas = no está bajo control de precios.

    `DISTINCT ON (descripcion, precio_institucional)` porque un mismo producto aparece con
    varios CUM: hay 8.612 grupos de descripción y precio idénticos (`ARAMAX ... x 30 -
    SCANDINAVIA PHARMA` sale con dos CUM distintos). Sin eso, los 8 candidatos pueden ser
    la misma caja ocho veces. Las presentaciones que solo cambian de laboratorio SÍ se
    conservan: son información distinta.
    """
    return await _p().fetch(_BUSCAR_MEDICAMENTO, nombre, limite)


async def consultar_desabastecimiento(nombre: str, limite: int = 8) -> list[asyncpg.Record]:
    """Candidatos del INVIMA con su score. Cero filas = no hay reportes.

    Ojo con `estado`: `no_desabastecido` (373 de 783 filas) NO es lo mismo que cero
    filas. Significa que el INVIMA sí le hizo seguimiento y cerró el caso.
    """
    return await _p().fetch(_CONSULTAR_DESABASTECIMIENTO, nombre, limite)


async def buscar_cobertura(nombre: str, limite: int = 8) -> list[asyncpg.Record]:
    """Candidatos del PBS con su score. Cero filas = NO se encontró, nunca "no cubierto".

    El listado no es exhaustivo y el cruce por principio activo con SISMED solo llega al
    72,5 %. Un falso negativo acá manda a alguien a pagar de su bolsillo algo a lo que
    tiene derecho, así que la ausencia no se puede reportar como negación.
    """
    return await _p().fetch(_BUSCAR_COBERTURA, nombre, limite)


if __name__ == "__main__":
    # Aplicar el esquema desde la máquina local, contra la URL PÚBLICA de
    # Railway (la privada solo resuelve dentro de Railway):
    #   cd apps/api && PYTHONPATH=src uv run python -m curuba.db
    import asyncio

    async def _main() -> None:
        await abrir()
        await aplicar_esquema()
        filas = await _p().fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1"
        )
        print("esquema aplicado. tablas:", ", ".join(f["tablename"] for f in filas))
        await cerrar()

    asyncio.run(_main())
