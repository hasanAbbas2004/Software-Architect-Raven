from __future__ import annotations

from pathlib import Path

from models.repository import RepositoryMetadata, RepositoryProfile
from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState
from validation.termination import InvestigationSignal, evaluate


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


def test_more_investigation_while_a_target_is_open():
    state = _state(InvestigationTarget(name="A", state=TargetState.VALIDATED), InvestigationTarget(name="B"))
    assert evaluate(state) == InvestigationSignal.MORE_INVESTIGATION


def test_complete_once_every_target_is_terminal():
    state = _state(
        InvestigationTarget(name="A", state=TargetState.VALIDATED),
        InvestigationTarget(name="B", state=TargetState.INSUFFICIENT_EVIDENCE),
    )
    assert evaluate(state) == InvestigationSignal.COMPLETE


def test_complete_with_no_targets_at_all():
    assert evaluate(_state()) == InvestigationSignal.COMPLETE
