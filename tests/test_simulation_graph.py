from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from persona_sim.db.base import Base
from persona_sim.db.models import SimulationStatus
from persona_sim.db.repositories import get_run
from persona_sim.schemas.eval import (
    EvaluationReport,
    Objection,
    ObjectionCategory,
    ObjectionSeverity,
    WillDecision,
)
from persona_sim.schemas.persona import AuthorityLevel, PersonaConstraints, PersonaSpec
from persona_sim.schemas.scenario import ScenarioSpec
from persona_sim.schemas.sim_state import SimulationState
from persona_sim.schemas.stimulus import Stimulus, StimulusType
from persona_sim.schemas.transcript import TranscriptEventType
from persona_sim.sim.graph.graph import build_simulation_graph
from persona_sim.sim.graph.nodes import GraphDependencies
from persona_sim.sim.graph.state import GraphState, RunConfig, RunMode, TurnInput


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


async def _fake_persona_responder(
    messages, model_name: str, temperature: float
) -> str:  # type: ignore[override]
    prompt_text = " ".join(getattr(message, "content", "") for message in messages)
    stance = "yes" if "Follow-up" not in prompt_text else "no"
    severity = "low" if stance == "yes" else "high"
    return f'{{"stance": "{stance}", "severity": "{severity}", "message": "ok"}}'


async def _fake_evaluation_responder(messages) -> EvaluationReport:  # type: ignore[override]
    return EvaluationReport(
        will_buy=WillDecision.YES,
        will_use_daily=WillDecision.RELUCTANT,
        trust_delta=0.2,
        top_objections=[
            Objection(
                category=ObjectionCategory.COST,
                detail="Too expensive",
                severity=ObjectionSeverity.MEDIUM,
            )
        ],
        required_proof=["pricing benchmark"],
        recommended_next_steps=["share case study"],
    )


async def _run_graph(mode: RunMode) -> tuple[GraphState, async_sessionmaker]:
    session_factory = await _session_factory()
    personas = [_persona("Buyer"), _persona("User")]
    scenario = _scenario()
    run_id = uuid4()
    config = RunConfig(
        run_id=run_id,
        model_name="gpt-4o-mini",
        temperature=0.0,
        mode=mode,
        turns=[
            TurnInput(
                stimulus=Stimulus(type=StimulusType.MESSAGE, content="Launch"),
                question="Initial question",
            ),
            TurnInput(
                stimulus=Stimulus(type=StimulusType.FEATURE, content="Follow-up feature"),
                question="Follow-up detail" if mode == RunMode.MULTI_TURN else None,
            ),
        ],
        persona_modes={personas[0].id: "economic_buyer", personas[1].id: "daily_user"},
    )
    initial_state = GraphState(
        simulation=SimulationState(
            run_id=run_id,
            scenario=scenario,
            personas=personas,
            persona_states={},
            transcript=[],
            outputs=None,
        ),
        config=config,
        current_turn=0,
        latest_responses=[],
    )

    deps = GraphDependencies(
        session_factory=session_factory,
        persona_responder=_fake_persona_responder,
        evaluation_responder=_fake_evaluation_responder,
    )
    graph = build_simulation_graph(deps).compile()
    result = await graph.ainvoke(initial_state)
    validated = GraphState.model_validate(result)
    return validated, session_factory


def test_single_turn_graph_executes_and_updates_state() -> None:
    state, session_factory = asyncio.run(_run_graph(RunMode.SINGLE_TURN))

    assert state.simulation.outputs is not None
    assert state.simulation.outputs.will_buy == WillDecision.YES
    persona_state = state.simulation.persona_states[next(iter(state.simulation.persona_states))]
    assert persona_state.trust_state.trust_score > 0.5
    assert state.current_turn == 1
    assert any(
        event.event_type == TranscriptEventType.EVALUATION
        for event in state.simulation.transcript
    )

    async def _validate() -> None:
        async with session_factory() as session:
            run = await get_run(session, state.simulation.run_id)
            assert run is not None
            assert run.status == SimulationStatus.COMPLETED
            assert len(run.transcript) == 5

    asyncio.run(_validate())


def test_multi_turn_runs_all_turns_and_persists() -> None:
    state, session_factory = asyncio.run(_run_graph(RunMode.MULTI_TURN))

    assert state.current_turn == 2
    assert len(state.simulation.transcript) == 8
    assert state.simulation.outputs and state.simulation.outputs.trust_delta == 0.2

    first_persona_state = state.simulation.persona_states[
        next(iter(state.simulation.persona_states))
    ]
    assert first_persona_state.trust_state.trust_score < 0.5
    assert first_persona_state.trust_state.fatigue_score >= 0.05

    async def _validate() -> None:
        async with session_factory() as session:
            run = await get_run(session, state.simulation.run_id)
            assert run is not None
            assert run.status == SimulationStatus.COMPLETED
            assert len(run.transcript) == 8

    asyncio.run(_validate())
