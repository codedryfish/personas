"""Integration-style tests for the simulation repository."""

import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from persona_sim.db.base import Base
from persona_sim.db.models import SimulationStatus
from persona_sim.db.repositories import (
    add_event,
    create_run,
    get_run,
    save_evaluation,
    set_status,
)
from persona_sim.schemas.eval import EvaluationReport, Objection, ObjectionCategory, ObjectionSeverity
from persona_sim.schemas.persona import PersonaConstraints, PersonaSpec
from persona_sim.schemas.scenario import ScenarioSpec
from persona_sim.schemas.transcript import TranscriptEvent, TranscriptEventType


async def _build_sessionmaker() -> async_sessionmaker:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


async def _exercise_repository() -> None:
    session_factory = await _build_sessionmaker()
    run_id = uuid4()
    scenario = ScenarioSpec(
        id=uuid4(),
        title="Launch",
        context="Test context",
        deadline=None,
        stressors=["time"],
        success_criteria=["ship"],
    )
    personas = [
        PersonaSpec(
            id=uuid4(),
            name="Alex",
            role="Engineer",
            sector="Tech",
            locale="UK",
            incentives=["impact"],
            fears=["failure"],
            constraints=PersonaConstraints(
                time_per_week_minutes=120,
                budget_gbp=1000,
                ai_trust_level=4,
                authority_level="medium",
            ),
            communication_style="direct",
        )
    ]
    event = TranscriptEvent(
        timestamp="2024-01-01T00:00:00Z",
        actor="system",
        event_type=TranscriptEventType.SYSTEM,
        content="Simulation started",
        meta={"note": "init"},
    )
    evaluation = EvaluationReport(
        will_buy="yes",
        will_use_daily="reluctant",
        trust_delta=0.1,
        top_objections=[
            Objection(
                category=ObjectionCategory.TRUST,
                detail="Needs more transparency",
                severity=ObjectionSeverity.MEDIUM,
            )
        ],
        required_proof=["share roadmap"],
        recommended_next_steps=["follow-up"],
    )

    async with session_factory() as session:
        created = await create_run(
            session,
            run_id=run_id,
            scenario=scenario,
            personas=personas,
            mode="playback",
            model_name="gpt-4o-mini",
            temperature=0.2,
        )
        assert created.status == SimulationStatus.CREATED
        await add_event(session, run_id=run_id, event=event)
        await set_status(session, run_id=run_id, status=SimulationStatus.RUNNING)
        await save_evaluation(session, run_id=run_id, report=evaluation)

        fetched = await get_run(session, run_id)
        assert fetched is not None
        assert fetched.status == SimulationStatus.RUNNING
        assert fetched.transcript[0].content == event.content
        assert fetched.evaluation is not None
        assert fetched.evaluation.model_dump() == evaluation.model_dump()

        state = fetched.to_simulation_state()
        assert state.outputs is not None
        assert state.transcript[0].actor == "system"


def test_simulation_repository_crud() -> None:
    asyncio.run(_exercise_repository())
