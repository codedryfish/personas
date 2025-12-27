"""Schema for structured persona responses returned by the LLM."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from persona_sim.schemas.eval import Objection


class PersonaResponseStance(str, Enum):
    """Enumerated stance a persona can take in a response."""

    YES = "yes"
    NO = "no"
    RELUCTANT = "reluctant"


class PersonaResponse(BaseModel):
    """Structured representation of a persona's reply to a stimulus."""

    model_config = ConfigDict(extra="forbid")

    stance: PersonaResponseStance = Field(..., description="Overall stance taken.")
    top_concerns: List[str] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="List of the persona's top concerns.",
    )
    objections: List[Objection] = Field(
        default_factory=list, description="Specific objections raised by the persona."
    )
    required_proof: List[str] = Field(
        default_factory=list, description="Evidence the persona requires to be convinced."
    )
    short_answer: str = Field(
        ..., description="Concise natural-language summary, capped at 120 words."
    )
    clarifying_questions: Optional[List[str]] = Field(
        default=None, description="Optional clarifying questions, maximum of three entries."
    )

    @field_validator("short_answer")
    @classmethod
    def _limit_short_answer_words(cls, value: str) -> str:  # noqa: D401 - simple validation
        """Ensure the short answer does not exceed 120 words."""

        word_count = len(value.split())
        if word_count > 120:
            msg = f"short_answer must be 120 words or fewer (received {word_count})"
            raise ValueError(msg)
        return value

    @field_validator("clarifying_questions")
    @classmethod
    def _limit_clarifying_questions(
        cls, value: Optional[List[str]]
    ) -> Optional[List[str]]:  # noqa: D401 - simple validation
        """Ensure no more than three clarifying questions are returned."""

        if value is not None and len(value) > 3:
            msg = "clarifying_questions must contain at most 3 entries"
            raise ValueError(msg)
        return value
