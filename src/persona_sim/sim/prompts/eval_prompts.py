"""Evaluator prompt templates producing structured EvaluationReport JSON."""

from __future__ import annotations

from typing import Iterable, List

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from persona_sim.schemas.persona import PersonaSpec
from persona_sim.schemas.scenario import ScenarioSpec
from persona_sim.schemas.transcript import TranscriptEvent

EVALUATOR_DIRECTIVE = (
    "Return only valid JSON matching the EvaluationReport schema without additional commentary."
)
EVALUATOR_REMINDERS = (
    "Summarize objections, required proof, and recommend next steps based strictly on the transcript."
)


def _summarize_personas(personas: Iterable[PersonaSpec]) -> str:
    summaries: List[str] = []
    for persona in personas:
        summaries.append(f"{persona.name} ({persona.role}, {persona.locale}) [{persona.id}]")
    return "; ".join(summaries) if summaries else "No personas provided."


def _summarize_events(events: Iterable[TranscriptEvent]) -> str:
    lines: List[str] = []
    for event in events:
        lines.append(f"{event.timestamp} - {event.actor} ({event.event_type.value}): {event.content}")
    return "\n".join(lines) if lines else "No transcript events recorded."


def build_evaluator_prompt(
    transcript_events: Iterable[TranscriptEvent],
    personas: Iterable[PersonaSpec],
    scenario: ScenarioSpec,
) -> List[BaseMessage]:
    """Build the evaluator prompt requesting a structured EvaluationReport JSON output."""
    system_content = "\n".join(
        [
            "You are an impartial evaluator converting the conversation into an EvaluationReport JSON.",
            EVALUATOR_DIRECTIVE,
            EVALUATOR_REMINDERS,
        ]
    )

    transcript_section = _summarize_events(transcript_events)
    persona_section = _summarize_personas(personas)
    scenario_section = (
        f"Scenario '{scenario.title}' ({scenario.id}): {scenario.context} "
        f"Stressors: {', '.join(scenario.stressors) if scenario.stressors else 'none'}. "
        f"Success criteria: {', '.join(scenario.success_criteria) if scenario.success_criteria else 'none'}."
    )

    user_content = "\n\n".join(
        [
            "Produce the EvaluationReport JSON with fields: will_buy, will_use_daily, trust_delta, "
            "top_objections, required_proof, recommended_next_steps.",
            f"Personas: {persona_section}",
            f"Scenario: {scenario_section}",
            "Transcript:",
            transcript_section,
        ]
    )

    return [SystemMessage(content=system_content), HumanMessage(content=user_content)]
