"""Async database engine + session factory.

The app talks to Supabase Postgres through the transaction pooler (pgbouncer), so
asyncpg's prepared-statement cache is disabled — pgbouncer transaction mode does not
keep server-side prepared statements alive across checkouts.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import get_settings


def to_asyncpg_url(url: str) -> str:
    """Normalise a libpq-style postgres URL to the SQLAlchemy asyncpg driver."""
    for prefix in ("postgresql+asyncpg://",):
        if url.startswith(prefix):
            return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    return url


def to_psycopg_url(url: str) -> str:
    """Plain libpq URL for psycopg (used by the LangGraph checkpointer)."""
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url[len("postgresql+asyncpg://") :]
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


_settings = get_settings()

engine = create_async_engine(
    to_asyncpg_url(_settings.database_url),
    pool_pre_ping=True,
    connect_args={"statement_cache_size": 0, "ssl": "require"},
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
