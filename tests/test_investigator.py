from __future__ import annotations

from pathlib import Path

import pytest

from agents.investigator import Investigator
from models.repository import RepositoryMetadata, RepositoryProfile
from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "auth.py").write_text(
        "import jwt\n\ndef login(username, password):\n    return create_jwt_token(username)\n"
    )
    return tmp_path


def _state(repo_path: Path, *targets: InvestigationTarget) -> RepositoryState:
    profile = RepositoryProfile(
        path=repo_path,
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


def test_investigate_finds_evidence_and_creates_observation(repo: Path):
    target = InvestigationTarget(name="Authentication")
    state = _state(repo, target)
    investigator = Investigator(repo)

    investigator.investigate(state, target)

    assert target.state == TargetState.STATIC_VERIFIED
    assert target.static_evidence == ["app/auth.py"]
    assert len(state.observation_store) == 1

    observation = state.observation_store.all()[0]
    assert observation.category == "Authentication"
    assert observation.evidence == ("app/auth.py",)
    assert observation.source == "Investigator"


def test_investigate_leaves_target_open_when_no_evidence_found(repo: Path):
    target = InvestigationTarget(name="Caching")
    state = _state(repo, target)
    investigator = Investigator(repo)

    investigator.investigate(state, target)

    assert target.state == TargetState.INVESTIGATING
    assert target.static_evidence == []
    assert len(state.observation_store) == 0


def test_investigate_skips_already_resolved_targets(repo: Path):
    target = InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED)
    state = _state(repo, target)
    investigator = Investigator(repo)

    investigator.investigate(state, target)

    assert len(state.observation_store) == 0
