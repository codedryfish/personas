from fastapi import FastAPI

from persona_sim import __version__
from persona_sim.api.routes.health import router as health_router
from persona_sim.core.config import get_settings
from persona_sim.core.logging import setup_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    setup_logging(settings.log_level)

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    application.include_router(health_router)

    return application


app = create_app()
