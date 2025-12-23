from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel

from persona_sim.sim.llm import client, structured


class _StubChatModel:
    def __init__(self, responses: list[str | Exception]):
        self._responses = responses
        self.calls: list[Sequence[BaseMessage]] = []

    def invoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        self.calls.append(messages)
        if not self._responses:
            raise RuntimeError("No responses queued.")

        next_response = self._responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return AIMessage(content=next_response)


class _SampleOutput(BaseModel):
    title: str
    count: int


def test_get_llm_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(client.MissingApiKeyError):
        client.get_llm(model_name="gpt-4o-mini", temperature=0.0)


def test_get_llm_configures_chat_model(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_kwargs: dict[str, Any] = {}

    class _ChatOpenAIStub:
        def __init__(self, **kwargs: Any) -> None:
            captured_kwargs.update(kwargs)

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(client, "ChatOpenAI", _ChatOpenAIStub)

    model = client.get_llm(model_name="gpt-4o-mini", temperature=0.25)

    assert isinstance(model, _ChatOpenAIStub)
    assert captured_kwargs["api_key"] == "test-key"
    assert captured_kwargs["model"] == "gpt-4o-mini"
    assert captured_kwargs["temperature"] == 0.25
    assert captured_kwargs["max_retries"] > 0
    assert captured_kwargs["timeout"] > 0


def test_invoke_structured_retries_and_returns_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubChatModel(
        responses=[
            "not-json",
            '{"title": "Hello", "count": 2}',
        ]
    )
    monkeypatch.setattr(structured, "get_llm", lambda *_, **__: stub)

    prompt = [HumanMessage(content="Give me a title and count.")]

    result = structured.invoke_structured(prompt, _SampleOutput)

    assert result.title == "Hello"
    assert result.count == 2
    assert len(stub.calls) == 2
    assert "Fix your JSON" in stub.calls[-1][-1].content


def test_invoke_structured_raises_after_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubChatModel(responses=["{", "{", "{"])
    monkeypatch.setattr(structured, "get_llm", lambda *_, **__: stub)

    prompt = [HumanMessage(content="Return structured JSON.")]

    with pytest.raises(structured.StructuredOutputError):
        structured.invoke_structured(prompt, _SampleOutput)

    assert len(stub.calls) == 3
