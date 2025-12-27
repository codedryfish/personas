import pytest

from persona_sim.schemas.eval import ObjectionSeverity, WillDecision
from persona_sim.schemas.sim_state import TrustState
from persona_sim.sim.heuristics import (
    PersonaResponseObjection,
    PersonaResponseSummary,
    apply_persona_heuristics,
)


def _trust_state(trust: float = 0.5, fatigue: float = 0.0, risk: float = 0.5) -> TrustState:
    return TrustState(trust_score=trust, fatigue_score=fatigue, risk_tolerance=risk)


def test_yes_increases_trust_and_reduces_fatigue() -> None:
    previous = _trust_state(trust=0.5, fatigue=0.1, risk=0.7)
    response = PersonaResponseSummary(message="Yes", stance=WillDecision.YES, objections=[])

    updated = apply_persona_heuristics(previous=previous, response=response, mode="economic_buyer")

    assert updated.trust_score == 0.55
    assert updated.fatigue_score == 0.07
    assert updated.risk_tolerance == pytest.approx(0.686)


def test_reluctant_decreases_trust_and_increases_fatigue() -> None:
    previous = _trust_state(trust=0.6, fatigue=0.2, risk=0.8)
    response = PersonaResponseSummary(message="Maybe", stance=WillDecision.RELUCTANT, objections=[])

    updated = apply_persona_heuristics(previous=previous, response=response, mode="daily_user")

    assert updated.trust_score == pytest.approx(0.58)
    assert updated.fatigue_score == pytest.approx(0.22)
    assert updated.risk_tolerance == pytest.approx(0.756)


def test_no_decreases_trust_and_increases_fatigue() -> None:
    previous = _trust_state(trust=0.4, fatigue=0.0, risk=0.6)
    response = PersonaResponseSummary(message="No", stance=WillDecision.NO, objections=[])

    updated = apply_persona_heuristics(previous=previous, response=response, mode="anti_persona")

    assert updated.trust_score == pytest.approx(0.35)
    assert updated.fatigue_score == pytest.approx(0.03)
    assert updated.risk_tolerance == pytest.approx(0.594)


def test_high_severity_objections_stack() -> None:
    previous = _trust_state(trust=0.5, fatigue=0.0, risk=0.9)
    response = PersonaResponseSummary(
        message="Blockers remain",
        stance=WillDecision.YES,
        objections=[
            PersonaResponseObjection(detail="risk", severity=ObjectionSeverity.HIGH),
            PersonaResponseObjection(detail="cost", severity=ObjectionSeverity.HIGH),
        ],
    )

    updated = apply_persona_heuristics(previous=previous, response=response, mode="economic_buyer")

    assert updated.trust_score == pytest.approx(0.49)
    assert updated.fatigue_score == pytest.approx(0.01)
    assert updated.risk_tolerance == pytest.approx(0.898)


def test_risk_tolerance_clamped_and_decreases_with_fatigue() -> None:
    previous = _trust_state(trust=0.9, fatigue=0.9, risk=1.0)
    response = PersonaResponseSummary(message="No", stance=WillDecision.NO, objections=[])

    updated = apply_persona_heuristics(previous=previous, response=response, mode="daily_user")

    assert updated.fatigue_score == pytest.approx(0.93)
    assert updated.risk_tolerance == pytest.approx(0.814)
