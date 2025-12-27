"""Deterministic heuristics for persona trust and fatigue updates."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from persona_sim.schemas.eval import ObjectionSeverity, WillDecision
from persona_sim.schemas.sim_state import TrustState


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class PersonaResponseObjection(BaseModel):
    """Summary of an objection extracted from a persona response."""

    model_config = ConfigDict(extra="forbid")

    detail: str = Field(..., description="Short description of the objection raised.")
    severity: ObjectionSeverity = Field(
        default=ObjectionSeverity.LOW, description="Severity classification for the objection."
    )


class PersonaResponseSummary(BaseModel):
    """Structured summary of a persona response used for heuristic updates."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., description="Raw response message from the persona.")
    stance: WillDecision = Field(..., description="Overall stance taken in the response.")
    objections: List[PersonaResponseObjection] = Field(
        default_factory=list,
        description="Extracted objections capturing severity for heuristic adjustments.",
    )


def apply_persona_heuristics(
    *, previous: TrustState, response: PersonaResponseSummary, mode: str
) -> TrustState:
    """Apply deterministic updates to trust, fatigue, and risk tolerance.

    The function is intentionally simple to remain predictable during tests and offline runs.
    The ``mode`` parameter is accepted for future specialization but currently does not alter the
    deterministic adjustments.
    """

    trust = previous.trust_score
    fatigue = previous.fatigue_score
    base_risk = previous.risk_tolerance

    if response.stance is WillDecision.YES:
        trust += 0.05
        fatigue -= 0.03
    elif response.stance is WillDecision.RELUCTANT:
        trust -= 0.02
        fatigue += 0.02
    else:
        trust -= 0.05
        fatigue += 0.03

    high_objections = sum(1 for obj in response.objections if obj.severity is ObjectionSeverity.HIGH)
    trust -= 0.03 * high_objections
    fatigue += 0.02 * high_objections

    trust = _clamp(trust)
    fatigue = _clamp(fatigue)
    risk_tolerance = _clamp(max(0.0, base_risk - fatigue * 0.2))

    return previous.model_copy(
        update={
            "trust_score": trust,
            "fatigue_score": fatigue,
            "risk_tolerance": risk_tolerance,
        }
    )
