"""Scenario-related Pydantic schemas."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScenarioSpec(BaseModel):
    """Specification for a simulation scenario."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "b5e18cb6-2f20-4f6d-a061-c3f46a45c265",
                "title": "UK compliance control rollout",
                "context": "Launching an AI assistant to streamline SMCR evidence collection for UK banking teams.",
                "deadline": "2024-11-30T17:00:00Z",
                "stressors": ["tight audit window", "multiple regulators"],
                "success_criteria": ["reduce manual reviews by 40%", "no critical audit findings"],
            }
        },
    )

    id: UUID = Field(..., description="Unique identifier for the scenario.")
    title: str = Field(..., description="Title of the scenario.")
    context: str = Field(..., description="Detailed context setting for the scenario.")
    deadline: Optional[str] = Field(
        default=None, description="Optional ISO-formatted deadline for the scenario."
    )
    stressors: List[str] = Field(
        default_factory=list, description="List of stressors impacting the scenario."
    )
    success_criteria: List[str] = Field(
        default_factory=list, description="Success criteria defined for the scenario."
    )
