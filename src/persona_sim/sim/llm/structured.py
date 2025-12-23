"""Helpers for structured LLM outputs to reduce hallucinations."""

from __future__ import annotations

import json
from typing import Any, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, ValidationError
from tenacity import Retrying, stop_after_attempt, wait_exponential

from persona_sim.sim.llm.client import get_llm

_DEFAULT_MODEL_NAME = "gpt-4o-mini"
_STRUCTURED_TEMPERATURE = 0.0
_VALIDATION_ATTEMPTS = 3


class StructuredOutputError(RuntimeError):
    """Raised when a structured response cannot be produced."""


def _build_retryer() -> Retrying:
    return Retrying(
        stop=stop_after_attempt(_VALIDATION_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )


def _normalize_content(message: BaseMessage | str) -> str:
    if isinstance(message, BaseMessage):
        return str(message.content)
    return str(message)


def _parse_and_validate(content: str, output_model: type[BaseModel]) -> BaseModel:
    parsed: Any = json.loads(content)
    return output_model.model_validate(parsed)


def _next_messages(
    original_messages: Sequence[BaseMessage],
    validation_error: Exception,
    last_content: str,
) -> list[BaseMessage]:
    guidance = (
        "Fix your JSON. Return ONLY valid JSON that matches the expected schema. "
        f"Validation errors: {validation_error}. "
        f"Last response content: {last_content}"
    )
    return [*original_messages, SystemMessage(content=guidance)]


def invoke_structured(
    prompt_messages: Sequence[BaseMessage], output_model: type[BaseModel]
) -> BaseModel:
    """
    Invoke the LLM and validate the response into the requested Pydantic model.

    If validation fails, the function retries with targeted guidance to correct the output while
    keeping the API surface narrow enough to swap out providers in the future.
    """

    messages: list[BaseMessage] = list(prompt_messages)
    llm: BaseChatModel = get_llm(_DEFAULT_MODEL_NAME, temperature=_STRUCTURED_TEMPERATURE)
    retryer = _build_retryer()
    last_error: Exception | None = None
    last_content = ""

    for _ in range(_VALIDATION_ATTEMPTS):
        try:
            response = retryer(llm.invoke, messages)
        except Exception as exc:
            raise StructuredOutputError("LLM invocation failed after retries.") from exc

        last_content = _normalize_content(response)
        try:
            return _parse_and_validate(last_content, output_model)
        except (ValidationError, json.JSONDecodeError) as validation_error:
            last_error = validation_error
            messages = _next_messages(prompt_messages, validation_error, last_content)

    raise StructuredOutputError("Failed to produce a valid structured response.") from last_error
