"""Simulation run API routes."""

from __future__ import annotations

from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from persona_sim.api.deps import get_simulation_service
from persona_sim.schemas import PersonaSpec, ScenarioSpec, SimulationState, Stimulus
from persona_sim.sim.errors import NotFoundError, RunFailedError, ValidationError
from persona_sim.sim.service import SimulationService

router = APIRouter(prefix="/v1/simulations", tags=["simulations"])


class SimulationCreateRequest(BaseModel):
    """Payload for starting a simulation run."""

    model_config = ConfigDict(extra="forbid")

    scenario: ScenarioSpec = Field(..., description="Scenario to simulate.")
    personas: list[PersonaSpec] = Field(..., description="Personas participating in the run.")
    stimuli: list[Stimulus] = Field(..., description="Stimuli shared with personas.")
    run_mode: str = Field(default="single-turn", description="Simulation execution mode.")
    steps: int = Field(default=1, ge=1, description="Number of steps to execute.")


class SimulationCreatedResponse(BaseModel):
    """Response containing the created run identifier."""

    model_config = ConfigDict(extra="forbid")

    run_id: UUID = Field(..., description="Identifier for the created run.")


@router.post(
    "",
    status_code=HTTPStatus.CREATED,
    response_model=SimulationCreatedResponse,
    response_model_exclude_none=True,
)
async def create_simulation_run(
    payload: SimulationCreateRequest,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationCreatedResponse:
    """Create a simulation run and return its identifier."""

    try:
        run_id = await service.start_run(
            scenario=payload.scenario,
            personas=payload.personas,
            stimuli=payload.stimuli,
            run_mode=payload.run_mode,
            steps=payload.steps,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)
        ) from exc  # pragma: no cover - simple mapping
    except RunFailedError as exc:
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc  # pragma: no cover - simple mapping

    return SimulationCreatedResponse(run_id=run_id)


@router.get(
    "/{run_id}",
    response_model=SimulationState,
    response_model_exclude_none=True,
)
async def get_simulation_run(
    run_id: UUID, service: SimulationService = Depends(get_simulation_service)
) -> SimulationState:
    """Retrieve a simulation run, including transcript and evaluation."""

    try:
        return await service.get_run(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(exc)) from exc
