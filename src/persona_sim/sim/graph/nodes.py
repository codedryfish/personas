"""LangGraph node implementations for persona simulations."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from langchain_core.messages import BaseMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from persona_sim.db.models import SimulationStatus
from persona_sim.db.repositories import add_event, create_run, save_evaluation, set_status
from persona_sim.schemas.eval import EvaluationReport, ObjectionSeverity, WillDecision
from persona_sim.schemas.persona import PersonaSpec
from persona_sim.schemas.persona_response import PersonaResponse as PersonaResponsePayload
from persona_sim.schemas.sim_state import PersonaState, SimulationState, TrustState
from persona_sim.schemas.transcript import TranscriptEvent, TranscriptEventType
from persona_sim.sim.heuristics import (
    PersonaResponseObjection,
    PersonaResponseSummary,
    apply_persona_heuristics,
)
from persona_sim.sim.graph.state import GraphState, PersonaResponse, RunMode, TurnInput
from persona_sim.sim.llm.client import get_llm
from persona_sim.sim.llm.structured import StructuredOutputError, invoke_structured
from persona_sim.sim.prompts.eval_prompts import build_evaluator_prompt
from persona_sim.sim.prompts.persona_prompts import (
    build_persona_system_prompt,
    build_persona_user_prompt,
)

PersonaResponder = Callable[
    [Sequence[BaseMessage], str, float], Awaitable[str | PersonaResponsePayload]
]
EvaluationResponder = Callable[[Sequence[BaseMessage]], Awaitable[EvaluationReport]]

_DEFAULT_TRUST = 0.5
_DEFAULT_FATIGUE = 0.0
_DEFAULT_RISK_TOLERANCE = 0.5


@dataclass(slots=True)
class GraphDependencies:
    """External dependencies injected into node functions."""

    session_factory: async_sessionmaker[AsyncSession]
    persona_responder: PersonaResponder = field(default_factory=lambda: _default_persona_responder)
    evaluation_responder: EvaluationResponder = field(
        default_factory=lambda: _default_evaluation_responder
    )


async def _default_persona_responder(
    messages: Sequence[BaseMessage], model_name: str, temperature: float
) -> PersonaResponsePayload:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, lambda: invoke_structured(messages, PersonaResponsePayload)
    )


async def _default_evaluation_responder(messages: Sequence[BaseMessage]) -> EvaluationReport:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: invoke_structured(messages, EvaluationReport))


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _highest_severity(summary: PersonaResponseSummary) -> ObjectionSeverity:
    if any(obj.severity == ObjectionSeverity.HIGH for obj in summary.objections):
        return ObjectionSeverity.HIGH
    if any(obj.severity == ObjectionSeverity.MEDIUM for obj in summary.objections):
        return ObjectionSeverity.MEDIUM
    return ObjectionSeverity.LOW


def _parse_persona_response(
    raw_response: str | PersonaResponsePayload, prompt_messages: Sequence[BaseMessage]
) -> PersonaResponsePayload:
    if isinstance(raw_response, PersonaResponsePayload):
        return raw_response

    content = str(raw_response)
    stripped = content.strip()
    if not stripped:
        return invoke_structured(prompt_messages, PersonaResponsePayload)

    try:
        return PersonaResponsePayload.model_validate_json(content)
    except Exception:
        pass

    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(content)
            return PersonaResponsePayload.model_validate(parsed)
        except Exception:
            try:
                return invoke_structured(prompt_messages, PersonaResponsePayload)
            except StructuredOutputError:
                pass

    return invoke_structured(prompt_messages, PersonaResponsePayload)


def _to_summary_from_payload(payload: PersonaResponsePayload) -> PersonaResponseSummary:
    objections = [
        PersonaResponseObjection(detail=obj.detail, severity=obj.severity)
        for obj in payload.objections
    ]
    stance = WillDecision(payload.stance.value)
    return PersonaResponseSummary(message=payload.short_answer, stance=stance, objections=objections)


def _resolve_persona_mode(
    persona_id: UUID, personas: list[PersonaSpec], mode_map: dict[UUID, str]
) -> str:
    if persona_id in mode_map:
        return mode_map[persona_id]

    fallback_modes = ("economic_buyer", "daily_user", "anti_persona")
    index = next((idx for idx, persona in enumerate(personas) if persona.id == persona_id), 0)
    return fallback_modes[index % len(fallback_modes)]


def _initialize_persona_state(persona: PersonaSpec) -> PersonaState:
    return PersonaState(
        persona_id=persona.id,
        trust_state=TrustState(
            trust_score=_DEFAULT_TRUST,
            fatigue_score=_DEFAULT_FATIGUE,
            risk_tolerance=_DEFAULT_RISK_TOLERANCE,
        ),
    )


def _merge_persona_states(state: GraphState) -> dict[UUID, PersonaState]:
    merged = dict(state.simulation.persona_states)
    for persona in state.simulation.personas:
        merged.setdefault(persona.id, _initialize_persona_state(persona))
    return merged


def _attach_event(
    simulation: SimulationState,
    *,
    actor: str,
    event_type: TranscriptEventType,
    content: str,
    meta: dict | None = None,
    step: int | None = None,
) -> SimulationState:
    merged_meta = dict(meta or {})
    if step is not None:
        merged_meta.setdefault("step", step)
    event = TranscriptEvent(
        timestamp=_timestamp(),
        actor=actor,
        event_type=event_type,
        content=content,
        meta=merged_meta or None,
    )
    transcript = [*simulation.transcript, event]
    return simulation.model_copy(update={"transcript": transcript})


def _question_content(turn_question: str | None, stimulus_summary: str) -> str:
    if turn_question:
        return f"{stimulus_summary}\nQuestion: {turn_question}"
    return stimulus_summary


def _stimulus_summary(turn_input: TurnInput) -> str:
    stimulus = turn_input.stimulus
    attachments = (
        f" Attachments: {', '.join(stimulus.attachments)}." if stimulus.attachments else ""
    )
    return f"Stimulus ({stimulus.type.value}): {stimulus.content}.{attachments}"


def _event_for_response(
    persona: PersonaSpec,
    payload: PersonaResponsePayload,
    summary: PersonaResponseSummary,
    *,
    step: int,
) -> TranscriptEvent:
    severity = _highest_severity(summary)
    return TranscriptEvent(
        timestamp=_timestamp(),
        actor=persona.name,
        event_type=TranscriptEventType.ANSWER,
        content=summary.message,
        meta={
            "step": step,
            "stance": summary.stance.value,
            "severity": severity.value,
            "raw": payload.model_dump(),
        },
    )


async def init_run_node(state: GraphState, deps: GraphDependencies) -> GraphState:
    simulation = state.simulation
    merged_persona_states = _merge_persona_states(state)
    simulation = simulation.model_copy(update={"persona_states": merged_persona_states})
    simulation = _attach_event(
        simulation,
        actor="system",
        event_type=TranscriptEventType.SYSTEM,
        content="Simulation started",
    )

    async with deps.session_factory() as session:
        await create_run(
            session,
            run_id=simulation.run_id,
            scenario=simulation.scenario,
            personas=simulation.personas,
            mode=state.config.mode.value,
            model_name=state.config.model_name,
            temperature=state.config.temperature,
            status=SimulationStatus.RUNNING,
        )

    return state.model_copy(update={"simulation": simulation})


async def persona_response_node(state: GraphState, deps: GraphDependencies) -> GraphState:
    turn_count = len(state.config.turns) or 1
    max_turns = 1 if state.config.mode is RunMode.SINGLE_TURN else turn_count
    if state.current_turn >= max_turns:
        return state

    turn_input = state.config.turns[state.current_turn] if state.config.turns else None
    if turn_input is None:
        return state

    stimulus_text = _stimulus_summary(turn_input)
    question_event_content = _question_content(turn_input.question, stimulus_text)
    simulation = _attach_event(
        state.simulation,
        actor="system",
        event_type=TranscriptEventType.QUESTION,
        content=question_event_content,
        step=state.current_turn + 1,
    )

    responses: list[TranscriptEvent] = []
    persona_responses: list[PersonaResponse] = []
    for persona in simulation.personas:
        persona_mode = _resolve_persona_mode(
            persona.id, simulation.personas, state.config.persona_modes
        )
        system_prompt = build_persona_system_prompt(persona, simulation.scenario, mode=persona_mode)
        user_prompt = build_persona_user_prompt(turn_input.stimulus, turn_input.question)
        prompt_messages = [*system_prompt, *user_prompt]
        raw_response = await deps.persona_responder(
            [*system_prompt, *user_prompt],
            state.config.model_name,
            state.config.temperature,
        )
        payload = _parse_persona_response(raw_response, prompt_messages)
        summary = _to_summary_from_payload(payload)
        response_event = _event_for_response(
            persona, payload, summary, step=state.current_turn + 1
        )
        responses.append(response_event)
        persona_responses.append(
            PersonaResponse(
                persona_id=persona.id,
                content=payload.short_answer,
                persona_mode=persona_mode,
                summary=summary,
                stance=summary.stance,
                objection_severity=_highest_severity(summary),
            )
        )

    updated_transcript = [*simulation.transcript, *responses]
    simulation = simulation.model_copy(update={"transcript": updated_transcript})

    return state.model_copy(
        update={"simulation": simulation, "latest_responses": persona_responses}
    )


async def update_state_node(state: GraphState) -> GraphState:
    persona_states = _merge_persona_states(state)

    for response in state.latest_responses:
        persona_state = persona_states.get(response.persona_id) or _initialize_persona_state(
            next(p for p in state.simulation.personas if p.id == response.persona_id)
        )
        updated_trust_state = apply_persona_heuristics(
            previous=persona_state.trust_state,
            response=response.summary,
            mode=response.persona_mode,
        )

        persona_states[response.persona_id] = persona_state.model_copy(
            update={"trust_state": updated_trust_state}
        )

    next_turn = state.current_turn + 1
    simulation = state.simulation.model_copy(update={"persona_states": persona_states})
    return state.model_copy(update={"simulation": simulation, "current_turn": next_turn})


async def evaluator_node(state: GraphState, deps: GraphDependencies) -> GraphState:
    simulation = state.simulation
    prompt = build_evaluator_prompt(simulation.transcript, simulation.personas, simulation.scenario)
    report = await deps.evaluation_responder(prompt)

    evaluation_event = TranscriptEvent(
        timestamp=_timestamp(),
        actor="system",
        event_type=TranscriptEventType.EVALUATION,
        content="Evaluation completed",
        meta=report.model_dump(),
    )
    transcript = [*simulation.transcript, evaluation_event]
    simulation = simulation.model_copy(update={"outputs": report, "transcript": transcript})
    return state.model_copy(update={"simulation": simulation})


async def persist_node(state: GraphState, deps: GraphDependencies) -> GraphState:
    simulation = state.simulation
    async with deps.session_factory() as session:
        await _persist_transcript(session, simulation.run_id, simulation.transcript)
        if simulation.outputs:
            await save_evaluation(session, run_id=simulation.run_id, report=simulation.outputs)
        await set_status(session, run_id=simulation.run_id, status=SimulationStatus.COMPLETED)

    return state


async def _persist_transcript(
    session: AsyncSession, run_id: UUID, transcript: Iterable[TranscriptEvent]
) -> None:
    for event in transcript:
        await add_event(session, run_id=run_id, event=event)
