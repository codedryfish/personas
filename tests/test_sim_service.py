from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from persona_sim.db.base import Base
from persona_sim.db.models import SimulationRun, SimulationStatus
from persona_sim.db.repositories import get_run
from persona_sim.schemas.eval import EvaluationReport, WillDecision
from persona_sim.schemas.persona import AuthorityLevel, PersonaConstraints, PersonaSpec
from persona_sim.schemas.scenario import ScenarioSpec
from persona_sim.schemas.stimulus import Stimulus, StimulusType
from persona_sim.sim.errors import NotFoundError, RunFailedError, ValidationError
from persona_sim.sim.service import SimulationService


async def _session_factory() -> async_sessionmaker:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def _persona(name: str) -> PersonaSpec:
    return PersonaSpec(
        id=uuid4(),
        name=name,
        role="Lead",
        sector="Tech",
        locale="UK",
        incentives=["outcomes"],
        fears=["downtime"],
        constraints=PersonaConstraints(
            time_per_week_minutes=120,
            budget_gbp=10000,
            ai_trust_level=4,
            authority_level=AuthorityLevel.MEDIUM,
        ),
        communication_style="direct",
    )


def _scenario() -> ScenarioSpec:
    return ScenarioSpec(
        id=uuid4(),
        title="Adopt platform",
        context="Testing adoption",
        stressors=["cost"],
        success_criteria=["value"],
    )


async def _fake_persona_responder(*_) -> str:  # type: ignore[override]
    return (
        '{"stance": "yes", "top_concerns": ["value"], "objections": [], '
        '"required_proof": ["case study"], "short_answer": "Yes, I agree.", '
        '"clarifying_questions": []}'
    )


async def _fake_evaluation_responder(*_) -> EvaluationReport:  # type: ignore[override]
    return EvaluationReport(
        will_buy=WillDecision.YES,
        will_use_daily=WillDecision.YES,
        trust_delta=0.1,
        top_objections=[],
        required_proof=[],
        recommended_next_steps=[],
    )


def _run(coro):
    return asyncio.run(coro)


def test_start_run_validates_and_persists() -> None:
    session_factory = _run(_session_factory())
    service = SimulationService(
        session_factory=session_factory,
        persona_responder=_fake_persona_responder,
        evaluation_responder=_fake_evaluation_responder,
    )
    scenario = _scenario()
    personas = [_persona("Buyer")]
    stimuli = [Stimulus(type=StimulusType.MESSAGE, content="Hello")]

    run_id = _run(
        service.start_run(
            scenario=scenario,
            personas=personas,
            stimuli=stimuli,
            run_mode="single-turn",
        )
    )

    async def _fetch():
        async with session_factory() as session:
            return await get_run(session, run_id)

    stored = _run(_fetch())
    assert stored is not None
    assert stored.scenario.title == scenario.title
    assert stored.status == SimulationStatus.COMPLETED


def test_start_run_rejects_invalid_inputs() -> None:
    session_factory = _run(_session_factory())
    service = SimulationService(session_factory=session_factory)
    scenario = _scenario()
    persona = _persona("Buyer")
    stimulus = Stimulus(type=StimulusType.MESSAGE, content="Hello")

    async def _run_call(**kwargs):
        return await service.start_run(**kwargs)

    with pytest.raises(ValidationError):
        _run(
            _run_call(
                scenario=scenario, personas=[], stimuli=[stimulus], run_mode="single-turn"
            )
        )

    with pytest.raises(ValidationError):
        _run(
            _run_call(
                scenario=scenario, personas=[persona], stimuli=[], run_mode="single-turn"
            )
        )

    with pytest.raises(ValidationError):
        _run(
            _run_call(
                scenario=scenario,
                personas=[persona],
                stimuli=[stimulus],
                run_mode="invalid-mode",
            )
        )


def test_get_run_returns_projection() -> None:
    session_factory = _run(_session_factory())
    service = SimulationService(
        session_factory=session_factory,
        persona_responder=_fake_persona_responder,
        evaluation_responder=_fake_evaluation_responder,
    )
    scenario = _scenario()
    personas = [_persona("Buyer")]
    stimuli = [Stimulus(type=StimulusType.MESSAGE, content="Hello")]

    run_id = _run(
        service.start_run(
            scenario=scenario,
            personas=personas,
            stimuli=stimuli,
            run_mode="single-turn",
        )
    )

    state = _run(service.get_run(run_id))
    assert state.run_id == run_id
    assert state.scenario.title == scenario.title


def test_get_run_not_found_raises() -> None:
    session_factory = _run(_session_factory())
    service = SimulationService(session_factory=session_factory)
    with pytest.raises(NotFoundError):
        _run(service.get_run(uuid4()))


def test_start_run_repeats_last_stimulus_when_steps_exceed_count() -> None:
    session_factory = _run(_session_factory())
    service = SimulationService(
        session_factory=session_factory,
        persona_responder=_fake_persona_responder,
        evaluation_responder=_fake_evaluation_responder,
    )
    scenario = _scenario()
    personas = [_persona("Buyer")]
    stimuli = [Stimulus(type=StimulusType.MESSAGE, content="Hello", question="First?")]

    run_id = _run(
        service.start_run(
            scenario=scenario,
            personas=personas,
            stimuli=stimuli,
            run_mode="multi-turn",
            steps=2,
        )
    )

    async def _fetch():
        async with session_factory() as session:
            return await get_run(session, run_id)

    stored = _run(_fetch())
    assert stored is not None
    assert stored.status == SimulationStatus.COMPLETED
    assert len(stored.transcript) == 6

    question_events = [event for event in stored.transcript if event.event_type.value == "question"]
    assert len(question_events) == 2
    assert {event.meta.get("step") for event in question_events} == {1, 2}


def test_run_failure_marks_status_failed() -> None:
    session_factory = _run(_session_factory())

    async def _failing_responder(*_) -> str:  # type: ignore[override]
        raise RuntimeError("boom")

    service = SimulationService(
        session_factory=session_factory,
        persona_responder=_failing_responder,
        evaluation_responder=_fake_evaluation_responder,
    )
    scenario = _scenario()
    personas = [_persona("Buyer")]
    stimuli = [Stimulus(type=StimulusType.MESSAGE, content="Hello")]

    with pytest.raises(RunFailedError):
        _run(
            service.start_run(
                scenario=scenario,
                personas=personas,
                stimuli=stimuli,
                run_mode="single-turn",
            )
        )

    async def _fetch_last_run():
        async with session_factory() as session:
            result = await session.execute(
                select(SimulationRun).order_by(SimulationRun.created_at.desc()).limit(1)
            )
            return result.scalars().first()

    run_record = _run(_fetch_last_run())
    assert run_record is not None
    assert run_record.status == SimulationStatus.FAILED
