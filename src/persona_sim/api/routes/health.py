from fastapi import APIRouter, Depends

from persona_sim import __version__
from persona_sim.api.deps import get_app_settings
from persona_sim.core.config import Settings
from persona_sim.db import verify_database_connection
from persona_sim.schemas.system import HealthResponse

router = APIRouter(prefix="/health", tags=["system"])


@router.get("", response_model=HealthResponse, response_model_exclude_none=True)
async def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    """Simple liveness endpoint with database status."""

    database_status = "ok"
    try:
        await verify_database_connection()
    except Exception:  # pragma: no cover - defensive health guard
        database_status = "unavailable"

    status = "ok" if database_status == "ok" else "degraded"
    return HealthResponse(
        status=status,
        environment=settings.environment,
        version=__version__,
        database=database_status,
    )
