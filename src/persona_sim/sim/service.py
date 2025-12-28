"""Service layer orchestrating simulation runs.

The service exposes a compact API for launching and retrieving simulation runs while keeping
callers insulated from LangGraph and persistence details. Responsibilities are kept narrow to
honor SOLID principles: validation and orchestration live here, execution is delegated to the
graph, and persistence is delegated to repositories.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from persona_sim.db.models import SimulationStatus
from persona_sim.core.config import get_settings
from persona_sim.db.repositories import get_run, set_status
from persona_sim.schemas.persona import PersonaSpec
from persona_sim.schemas.scenario import ScenarioSpec
from persona_sim.schemas.sim_state import SimulationState
from persona_sim.schemas.stimulus import Stimulus
from persona_sim.sim.errors import NotFoundError, RunFailedError, ValidationError
from persona_sim.sim.graph import GraphDependencies, GraphState, RunConfig, RunMode, TurnInput
from persona_sim.sim.graph.graph import build_simulation_graph
from persona_sim.sim.graph.nodes import EvaluationResponder, PersonaResponder


class SimulationService:
    """Coordinate simulation runs and retrieval."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        persona_responder: PersonaResponder | None = None,
        evaluation_responder: EvaluationResponder | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> None:
        settings = get_settings()
        self._session_factory = session_factory
        self._model_name = model_name or settings.model_name
        self._temperature = temperature if temperature is not None else settings.default_temperature
        self._persona_responder = persona_responder
        self._evaluation_responder = evaluation_responder

    async def start_run(
        self,
        *,
        scenario: ScenarioSpec,
        personas: Sequence[PersonaSpec],
        stimuli: Sequence[Stimulus],
        run_mode: str,
        steps: int = 1,
    ) -> uuid.UUID:
        """Validate inputs, execute the LangGraph run, and return the run identifier."""

        self._validate_inputs(personas=personas, stimuli=stimuli, steps=steps, run_mode=run_mode)
        mode = RunMode(run_mode)
        run_id = uuid.uuid4()
        turns = []
        for idx in range(steps):
            stimulus = stimuli[min(idx, len(stimuli) - 1)]
            turns.append(TurnInput(stimulus=stimulus, question=stimulus.question))
        config = RunConfig(
            run_id=run_id,
            model_name=self._model_name,
            temperature=self._temperature,
            mode=mode,
            turns=turns,
        )

        initial_state = GraphState(
            simulation=SimulationState(
                run_id=run_id,
                scenario=scenario,
                personas=list(personas),
                persona_states={},
                transcript=[],
                outputs=None,
            ),
            config=config,
            current_turn=0,
            latest_responses=[],
        )

        deps = self._build_dependencies()

        graph = build_simulation_graph(deps).compile()
        try:
            result = await graph.ainvoke(initial_state)
            _ = GraphState.model_validate(result)
        except Exception as exc:  # pragma: no cover - propagated as domain error
            await self._mark_run_failed(run_id)
            raise RunFailedError("Simulation run failed") from exc

        return run_id

    async def get_run(self, run_id: uuid.UUID) -> SimulationState:
        """Retrieve a completed or in-flight simulation."""

        async with self._session_factory() as session:
            dto = await get_run(session, run_id)
        if dto is None:
            raise NotFoundError(f"Run {run_id} not found")
        return dto.to_simulation_state()

    async def _mark_run_failed(self, run_id: uuid.UUID) -> None:
        try:
            async with self._session_factory() as session:
                await set_status(session, run_id=run_id, status=SimulationStatus.FAILED)
        except LookupError:  # pragma: no cover - best-effort status update
            return
        except Exception:  # pragma: no cover - best-effort status update
            return

    @staticmethod
    def _validate_inputs(
        *, personas: Sequence[PersonaSpec], stimuli: Sequence[Stimulus], steps: int, run_mode: str
    ) -> None:
        if not personas:
            raise ValidationError("At least one persona is required")
        if not stimuli:
            raise ValidationError("At least one stimulus is required")
        if steps <= 0:
            raise ValidationError("steps must be positive")
        try:
            RunMode(run_mode)
        except ValueError as exc:  # pragma: no cover - simple value guard
            raise ValidationError(f"Unsupported run mode: {run_mode}") from exc

    def _build_dependencies(self) -> GraphDependencies:
        persona_responder = self._persona_responder
        evaluation_responder = self._evaluation_responder

        kwargs = {}
        if persona_responder is not None:
            kwargs["persona_responder"] = persona_responder
        if evaluation_responder is not None:
            kwargs["evaluation_responder"] = evaluation_responder

        return GraphDependencies(session_factory=self._session_factory, **kwargs)
