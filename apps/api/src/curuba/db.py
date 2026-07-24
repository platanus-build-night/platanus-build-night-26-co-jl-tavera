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
