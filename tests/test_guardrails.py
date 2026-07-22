from __future__ import annotations

from config.settings import GuardrailSettings
from models.target import InvestigationTarget
from validation.guardrails import GuardrailTracker


def test_max_iterations_reached():
    tracker = GuardrailTracker(settings=GuardrailSettings(max_iterations=2))
    assert tracker.max_iterations_reached() is False

    tracker.record_iteration()
    assert tracker.max_iterations_reached() is False

    tracker.record_iteration()
    assert tracker.max_iterations_reached() is True


def test_duplicate_limit_resets_on_progress():
    tracker = GuardrailTracker(settings=GuardrailSettings(duplicate_investigation_limit=2))
    target = InvestigationTarget(name="Authentication")

    tracker.record_investigation_attempt(target, made_progress=False)
    assert tracker.duplicate_limit_exceeded(target) is False

    tracker.record_investigation_attempt(target, made_progress=False)
    assert tracker.duplicate_limit_exceeded(target) is True

    tracker.record_investigation_attempt(target, made_progress=True)
    assert tracker.duplicate_limit_exceeded(target) is False


def test_duplicate_limit_is_tracked_per_target():
    tracker = GuardrailTracker(settings=GuardrailSettings(duplicate_investigation_limit=1))
    target_a = InvestigationTarget(name="A")
    target_b = InvestigationTarget(name="B")

    tracker.record_investigation_attempt(target_a, made_progress=False)

    assert tracker.duplicate_limit_exceeded(target_a) is True
    assert tracker.duplicate_limit_exceeded(target_b) is False
