"""Simulation state schemas for tracking run progress."""

from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from persona_sim.schemas.eval import EvaluationReport
from persona_sim.schemas.persona import PersonaSpec
from persona_sim.schemas.scenario import ScenarioSpec
from persona_sim.schemas.transcript import TranscriptEvent


class TrustState(BaseModel):
    """Trust and fatigue metrics for a persona."""

    model_config = ConfigDict(extra="forbid")

    trust_score: float = Field(..., ge=0.0, le=1.0, description="Trust score in range 0-1.")
    fatigue_score: float = Field(
        ..., ge=0.0, le=1.0, description="Fatigue score in range 0-1 reflecting burnout."
    )
    risk_tolerance: float = Field(
        ..., ge=0.0, le=1.0, description="Risk tolerance in range 0-1 reflecting risk appetite."
    )


class PersonaState(BaseModel):
    """State snapshot for an individual persona."""

    model_config = ConfigDict(extra="forbid")

    persona_id: UUID = Field(..., description="Identifier linking to the persona specification.")
    trust_state: TrustState = Field(..., description="Current trust-related metrics.")
    short_memory: List[str] = Field(
        default_factory=list, description="Short-term memory entries (most recent first)."
    )
    long_bias: Optional[str] = Field(
        default=None, description="Long-term bias or predisposition noted for the persona."
    )
    flags: Dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean flags tracking persona-specific toggles or states.",
    )


class SimulationState(BaseModel):
    """Aggregate simulation state across personas and scenario."""

    model_config = ConfigDict(extra="forbid")

    run_id: UUID = Field(..., description="Unique identifier for the simulation run.")
    scenario: ScenarioSpec = Field(..., description="Scenario context for the run.")
    personas: List[PersonaSpec] = Field(
        default_factory=list, description="Personas participating in the simulation."
    )
    persona_states: Dict[UUID, PersonaState] = Field(
        default_factory=dict,
        description="State keyed by persona identifier for quick access.",
    )
    transcript: List[TranscriptEvent] = Field(
        default_factory=list, description="Chronological transcript of simulation events."
    )
    outputs: Optional[EvaluationReport] = Field(
        default=None, description="Optional evaluation report produced post-simulation."
    )

