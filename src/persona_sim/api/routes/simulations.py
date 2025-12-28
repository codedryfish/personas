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


UK_COMPLIANCE_EXAMPLE = {
    "scenario": {
        "id": "b5e18cb6-2f20-4f6d-a061-c3f46a45c265",
        "title": "UK compliance control rollout",
        "context": "Launching an AI assistant to streamline SMCR evidence collection for UK banking teams.",
        "deadline": "2024-11-30T17:00:00Z",
        "stressors": ["tight audit window", "multiple regulators"],
        "success_criteria": ["reduce manual reviews by 40%", "no critical audit findings"],
    },
    "personas": [
        {
            "id": "2fdab821-76d6-4c04-9a4b-6bc0099ae0b0",
            "name": "Priya Desai",
            "role": "Head of Compliance Technology",
            "sector": "Banking",
            "locale": "UK",
            "incentives": ["prove audit readiness", "shorten change cycles"],
            "fears": ["vendor lock-in", "regulatory gaps"],
            "constraints": {
                "time_per_week_minutes": 180,
                "budget_gbp": 75000,
                "ai_trust_level": 3,
                "authority_level": "high",
            },
            "communication_style": "crisp, metric-led",
        },
        {
            "id": "8db75344-5df5-4f93-9a45-7f0c6801f4c0",
            "name": "Jamie Clark",
            "role": "Compliance Analyst",
            "sector": "Banking",
            "locale": "UK",
            "incentives": ["fewer manual tasks", "clear exception handling"],
            "fears": ["false positives", "opaque guidance"],
            "constraints": {
                "time_per_week_minutes": 240,
                "budget_gbp": 5000,
                "ai_trust_level": 4,
                "authority_level": "medium",
            },
            "communication_style": "succinct tickets",
        },
        {
            "id": "4e0ad9e9-4a0a-4b59-bb61-640703ba6f6a",
            "name": "Alex Morgan",
            "role": "Shadow IT Vendor",
            "sector": "Fintech",
            "locale": "UK",
            "incentives": ["bypass change control", "sell point tools"],
            "fears": ["central oversight", "standardized controls"],
            "constraints": {
                "time_per_week_minutes": 120,
                "budget_gbp": 0,
                "ai_trust_level": 2,
                "authority_level": "low",
            },
            "communication_style": "pushy proposals",
        },
    ],
    "stimuli": [
        {
            "type": "feature",
            "content": "Adaptive SMCR evidence pack generator with audit trails.",
            "question": "What gaps remain for FCA alignment?",
        },
        {
            "type": "pricing",
            "content": "Pilot bundle at £18k for 3 squads with monthly billing.",
        },
    ],
    "run_mode": "single-turn",
    "steps": 2,
}


class SimulationCreateRequest(BaseModel):
    """Payload for starting a simulation run."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [UK_COMPLIANCE_EXAMPLE]})

    scenario: ScenarioSpec = Field(..., description="Scenario to simulate.")
    personas: list[PersonaSpec] = Field(..., description="Personas participating in the run.")
    stimuli: list[Stimulus] = Field(..., description="Stimuli shared with personas.")
    run_mode: str = Field(default="single-turn", description="Simulation execution mode.")
    steps: int = Field(default=1, ge=1, description="Number of steps to execute.")


class SimulationCreatedResponse(BaseModel):
    """Response containing the created run identifier."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"run_id": "d07be1ed-958e-4b9e-81c9-eaaf995c6a60"}},
    )

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
