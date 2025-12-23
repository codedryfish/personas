from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from persona_sim.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for SQLAlchemy models."""

    pass


def get_engine() -> AsyncEngine:
    """Create a configured async engine."""

    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False, future=True)
