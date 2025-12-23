"""Scenario-related Pydantic schemas."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScenarioSpec(BaseModel):
    """Specification for a simulation scenario."""

    model_config = ConfigDict(extra="forbid")

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

