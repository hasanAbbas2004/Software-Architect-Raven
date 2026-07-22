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
    (tmp_path / "app" / "dependencies.py").write_text(
        "def require_owner_or_admin(user):\n    if user.role != 'admin':\n        raise Forbidden()\n"
    )
    (tmp_path / "app" / "rate_limit.py").write_text(
        "def enforce(key):\n    bucket = get_bucket(key)\n    if bucket.exceeds_throttle():\n        raise RateLimitExceededError()\n"
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


def test_investigate_finds_authorization_evidence(repo: Path):
    target = InvestigationTarget(name="Authorization")
    state = _state(repo, target)
    investigator = Investigator(repo)

    investigator.investigate(state, target)

    assert target.state == TargetState.STATIC_VERIFIED
    assert target.static_evidence == ["app/dependencies.py"]


def test_investigate_finds_rate_limiting_evidence(repo: Path):
    target = InvestigationTarget(name="Rate Limiting")
    state = _state(repo, target)
    investigator = Investigator(repo)

    investigator.investigate(state, target)

    assert target.state == TargetState.STATIC_VERIFIED
    assert target.static_evidence == ["app/rate_limit.py"]


def test_investigate_works_with_a_relative_repository_root(repo: Path, monkeypatch):
    # Regression test: Investigator used to store repository_root unresolved, while
    # tools.filesystem.iter_source_files() always resolves — a relative root (as opposed to the
    # absolute paths every earlier manual test happened to use) crashed relative_to() with
    # "not in the subpath", first caught running `raven report` against a relative CLI path.
    monkeypatch.chdir(repo.parent)
    relative_root = Path(repo.name)

    target = InvestigationTarget(name="Authentication")
    state = _state(repo, target)
    investigator = Investigator(relative_root)

    investigator.investigate(state, target)

    assert target.state == TargetState.STATIC_VERIFIED
    assert target.static_evidence == ["app/auth.py"]


def test_investigate_skips_already_resolved_targets(repo: Path):
    target = InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED)
    state = _state(repo, target)
    investigator = Investigator(repo)

    investigator.investigate(state, target)

    assert len(state.observation_store) == 0
