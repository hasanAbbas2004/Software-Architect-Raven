from __future__ import annotations

import json
from pathlib import Path

import pytest

import agents.executor as executor_module
from agents.executor import Executor, RuntimeFailureLimitExceeded, SessionLifetimeExceeded
from models.repository import RepositoryMetadata, RepositoryProfile, RuntimeConfig
from models.target import InvestigationTarget, TargetState
from runtime.docker import DockerError, ExecResult
from runtime.gateway_runner import GatewayOutputError
from state.state import RepositoryState

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "output": {"type": "object"},
    },
    "required": ["status", "output"],
}


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    raven_dir = tmp_path / ".raven"
    raven_dir.mkdir()
    (raven_dir / "output_schema.json").write_text(json.dumps(OUTPUT_SCHEMA))
    (tmp_path / "Dockerfile").write_text("FROM python:3.11-slim\n")
    return tmp_path


def _state(
    repo_path: Path,
    *targets: InvestigationTarget,
    network_required: bool = False,
    docker_reference: str = "Dockerfile",
) -> RepositoryState:
    profile = RepositoryProfile(
        path=repo_path,
        name="fixture",
        has_dockerfile=True,
        has_docker_compose=False,
        has_raven_directory=True,
        contract_valid=True,
    )
    metadata = RepositoryMetadata(
        framework="fastapi",
        runtime=RuntimeConfig(
            docker_reference=docker_reference,
            timeout_seconds=5,
            session_timeout_seconds=600,
            health_endpoint="/health",
            health_port=8000,
            test_command="pytest",
            network_required=network_required,
        ),
    )
    return RepositoryState(
        repository_profile=profile, repository_metadata=metadata, investigation_targets=list(targets)
    )


def _ok(*_args, **_kwargs) -> ExecResult:
    return ExecResult(exit_code=0, stdout="", stderr="")


def test_run_target_skips_non_static_verified_targets(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Authentication", state=TargetState.PENDING)
    state = _state(repo, target)
    executor = Executor(repo, runtime_failure_limit=3)

    called = []
    monkeypatch.setattr(executor_module, "build_image", lambda *a, **k: called.append(1))

    executor.run_target(state, target)

    assert target.state == TargetState.PENDING
    assert called == []


def test_ensure_container_running_builds_and_starts_once(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED)
    state = _state(repo, target)
    executor = Executor(repo, runtime_failure_limit=3)

    build_calls, run_calls = [], []
    monkeypatch.setattr(executor_module, "build_image", lambda *a, **k: build_calls.append(1))
    monkeypatch.setattr(executor_module, "run_container", lambda *a, **k: run_calls.append(1))
    monkeypatch.setattr(executor_module, "exec_in_container", _ok)

    executor.ensure_container_running(state)
    executor.ensure_container_running(state)

    assert len(build_calls) == 1
    assert len(run_calls) == 1


def test_run_target_success_transitions_to_runtime_verified(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED)
    state = _state(repo, target)
    executor = Executor(repo, runtime_failure_limit=3)

    monkeypatch.setattr(executor_module, "build_image", lambda *a, **k: None)
    monkeypatch.setattr(executor_module, "run_container", lambda *a, **k: None)
    monkeypatch.setattr(executor_module, "exec_in_container", _ok)
    monkeypatch.setattr(executor_module, "run_gateway", lambda *a, **k: {"status": "success", "output": {}})

    executor.run_target(state, target)

    assert target.state == TargetState.RUNTIME_VERIFIED
    assert len(target.runtime_evidence) == 1

    observations = state.observation_store.by_source("Executor")
    assert len(observations) == 1
    assert observations[0].runtime_verified is True


def test_runtime_failure_limit_is_enforced(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED)
    state = _state(repo, target)
    executor = Executor(repo, runtime_failure_limit=2)

    def always_fail(*_a, **_k):
        raise DockerError("boom")

    monkeypatch.setattr(executor_module, "build_image", always_fail)

    with pytest.raises(DockerError):
        executor.ensure_container_running(state)
    assert executor.runtime_failures == 1

    with pytest.raises(RuntimeFailureLimitExceeded):
        executor.ensure_container_running(state)
    assert executor.runtime_failures == 2


def test_session_lifetime_exceeded_blocks_further_targets(repo: Path, monkeypatch):
    target_a = InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED)
    target_b = InvestigationTarget(name="Database", state=TargetState.STATIC_VERIFIED)
    state = _state(repo, target_a, target_b)
    executor = Executor(repo, runtime_failure_limit=3)

    monkeypatch.setattr(executor_module, "build_image", lambda *a, **k: None)
    monkeypatch.setattr(executor_module, "run_container", lambda *a, **k: None)
    monkeypatch.setattr(executor_module, "exec_in_container", _ok)
    monkeypatch.setattr(executor_module, "run_gateway", lambda *a, **k: {"status": "success", "output": {}})

    executor.run_target(state, target_a)
    executor._session_started_at -= 10_000  # simulate the session having already run out

    with pytest.raises(SessionLifetimeExceeded):
        executor.run_target(state, target_b)


def test_docker_compose_repositories_are_not_yet_supported(repo: Path):
    target = InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED)
    state = _state(repo, target, docker_reference="docker-compose.yml")
    executor = Executor(repo, runtime_failure_limit=3)

    with pytest.raises(NotImplementedError):
        executor.ensure_container_running(state)


def test_stop_removes_both_container_and_image(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED)
    state = _state(repo, target)
    executor = Executor(repo, runtime_failure_limit=3)

    monkeypatch.setattr(executor_module, "build_image", lambda *a, **k: None)
    monkeypatch.setattr(executor_module, "run_container", lambda *a, **k: None)
    monkeypatch.setattr(executor_module, "exec_in_container", _ok)
    monkeypatch.setattr(executor_module, "capture_container_logs", lambda *a, **k: "")

    remove_image_calls = []
    stop_container_calls = []
    monkeypatch.setattr(executor_module, "remove_image", lambda tag, **k: remove_image_calls.append(tag))
    monkeypatch.setattr(executor_module, "stop_container", lambda name, **k: stop_container_calls.append(name))

    executor.ensure_container_running(state)
    executor.stop(state)

    assert len(stop_container_calls) == 1
    assert len(remove_image_calls) == 1
    assert remove_image_calls[0] == stop_container_calls[0]


def test_gateway_output_failing_schema_validation_counts_as_a_failure(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED)
    state = _state(repo, target)
    executor = Executor(repo, runtime_failure_limit=3)

    monkeypatch.setattr(executor_module, "build_image", lambda *a, **k: None)
    monkeypatch.setattr(executor_module, "run_container", lambda *a, **k: None)
    monkeypatch.setattr(executor_module, "exec_in_container", _ok)

    def bad_gateway(*_a, **_k):
        raise GatewayOutputError("schema mismatch")

    monkeypatch.setattr(executor_module, "run_gateway", bad_gateway)

    with pytest.raises(GatewayOutputError):
        executor.run_target(state, target)
    assert executor.runtime_failures == 1
