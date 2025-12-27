"""Dependency providers for FastAPI routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from persona_sim.core.config import Settings, get_settings
from persona_sim.db.session import get_sessionmaker
from persona_sim.sim.service import SimulationService


def get_app_settings() -> Settings:
    """Dependency wrapper for application settings."""

    return get_settings()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Provide the shared async session factory."""

    return get_sessionmaker()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session."""

    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


@lru_cache
def get_simulation_service() -> SimulationService:
    """Provide a singleton SimulationService wired with the default session factory."""

    return SimulationService(session_factory=get_session_factory())
