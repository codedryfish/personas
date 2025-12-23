"""Factory for creating resilient LLM chat model instances."""

from __future__ import annotations

import os
from typing import Callable, Final, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

_MAX_RETRIES: Final = 3
_TIMEOUT_SECONDS: Final = 30

_T = TypeVar("_T")
RetryDecorator = Callable[[Callable[..., _T]], Callable[..., _T]]


class MissingApiKeyError(RuntimeError):
    """Raised when the required API key is absent."""


def _get_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise MissingApiKeyError("Set OPENAI_API_KEY to use the OpenAI chat model.")
    return api_key


def _retry_decorator() -> RetryDecorator:
    return retry(
        reraise=True,
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=8),
    )


def get_llm(model_name: str, temperature: float) -> BaseChatModel:
    """
    Return a LangChain chat model configured for resilience and low hallucination risk.

    The resulting model uses tenacity-driven retries for transient failures and expects
    the API key to be provided via the ``OPENAI_API_KEY`` environment variable.
    """

    api_key = _get_api_key()
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        max_retries=_MAX_RETRIES,
        timeout=_TIMEOUT_SECONDS,
        retry_decorator=_retry_decorator(),
    )
