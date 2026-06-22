"""Apply SQL migration files in order against the configured database.

Usage:  uv run python -m migrations.run

Each *.sql file under migrations/ is executed once, tracked in a `schema_migrations`
table. Files are applied in lexicographic order, so name them `0001_*`, `0002_*`, ...
"""

import asyncio
from pathlib import Path

import asyncpg

from config import get_settings
from db import to_psycopg_url

MIGRATIONS_DIR = Path(__file__).parent


async def _apply() -> None:
    settings = get_settings()
    dsn = to_psycopg_url(settings.database_url)
    conn = await asyncpg.connect(dsn, statement_cache_size=0, ssl="require")
    try:
        await conn.execute(
            "create table if not exists schema_migrations "
            "(name text primary key, applied_at timestamptz not null default now())"
        )
        applied = {r["name"] for r in await conn.fetch("select name from schema_migrations")}

        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                print(f"skip   {path.name} (already applied)")
                continue
            print(f"apply  {path.name}")
            sql = path.read_text()
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "insert into schema_migrations (name) values ($1)", path.name
                )
        print("migrations up to date")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(_apply())
