from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from persona_sim.api.deps import get_simulation_service
from persona_sim.app.main import app
from persona_sim.schemas.eval import EvaluationReport, WillDecision
from persona_sim.schemas.persona import AuthorityLevel, PersonaConstraints, PersonaSpec
from persona_sim.schemas.scenario import ScenarioSpec
from persona_sim.schemas.sim_state import SimulationState
from persona_sim.schemas.stimulus import Stimulus, StimulusType
from persona_sim.schemas.transcript import TranscriptEvent, TranscriptEventType
from persona_sim.sim.errors import NotFoundError


class StubSimulationService:
    def __init__(self) -> None:
        self.run_id = uuid4()
        self.last_payload: dict | None = None
        self._state = self._build_state(self.run_id)

    async def start_run(self, **kwargs) -> UUID:
        self.last_payload = kwargs
        return self.run_id

    async def get_run(self, run_id: UUID) -> SimulationState:
        if run_id != self.run_id:
            raise NotFoundError(f"Run {run_id} not found")
        return self._state

    @staticmethod
    def _build_state(run_id: UUID) -> SimulationState:
        scenario = ScenarioSpec(
            id=uuid4(),
            title="Launch feature",
            context="Validate feature launch",
            stressors=["timeline"],
            success_criteria=["adoption"],
        )
        persona = PersonaSpec(
            id=uuid4(),
            name="Buyer",
            role="Lead",
            sector="Tech",
            locale="UK",
            incentives=["value"],
            fears=["risk"],
            constraints=PersonaConstraints(
                time_per_week_minutes=60,
                budget_gbp=5000,
                ai_trust_level=4,
                authority_level=AuthorityLevel.MEDIUM,
            ),
            communication_style="direct",
        )
        transcript = [
            TranscriptEvent(
                timestamp="2024-01-01T00:00:00Z",
                actor="system",
                event_type=TranscriptEventType.SYSTEM,
                content="Started",
            )
        ]
        evaluation = EvaluationReport(
            will_buy=WillDecision.YES,
            will_use_daily=WillDecision.YES,
            trust_delta=0.3,
            top_objections=[],
            required_proof=[],
            recommended_next_steps=[],
        )
        return SimulationState(
            run_id=run_id,
            scenario=scenario,
            personas=[persona],
            persona_states={},
            transcript=transcript,
            outputs=evaluation,
        )


@pytest.fixture()
def stub_service() -> StubSimulationService:
    stub = StubSimulationService()
    app.dependency_overrides[get_simulation_service] = lambda: stub
    yield stub
    app.dependency_overrides.clear()


@pytest.fixture()
def client(stub_service: StubSimulationService) -> TestClient:  # noqa: ARG001
    return TestClient(app)


def test_create_simulation_returns_run_id(client: TestClient, stub_service: StubSimulationService) -> None:
    payload = {
        "scenario": {
            "id": str(uuid4()),
            "title": "Launch feature",
            "context": "Validate feature launch",
            "stressors": ["timeline"],
            "success_criteria": ["adoption"],
        },
        "personas": [
            {
                "id": str(uuid4()),
                "name": "Buyer",
                "role": "Lead",
                "sector": "Tech",
                "locale": "UK",
                "incentives": ["value"],
                "fears": ["risk"],
                "constraints": {
                    "time_per_week_minutes": 60,
                    "budget_gbp": 5000,
                    "ai_trust_level": 4,
                    "authority_level": "medium",
                },
                "communication_style": "direct",
            }
        ],
        "stimuli": [{"type": StimulusType.MESSAGE.value, "content": "Hello"}],
        "run_mode": "single-turn",
        "steps": 1,
    }

    response = client.post("/v1/simulations", json=payload)

    assert response.status_code == 201
    assert response.json()["run_id"] == str(stub_service.run_id)
    assert stub_service.last_payload is not None
    assert stub_service.last_payload["run_mode"] == "single-turn"


def test_get_simulation_returns_state(client: TestClient, stub_service: StubSimulationService) -> None:
    response = client.get(f"/v1/simulations/{stub_service.run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == str(stub_service.run_id)
    assert body["scenario"]["title"] == "Launch feature"
    assert body["outputs"]["will_buy"] == WillDecision.YES.value


def test_get_simulation_not_found_returns_404(client: TestClient, stub_service: StubSimulationService) -> None:
    unknown_id = uuid4()

    response = client.get(f"/v1/simulations/{unknown_id}")

    assert response.status_code == 404
