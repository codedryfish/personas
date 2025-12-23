"""Transcript event schemas for simulation logging."""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class TranscriptEventType(str, Enum):
    """Enumeration of transcript event categories."""

    QUESTION = "question"
    ANSWER = "answer"
    SYSTEM = "system"
    EVALUATION = "evaluation"


class TranscriptEvent(BaseModel):
    """Event entry recorded during a simulation run."""

    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(..., description="Timestamp of the event in ISO format.")
    actor: str = Field(..., description='Actor generating the event, persona ID or "system".')
    event_type: TranscriptEventType = Field(..., description="Category of the transcript event.")
    content: str = Field(..., description="Primary content of the event.")
    meta: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata associated with the event."
    )

