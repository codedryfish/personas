"""Persistence helpers for simulation runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from persona_sim.db.models import (
    EvaluationReport as EvaluationReportModel,
    SimulationRun,
    SimulationStatus,
    TranscriptEvent as TranscriptEventModel,
)
from persona_sim.schemas.eval import EvaluationReport
from persona_sim.schemas.persona import PersonaSpec
from persona_sim.schemas.scenario import ScenarioSpec
from persona_sim.schemas.sim_state import SimulationState
from persona_sim.schemas.transcript import TranscriptEvent

_PERSONA_LIST_ADAPTER = TypeAdapter(List[PersonaSpec])


@dataclass(frozen=True)
class SimulationRunDTO:
    """Lightweight DTO exposing a hydrated simulation run."""

    run_id: UUID
    created_at: datetime
    scenario: ScenarioSpec
    personas: List[PersonaSpec]
    mode: str
    status: SimulationStatus
    model_name: str
    temperature: float
    transcript: List[TranscriptEvent]
    evaluation: Optional[EvaluationReport]

    def to_simulation_state(self) -> SimulationState:
        """Project the run into a SimulationState."""

        return SimulationState(
            run_id=self.run_id,
            scenario=self.scenario,
            personas=self.personas,
            persona_states={},
            transcript=self.transcript,
            outputs=self.evaluation,
        )


def _serialize_personas(personas: List[PersonaSpec]) -> str:
    personas_json = _PERSONA_LIST_ADAPTER.dump_json(personas)
    return personas_json.decode() if isinstance(personas_json, bytes) else personas_json


def _deserialize_personas(personas_json: str) -> List[PersonaSpec]:
    return _PERSONA_LIST_ADAPTER.validate_json(personas_json)


async def create_run(
    session: AsyncSession,
    *,
    run_id: UUID,
    scenario: ScenarioSpec,
    personas: List[PersonaSpec],
    mode: str,
    model_name: str,
    temperature: float,
    status: SimulationStatus = SimulationStatus.CREATED,
) -> SimulationRunDTO:
    """Create a new simulation run."""

    record = SimulationRun(
        run_id=str(run_id),
        scenario_json=scenario.model_dump_json(),
        personas_json=_serialize_personas(personas),
        mode=mode,
        status=status,
        model_name=model_name,
        temperature=temperature,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    created = await get_run(session, run_id)
    if created is None:
        msg = f"Failed to reload simulation run {run_id}"
        raise RuntimeError(msg)
    return created


async def add_event(session: AsyncSession, *, run_id: UUID, event: TranscriptEvent) -> None:
    """Persist a transcript event for a given run."""

    record = TranscriptEventModel(
        run_id=str(run_id),
        timestamp=event.timestamp,
        actor=event.actor,
        event_type=event.event_type.value,
        content=event.content,
        meta_json=json.dumps(event.meta) if event.meta is not None else None,
    )
    session.add(record)
    await session.commit()


async def set_status(session: AsyncSession, *, run_id: UUID, status: SimulationStatus) -> None:
    """Update the status of a simulation run."""

    query = (
        update(SimulationRun)
        .where(SimulationRun.run_id == str(run_id))
        .values(status=status)
        .execution_options(synchronize_session="fetch")
    )
    result = await session.execute(query)
    if result.rowcount == 0:
        msg = f"Simulation run {run_id} not found"
        raise LookupError(msg)
    await session.commit()


async def save_evaluation(
    session: AsyncSession, *, run_id: UUID, report: EvaluationReport
) -> None:
    """Save or replace the evaluation report for a run."""

    existing = await session.get(EvaluationReportModel, str(run_id))
    if existing:
        existing.report_json = report.model_dump_json()
    else:
        session.add(
            EvaluationReportModel(run_id=str(run_id), report_json=report.model_dump_json())
        )
    await session.commit()


async def get_run(session: AsyncSession, run_id: UUID) -> Optional[SimulationRunDTO]:
    """Fetch a run along with transcript events and evaluation output."""

    run_record = await session.get(SimulationRun, str(run_id))
    if not run_record:
        return None

    transcript_result = await session.execute(
        select(TranscriptEventModel)
        .where(TranscriptEventModel.run_id == run_record.run_id)
        .order_by(TranscriptEventModel.id)
    )
    transcript = [
        TranscriptEvent(
            timestamp=event.timestamp,
            actor=event.actor,
            event_type=event.event_type,
            content=event.content,
            meta=json.loads(event.meta_json) if event.meta_json else None,
        )
        for event in transcript_result.scalars().all()
    ]

    report_record = await session.get(EvaluationReportModel, run_record.run_id)
    evaluation = (
        EvaluationReport.model_validate_json(report_record.report_json) if report_record else None
    )

    scenario = ScenarioSpec.model_validate_json(run_record.scenario_json)
    personas = _deserialize_personas(run_record.personas_json)

    return SimulationRunDTO(
        run_id=UUID(run_record.run_id),
        created_at=run_record.created_at,
        scenario=scenario,
        personas=personas,
        mode=run_record.mode,
        status=run_record.status,
        model_name=run_record.model_name,
        temperature=run_record.temperature,
        transcript=transcript,
        evaluation=evaluation,
    )
