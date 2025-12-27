"""Persona prompt templates built as pure LangChain message lists."""

from __future__ import annotations

from typing import List, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from persona_sim.schemas.persona import PersonaSpec
from persona_sim.schemas.scenario import ScenarioSpec
from persona_sim.schemas.stimulus import Stimulus

WORD_LIMIT_DIRECTIVE = (
    "Keep responses concise: under 250 words unless the user explicitly requests a longer answer."
)
GROUNDING_DIRECTIVE = (
    "Only use grounded, role-consistent reasoning based on the provided persona, scenario, and stimulus; "
    "never invent external facts."
)
CLARIFICATION_DIRECTIVE = (
    "If critical details are missing, ask clarifying questions instead of assuming facts."
)
STRUCTURE_DIRECTIVE = (
    "Respond only with valid PersonaResponse JSON: "
    "{stance: one of [yes,no,reluctant]; "
    "top_concerns: array of 1-3 strings; "
    "objections: array of Objection {category, detail, severity}; "
    "required_proof: array of strings; "
    "short_answer: string capped at 120 words; "
    "clarifying_questions: optional array with up to 3 strings}. "
    "No extra commentary."
)

_MODE_DESCRIPTORS = {
    "economic_buyer": "You are the economic buyer who cares most about ROI, compliance, and contract risk.",
    "daily_user": "You are the daily user who cares most about usability, stability, and workflow fit.",
    "anti_persona": "You are an anti-persona who is skeptical, risk-averse, and resistant to adoption.",
}


def _format_persona_brief(persona: PersonaSpec) -> str:
    incentives = "; ".join(persona.incentives) if persona.incentives else "None listed"
    fears = "; ".join(persona.fears) if persona.fears else "None listed"
    constraints = persona.constraints
    constraint_summary = (
        f"Time/week: {constraints.time_per_week_minutes} minutes; "
        f"Budget: £{constraints.budget_gbp}; "
        f"AI trust: {constraints.ai_trust_level}/5; "
        f"Authority: {constraints.authority_level.value}"
    )
    communication = (
        persona.communication_style if persona.communication_style else "No specific preference stated."
    )
    return (
        f"Persona {persona.name} ({persona.role}, {persona.locale}) "
        f"Sector: {persona.sector or 'unspecified'}. "
        f"Incentives: {incentives}. Fears: {fears}. "
        f"Constraints: {constraint_summary}. "
        f"Communication style: {communication}"
    )


def _format_scenario_brief(scenario: ScenarioSpec) -> str:
    stressors = "; ".join(scenario.stressors) if scenario.stressors else "None listed"
    success_criteria = "; ".join(scenario.success_criteria) if scenario.success_criteria else "None listed"
    return (
        f"Scenario '{scenario.title}' ({scenario.id}): {scenario.context} "
        f"Deadline: {scenario.deadline or 'not specified'}. "
        f"Stressors: {stressors}. Success criteria: {success_criteria}."
    )


def build_persona_system_prompt(
    persona: PersonaSpec, scenario: ScenarioSpec, mode: str
) -> List[BaseMessage]:
    """Build the system prompt guiding persona responses."""
    if mode not in _MODE_DESCRIPTORS:
        raise ValueError(f"Unsupported mode '{mode}'. Expected one of {sorted(_MODE_DESCRIPTORS)}.")

    persona_brief = _format_persona_brief(persona)
    scenario_brief = _format_scenario_brief(scenario)
    mode_brief = _MODE_DESCRIPTORS[mode]

    content = "\n".join(
        [
            "You are a simulated persona in a product discovery conversation.",
            mode_brief,
            persona_brief,
            scenario_brief,
            GROUNDING_DIRECTIVE,
            CLARIFICATION_DIRECTIVE,
            STRUCTURE_DIRECTIVE,
            WORD_LIMIT_DIRECTIVE,
        ]
    )

    return [SystemMessage(content=content)]


def build_persona_user_prompt(stimulus: Stimulus, question: str | None) -> Sequence[BaseMessage]:
    """Build the user-facing prompt combining the stimulus and optional question."""
    stimulus_lines = [
        f"Stimulus type: {stimulus.type.value}",
        f"Content: {stimulus.content}",
    ]
    if stimulus.attachments:
        stimulus_lines.append(f"Attachments: {', '.join(stimulus.attachments)}")

    question_line = f"Question: {question}" if question else "Respond based on the stimulus."
    user_content = "\n".join(stimulus_lines + [question_line, STRUCTURE_DIRECTIVE, WORD_LIMIT_DIRECTIVE])

    return [HumanMessage(content=user_content)]
