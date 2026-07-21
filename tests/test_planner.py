from __future__ import annotations

from pathlib import Path

from agents.planner import Planner
from models.repository import RepositoryMetadata, RepositoryProfile
from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState


def _state(*targets: InvestigationTarget) -> RepositoryState:
    profile = RepositoryProfile(
        path=Path("."),  # Planner never reads the filesystem, so this is never dereferenced
        name="fixture",
        has_dockerfile=True,
        has_docker_compose=False,
        has_raven_directory=True,
        contract_valid=True,
    )
    return RepositoryState(
        repository_profile=profile,
        repository_metadata=RepositoryMetadata(),
        investigation_targets=list(targets),
    )


def test_next_task_returns_first_unresolved_target():
    state = _state(InvestigationTarget(name="Authentication"), InvestigationTarget(name="Database"))
    planner = Planner()

    target = planner.next_task(state)

    assert target is not None
    assert target.name == "Authentication"


def test_next_task_skips_already_resolved_targets():
    state = _state(
        InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED),
        InvestigationTarget(name="Database"),
    )
    planner = Planner()

    target = planner.next_task(state)

    assert target is not None
    assert target.name == "Database"


def test_next_task_returns_none_when_all_targets_resolved():
    state = _state(
        InvestigationTarget(name="Authentication", state=TargetState.VALIDATED),
        InvestigationTarget(name="Database", state=TargetState.INSUFFICIENT_EVIDENCE),
    )
    planner = Planner()

    assert planner.next_task(state) is None
