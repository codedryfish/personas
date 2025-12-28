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

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "trust_score": 0.62,
                "fatigue_score": 0.18,
                "risk_tolerance": 0.44,
            }
        },
    )

    trust_score: float = Field(..., ge=0.0, le=1.0, description="Trust score in range 0-1.")
    fatigue_score: float = Field(
        ..., ge=0.0, le=1.0, description="Fatigue score in range 0-1 reflecting burnout."
    )
    risk_tolerance: float = Field(
        ..., ge=0.0, le=1.0, description="Risk tolerance in range 0-1 reflecting risk appetite."
    )


class PersonaState(BaseModel):
    """State snapshot for an individual persona."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "persona_id": "2fdab821-76d6-4c04-9a4b-6bc0099ae0b0",
                "trust_state": {
                    "trust_score": 0.62,
                    "fatigue_score": 0.18,
                    "risk_tolerance": 0.44,
                },
                "short_memory": [
                    "Requested mapping between SMCR control IDs and assistant outputs.",
                    "Flagged concern about false positives on audit trails.",
                ],
                "long_bias": "prefers transparent auditability",
                "flags": {"requires_explanation": True},
            }
        },
    )

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

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "run_id": "d07be1ed-958e-4b9e-81c9-eaaf995c6a60",
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
                    }
                ],
                "persona_states": {
                    "2fdab821-76d6-4c04-9a4b-6bc0099ae0b0": {
                        "persona_id": "2fdab821-76d6-4c04-9a4b-6bc0099ae0b0",
                        "trust_state": {
                            "trust_score": 0.62,
                            "fatigue_score": 0.18,
                            "risk_tolerance": 0.44,
                        },
                        "short_memory": [
                            "Requested mapping between SMCR control IDs and assistant outputs.",
                            "Flagged concern about false positives on audit trails.",
                        ],
                        "long_bias": "prefers transparent auditability",
                        "flags": {"requires_explanation": True},
                    }
                },
                "transcript": [],
                "outputs": None,
            }
        },
    )

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
