from __future__ import annotations

import json
from pathlib import Path

import pytest

from models.observation import Observation
from models.repository import RepositoryMetadata, RepositoryProfile
from models.target import InvestigationTarget, TargetState
from reports.report_generator import ReportGenerator
from state.state import RepositoryState


@pytest.fixture()
def state() -> RepositoryState:
    profile = RepositoryProfile(
        path=Path("/repo"),
        name="fixture-app",
        has_dockerfile=True,
        has_docker_compose=False,
        has_raven_directory=True,
        contract_valid=True,
    )
    validated_target = InvestigationTarget(
        name="Authentication",
        state=TargetState.VALIDATED,
        static_evidence=["app/auth.py"],
        runtime_evidence=["gateway.py --input sample_input.json (status=success)"],
    )
    insufficient_target = InvestigationTarget(name="Database", state=TargetState.INSUFFICIENT_EVIDENCE)

    repo_state = RepositoryState(
        repository_profile=profile,
        repository_metadata=RepositoryMetadata(framework="fastapi"),
        investigation_targets=[validated_target, insufficient_target],
    )
    repo_state.observation_store.add(
        Observation(
            category="Authentication",
            claim="Static evidence for 'Authentication' found in 1 file(s)",
            evidence=("app/auth.py",),
            source="Investigator",
        )
    )
    repo_state.observation_store.add(
        Observation(
            category="Authentication",
            claim="Runtime verification for 'Authentication': gateway.py returned status=success",
            evidence=("gateway.py --input sample_input.json (status=success)",),
            source="Executor",
            runtime_verified=True,
        )
    )
    repo_state.runtime_metadata["tests_passed"] = True
    repo_state.runtime_metadata["test_output"] = "2 passed in 0.10s"
    repo_state.log("Validator: Authentication -> VALIDATED")
    repo_state.log("Validator: Database -> INSUFFICIENT_EVIDENCE (duplicate investigation limit reached)")
    return repo_state


def test_generate_writes_all_five_files(tmp_path: Path, state: RepositoryState):
    ReportGenerator(tmp_path).generate(state)

    for filename in (
        "summary.md",
        "architecture.md",
        "runtime_report.md",
        "repository_summary.json",
        "investigation_log.json",
    ):
        assert (tmp_path / filename).is_file()


def test_summary_reports_signal_and_target_counts(tmp_path: Path, state: RepositoryState):
    ReportGenerator(tmp_path).generate(state)
    content = (tmp_path / "summary.md").read_text(encoding="utf-8")

    assert "1/2 investigation targets validated" in content
    assert "Authentication" in content
    assert "Database" in content


def test_architecture_report_includes_validated_evidence(tmp_path: Path, state: RepositoryState):
    ReportGenerator(tmp_path).generate(state)
    content = (tmp_path / "architecture.md").read_text(encoding="utf-8")

    assert "## Authentication" in content
    assert "app/auth.py" in content


def test_architecture_report_honestly_explains_insufficient_evidence(tmp_path: Path, state: RepositoryState):
    ReportGenerator(tmp_path).generate(state)
    content = (tmp_path / "architecture.md").read_text(encoding="utf-8")

    assert "## Database" in content
    assert "Insufficient evidence" in content
    assert "duplicate investigation limit reached" in content


def test_runtime_report_includes_test_output(tmp_path: Path, state: RepositoryState):
    ReportGenerator(tmp_path).generate(state)
    content = (tmp_path / "runtime_report.md").read_text(encoding="utf-8")

    assert "Test suite passed: True" in content
    assert "2 passed in 0.10s" in content


def test_repository_summary_json_is_well_formed(tmp_path: Path, state: RepositoryState):
    ReportGenerator(tmp_path).generate(state)
    data = json.loads((tmp_path / "repository_summary.json").read_text(encoding="utf-8"))

    assert data["name"] == "fixture-app"
    assert data["investigation_signal"] == "COMPLETE"  # both targets (VALIDATED + INSUFFICIENT_EVIDENCE) are terminal
    assert len(data["targets"]) == 2


def test_investigation_log_json_includes_observations_and_logs(tmp_path: Path, state: RepositoryState):
    ReportGenerator(tmp_path).generate(state)
    data = json.loads((tmp_path / "investigation_log.json").read_text(encoding="utf-8"))

    assert len(data["observations"]) == 2
    assert any("VALIDATED" in line for line in data["execution_logs"])
