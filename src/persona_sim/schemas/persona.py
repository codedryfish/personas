"""Persona-related Pydantic schemas."""

from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuthorityLevel(str, Enum):
    """Enumeration of persona authority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PersonaConstraints(BaseModel):
    """Constraints and preferences that shape persona behavior."""

    model_config = ConfigDict(extra="forbid")

    time_per_week_minutes: int = Field(
        ..., ge=0, description="Available time commitment in minutes per week."
    )
    budget_gbp: int = Field(..., ge=0, description="Budget available in GBP.")
    ai_trust_level: int = Field(
        ..., ge=1, le=5, description="Persona's trust in AI on a 1-5 scale."
    )
    authority_level: AuthorityLevel = Field(
        ..., description="Decision-making authority within their organization."
    )


class PersonaSpec(BaseModel):
    """Specification for a simulated persona."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
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
        },
    )

    id: UUID = Field(..., description="Unique identifier for the persona.")
    name: str = Field(..., description="Human-readable persona name.")
    role: str = Field(..., description="Role or title of the persona.")
    sector: Optional[str] = Field(
        default=None, description="Industry or sector the persona belongs to."
    )
    locale: str = Field(default="UK", description="Locale or region for the persona.")
    incentives: List[str] = Field(
        default_factory=list, description="Motivations or incentives influencing the persona."
    )
    fears: List[str] = Field(
        default_factory=list, description="Key fears or concerns held by the persona."
    )
    constraints: PersonaConstraints = Field(
        ..., description="Operational constraints applied to the persona."
    )
    communication_style: Optional[str] = Field(
        default=None, description="Preferred communication style for the persona."
    )
