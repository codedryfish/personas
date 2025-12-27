from __future__ import annotations

from uuid import uuid4

from persona_sim.schemas.persona import AuthorityLevel, PersonaConstraints, PersonaSpec
from persona_sim.schemas.scenario import ScenarioSpec
from persona_sim.schemas.stimulus import Stimulus, StimulusType
from persona_sim.schemas.transcript import TranscriptEvent, TranscriptEventType
from persona_sim.sim.prompts.eval_prompts import build_evaluator_prompt
from persona_sim.sim.prompts.persona_prompts import (
    build_persona_system_prompt,
    build_persona_user_prompt,
)


def _persona() -> PersonaSpec:
    return PersonaSpec(
        id=uuid4(),
        name="Jordan Taylor",
        role="Head of Operations",
        sector="Healthcare",
        locale="UK",
        incentives=["Reduce costs", "Improve safety"],
        fears=["Downtime", "Compliance breaches"],
        constraints=PersonaConstraints(
            time_per_week_minutes=120,
            budget_gbp=50000,
            ai_trust_level=3,
            authority_level=AuthorityLevel.HIGH,
        ),
        communication_style="Precise and concise",
    )


def _scenario() -> ScenarioSpec:
    return ScenarioSpec(
        id=uuid4(),
        title="Introduce AI triage",
        context="Exploring AI to triage incoming patient queries.",
        stressors=["Regulation", "Data privacy"],
        success_criteria=["Reduce wait times", "Maintain accuracy"],
    )


def test_persona_system_prompt_includes_required_directives() -> None:
    content = build_persona_system_prompt(_persona(), _scenario(), mode="daily_user")[0].content

    assert "PersonaResponse JSON" in content
    assert "stance: one of [yes,no,reluctant]" in content
    assert "top_concerns: array of 1-3 strings" in content
    assert "never invent external facts" in content
    assert "No extra commentary" in content


def test_persona_user_prompt_includes_structure_and_limits() -> None:
    stimulus = Stimulus(type=StimulusType.FEATURE, content="Dashboard improvements")
    content = build_persona_user_prompt(stimulus, question="How does this affect your workflow?")[0].content

    assert "Stimulus type: feature" in content
    assert "PersonaResponse JSON" in content
    assert "short_answer: string capped at 120 words" in content


def test_evaluator_prompt_requests_evaluation_report_json() -> None:
    transcript = [
        TranscriptEvent(
            timestamp="2024-01-01T00:00:00Z",
            actor="system",
            event_type=TranscriptEventType.SYSTEM,
            content="Simulation start",
        )
    ]
    messages = build_evaluator_prompt(transcript, personas=[_persona()], scenario=_scenario())

    system_content = messages[0].content
    user_content = messages[1].content

    assert "EvaluationReport JSON" in system_content
    assert "Return only valid JSON" in system_content
    assert "EvaluationReport JSON" in user_content
    assert "will_buy" in user_content
