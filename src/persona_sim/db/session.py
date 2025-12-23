from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from persona_sim.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Create a configured async engine."""

    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False, future=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return a shared async session factory."""

    return async_sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a scoped async session."""

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        yield session


async def verify_database_connection(engine: AsyncEngine | None = None) -> None:
    """Ensure the database is reachable during application startup."""

    active_engine = engine or get_engine()
    async with active_engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
