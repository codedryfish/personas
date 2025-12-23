from fastapi import APIRouter, Depends

from persona_sim import __version__
from persona_sim.api.dependencies import get_app_settings
from persona_sim.core.config import Settings
from persona_sim.schemas.system import HealthResponse

router = APIRouter(prefix="/health", tags=["system"])


@router.get("", response_model=HealthResponse)
def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    """Simple liveness endpoint."""

    return HealthResponse(
        status="ok",
        environment=settings.environment,
        version=__version__,
    )
