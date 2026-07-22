from __future__ import annotations

import json
from pathlib import Path

import agents.executor as executor_module
from config.settings import GuardrailSettings
from models.target import TargetState
from orchestrator import run_investigation
from runtime.docker import DockerError, ExecResult
from validation.termination import InvestigationSignal, evaluate

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"status": {"type": "string"}, "output": {"type": "object"}},
    "required": ["status", "output"],
}


def _build_repo(tmp_path: Path, target_names: list[str]) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "README.md").write_text("# fixture\n")
    (tmp_path / "Dockerfile").write_text("FROM python:3.11-slim\n")
    (tmp_path / "gateway.py").write_text("print('stub')\n")
    (tmp_path / "sample_input.json").write_text("{}")

    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "auth.py").write_text("import jwt\ndef login():\n    pass\n")

    raven_dir = tmp_path / ".raven"
    raven_dir.mkdir()
    (raven_dir / "repository.yaml").write_text(
        "framework: fastapi\n"
        "runtime:\n"
        "  docker: Dockerfile\n"
        "  build_timeout_seconds: 5\n"
        "  timeout_seconds: 5\n"
        "  session_timeout_seconds: 600\n"
        "health:\n"
        "  endpoint: /health\n"
        "  port: 8000\n"
        "tests:\n"
        "  command: pytest\n"
        "network:\n"
        "  required: false\n"
    )
    (raven_dir / "running_instructions.md").write_text("Run it.\n")
    (raven_dir / "investigation_targets.md").write_text("\n\n".join(target_names) + "\n")
    (raven_dir / "input_schema.json").write_text(json.dumps({"type": "object"}))
    (raven_dir / "output_schema.json").write_text(json.dumps(OUTPUT_SCHEMA))

    return tmp_path


def _ok(*_args, **_kwargs) -> ExecResult:
    return ExecResult(exit_code=0, stdout="", stderr="")


def test_happy_path_reaches_complete_with_validated_target(tmp_path: Path, monkeypatch):
    repo = _build_repo(tmp_path, ["Authentication"])

    monkeypatch.setattr(executor_module, "build_image", lambda *a, **k: None)
    monkeypatch.setattr(executor_module, "run_container", lambda *a, **k: None)
    monkeypatch.setattr(executor_module, "exec_in_container", _ok)
    monkeypatch.setattr(executor_module, "run_gateway", lambda *a, **k: {"status": "success", "output": {}})
    monkeypatch.setattr(executor_module, "capture_container_logs", lambda *a, **k: "")
    monkeypatch.setattr(executor_module, "stop_container", lambda *a, **k: None)
    monkeypatch.setattr(executor_module, "remove_image", lambda *a, **k: None)

    state = run_investigation(repo, guardrails=GuardrailSettings())

    assert evaluate(state) == InvestigationSignal.COMPLETE
    assert state.get_target("Authentication").state == TargetState.VALIDATED


def test_duplicate_investigation_limit_marks_target_insufficient(tmp_path: Path):
    repo = _build_repo(tmp_path, ["Nonexistent Thing"])
    guardrails = GuardrailSettings(duplicate_investigation_limit=2, max_iterations=20)

    state = run_investigation(repo, guardrails=guardrails)

    assert evaluate(state) == InvestigationSignal.COMPLETE
    assert state.get_target("Nonexistent Thing").state == TargetState.INSUFFICIENT_EVIDENCE


def test_runtime_failure_limit_cascades_to_insufficient_evidence(tmp_path: Path, monkeypatch):
    repo = _build_repo(tmp_path, ["Authentication"])
    guardrails = GuardrailSettings(runtime_failure_limit=2, max_iterations=20)

    def always_fail(*_a, **_k):
        raise DockerError("boom")

    monkeypatch.setattr(executor_module, "build_image", always_fail)

    state = run_investigation(repo, guardrails=guardrails)

    assert evaluate(state) == InvestigationSignal.COMPLETE
    assert state.get_target("Authentication").state == TargetState.INSUFFICIENT_EVIDENCE


def test_max_iterations_cascades_remaining_targets(tmp_path: Path):
    repo = _build_repo(tmp_path, ["Authentication", "Database"])
    guardrails = GuardrailSettings(max_iterations=1)

    state = run_investigation(repo, guardrails=guardrails)

    assert evaluate(state) == InvestigationSignal.COMPLETE
    assert all(t.state == TargetState.INSUFFICIENT_EVIDENCE for t in state.investigation_targets)
