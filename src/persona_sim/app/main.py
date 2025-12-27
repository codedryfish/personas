from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from persona_sim import __version__
from persona_sim.api.routes.health import router as health_router
from persona_sim.api.routes.simulations import router as simulations_router
from persona_sim.core.config import get_settings
from persona_sim.core.logging import setup_logging
from persona_sim.db import verify_database_connection


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await verify_database_connection()
        yield

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    application.include_router(health_router)
    application.include_router(simulations_router)

    return application


app = create_app()
