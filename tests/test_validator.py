from __future__ import annotations

from pathlib import Path

from agents.validator import Validator
from models.observation import Observation
from models.repository import RepositoryMetadata, RepositoryProfile
from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState


def _state(*targets: InvestigationTarget) -> RepositoryState:
    profile = RepositoryProfile(
        path=Path("."),
        name="fixture",
        has_dockerfile=True,
        has_docker_compose=False,
        has_raven_directory=True,
        contract_valid=True,
    )
    return RepositoryState(
        repository_profile=profile, repository_metadata=RepositoryMetadata(), investigation_targets=list(targets)
    )


def test_validate_target_ignores_targets_not_runtime_verified():
    target = InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED)
    state = _state(target)

    Validator().validate_target(state, target)

    assert target.state == TargetState.STATIC_VERIFIED


def test_validate_target_becomes_validated_with_evidence_and_observation():
    target = InvestigationTarget(
        name="Authentication",
        state=TargetState.RUNTIME_VERIFIED,
        static_evidence=["app/auth.py"],
        runtime_evidence=["gateway.py --input sample_input.json (status=success)"],
    )
    state = _state(target)
    state.observation_store.add(
        Observation(category="Authentication", claim="static ok", evidence=("app/auth.py",), source="Investigator")
    )
    state.observation_store.add(
        Observation(
            category="Authentication",
            claim="runtime ok",
            evidence=("gateway.py",),
            source="Executor",
            runtime_verified=True,
        )
    )

    Validator().validate_target(state, target)

    assert target.state == TargetState.VALIDATED


def test_validate_target_marks_insufficient_evidence_when_missing_evidence():
    target = InvestigationTarget(name="Authentication", state=TargetState.RUNTIME_VERIFIED)
    state = _state(target)

    Validator().validate_target(state, target)

    assert target.state == TargetState.INSUFFICIENT_EVIDENCE


def test_validate_target_detects_contradiction_when_no_runtime_observation_backs_it():
    target = InvestigationTarget(
        name="Authentication",
        state=TargetState.RUNTIME_VERIFIED,
        static_evidence=["app/auth.py"],
        runtime_evidence=["gateway.py --input sample_input.json (status=success)"],
    )
    state = _state(target)
    # No Observation added at all — the target claims RUNTIME_VERIFIED but nothing backs it.

    Validator().validate_target(state, target)

    assert target.state == TargetState.INSUFFICIENT_EVIDENCE


def test_mark_insufficient_evidence_does_not_override_terminal_state():
    target = InvestigationTarget(name="Authentication", state=TargetState.VALIDATED)
    state = _state(target)

    Validator().mark_insufficient_evidence(state, target, "some reason")

    assert target.state == TargetState.VALIDATED


def test_cascade_guardrail_limit_marks_all_non_terminal_targets():
    validated = InvestigationTarget(name="A", state=TargetState.VALIDATED)
    pending = InvestigationTarget(name="B", state=TargetState.PENDING)
    static_verified = InvestigationTarget(name="C", state=TargetState.STATIC_VERIFIED)
    state = _state(validated, pending, static_verified)

    Validator().cascade_guardrail_limit(state, "max iterations reached")

    assert validated.state == TargetState.VALIDATED
    assert pending.state == TargetState.INSUFFICIENT_EVIDENCE
    assert static_verified.state == TargetState.INSUFFICIENT_EVIDENCE
