"""Stimulus schemas used to drive persona simulations."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StimulusType(str, Enum):
    """Enumeration of stimulus categories."""

    FEATURE = "feature"
    PRICING = "pricing"
    MESSAGE = "message"
    INCIDENT = "incident"


class Stimulus(BaseModel):
    """Input stimulus presented during a simulation run."""

    model_config = ConfigDict(extra="forbid")

    type: StimulusType = Field(..., description="Type of the stimulus.")
    content: str = Field(..., description="Primary content of the stimulus.")
    question: Optional[str] = Field(
        default=None, description="Optional follow-up question paired with the stimulus."
    )
    attachments: Optional[List[str]] = Field(
        default=None,
        description="Optional list of attachment references, such as URLs or asset IDs.",
    )
