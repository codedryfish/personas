"""Graph state definitions for persona simulation LangGraph workflows."""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from persona_sim.schemas.eval import ObjectionSeverity, WillDecision
from persona_sim.schemas.sim_state import SimulationState
from persona_sim.schemas.stimulus import Stimulus


class RunMode(str, Enum):
    """Supported execution modes for the simulation graph."""

    SINGLE_TURN = "single-turn"
    MULTI_TURN = "multi-turn"


class TurnInput(BaseModel):
    """Input for a single turn containing the stimulus and optional question."""

    model_config = ConfigDict(extra="forbid")

    stimulus: Stimulus = Field(..., description="Stimulus shared with all personas for the turn.")
    question: str | None = Field(
        default=None, description="Optional follow-up question layered on the stimulus."
    )


class RunConfig(BaseModel):
    """Static configuration for a simulation run."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    run_id: UUID = Field(..., description="Identifier for the run, reused for persistence.")
    model_name: str = Field(..., description="LLM model name used for persona responses.")
    temperature: float = Field(..., ge=0.0, le=1.0, description="Sampling temperature for the LLM.")
    mode: RunMode = Field(default=RunMode.SINGLE_TURN, description="Single or multi-turn mode.")
    turns: list[TurnInput] = Field(
        default_factory=list,
        description="Ordered turn inputs. In single-turn mode only the first entry is used.",
    )
    persona_modes: dict[UUID, str] = Field(
        default_factory=dict,
        description="Optional overrides mapping persona IDs to persona prompt modes.",
    )


class PersonaResponse(BaseModel):
    """LLM response captured for a persona during a turn."""

    model_config = ConfigDict(extra="forbid")

    persona_id: UUID = Field(..., description="Identifier of the responding persona.")
    content: str = Field(..., description="Raw response content from the persona model.")
    stance: WillDecision = Field(..., description="Stance inferred from the response content.")
    objection_severity: ObjectionSeverity = Field(
        default=ObjectionSeverity.LOW,
        description="Highest objection severity inferred from the response.",
    )


class GraphState(BaseModel):
    """Mutable state threaded through the LangGraph execution."""

    model_config = ConfigDict(extra="forbid")

    simulation: SimulationState = Field(..., description="Primary simulation state object.")
    config: RunConfig = Field(..., description="Run configuration and turn inputs.")
    current_turn: int = Field(default=0, ge=0, description="Zero-based turn index.")
    latest_responses: list[PersonaResponse] = Field(
        default_factory=list, description="Responses collected in the active turn."
    )
