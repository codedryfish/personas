from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from persona_sim.db.engine import get_engine


_engine = get_engine()
SessionLocal = async_sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a scoped async session."""

    async with SessionLocal() as session:
        yield session
