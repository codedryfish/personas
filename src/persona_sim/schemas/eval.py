"""Evaluation schemas capturing persona responses and objections."""

from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ObjectionCategory(str, Enum):
    """Enumeration of objection categories."""

    RISK = "risk"
    COST = "cost"
    TIME = "time"
    TRUST = "trust"
    COMPLIANCE = "compliance"
    USABILITY = "usability"
    OTHER = "other"


class ObjectionSeverity(str, Enum):
    """Enumeration of objection severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Objection(BaseModel):
    """Objection raised by a persona during evaluation."""

    model_config = ConfigDict(extra="forbid")

    category: ObjectionCategory = Field(..., description="Category of the objection.")
    detail: str = Field(..., description="Detailed description of the objection.")
    severity: ObjectionSeverity = Field(..., description="Severity of the objection.")


class WillDecision(str, Enum):
    """Decision outcome for adoption or usage."""

    YES = "yes"
    NO = "no"
    RELUCTANT = "reluctant"


class EvaluationReport(BaseModel):
    """Evaluation results for a simulation run."""

    model_config = ConfigDict(extra="forbid")

    will_buy: WillDecision = Field(..., description="Buying decision outcome.")
    will_use_daily: WillDecision = Field(..., description="Daily usage intent outcome.")
    trust_delta: float = Field(
        ..., ge=-1.0, le=1.0, description="Change in trust score between -1 and 1."
    )
    top_objections: List[Objection] = Field(
        default_factory=list, description="List of top objections raised by personas."
    )
    required_proof: List[str] = Field(
        default_factory=list, description="Evidence required to satisfy concerns."
    )
    recommended_next_steps: List[str] = Field(
        default_factory=list, description="Recommended next steps post-evaluation."
    )

