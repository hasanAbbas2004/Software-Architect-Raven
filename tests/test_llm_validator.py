from __future__ import annotations

import json
from pathlib import Path

import openai

import agents.llm_validator as llm_validator_module
from agents.llm_validator import LLMValidator
from models.observation import Observation
from models.repository import RepositoryMetadata, RepositoryProfile
from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState


class _FakeMessage:
    def __init__(self, content: str, refusal=None):
        self.content = content
        self.refusal = refusal


class _FakeChoice:
    def __init__(self, message: _FakeMessage, finish_reason: str = "stop"):
        self.message = message
        self.finish_reason = finish_reason


class _FakeResponse:
    def __init__(self, content=None, refusal=None, finish_reason: str = "stop"):
        self.choices = [_FakeChoice(_FakeMessage(content, refusal), finish_reason)]


class _FakeCompletions:
    def __init__(self, response=None, error: Exception | None = None):
        self._response = response
        self._error = error

    def create(self, **kwargs):
        if self._error is not None:
            raise self._error
        return self._response


class _FakeChat:
    def __init__(self, response=None, error: Exception | None = None):
        self.completions = _FakeCompletions(response, error)


class _FakeClient:
    def __init__(self, response=None, error: Exception | None = None):
        self.chat = _FakeChat(response, error)


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


def _runtime_verified_target(name: str = "Authentication") -> InvestigationTarget:
    return InvestigationTarget(
        name=name,
        state=TargetState.RUNTIME_VERIFIED,
        static_evidence=["app/auth.py"],
        runtime_evidence=["gateway.py --input sample_input.json (status=success)"],
    )


def test_validate_target_ignores_targets_not_runtime_verified(monkeypatch):
    target = InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED)
    state = _state(target)
    monkeypatch.setattr(llm_validator_module, "OpenAI", lambda: _FakeClient(_FakeResponse("")))

    LLMValidator().validate_target(state, target)

    assert target.state == TargetState.STATIC_VERIFIED


def test_validate_target_becomes_validated_on_llm_approval(monkeypatch):
    target = _runtime_verified_target()
    state = _state(target)
    state.observation_store.add(
        Observation(category="Authentication", claim="ok", evidence=("app/auth.py",), source="Investigator")
    )
    state.observation_store.add(
        Observation(
            category="Authentication", claim="runtime ok", evidence=("gateway.py",),
            source="Executor", runtime_verified=True,
        )
    )

    response = _FakeResponse(json.dumps({"decision": "VALIDATED", "reason": "solid evidence"}))
    monkeypatch.setattr(llm_validator_module, "OpenAI", lambda: _FakeClient(response))

    LLMValidator().validate_target(state, target)

    assert target.state == TargetState.VALIDATED


def test_validate_target_marks_insufficient_on_llm_rejection(monkeypatch):
    target = _runtime_verified_target()
    state = _state(target)

    response = _FakeResponse(json.dumps({"decision": "INSUFFICIENT_EVIDENCE", "reason": "weak"}))
    monkeypatch.setattr(llm_validator_module, "OpenAI", lambda: _FakeClient(response))

    LLMValidator().validate_target(state, target)

    assert target.state == TargetState.INSUFFICIENT_EVIDENCE


def test_validate_target_overrides_llm_when_evidence_is_actually_missing(monkeypatch):
    # Target has RUNTIME_VERIFIED state but (unrealistically) no evidence lists populated —
    # the hard invariant must reject VALIDATED regardless of what the model says.
    target = InvestigationTarget(name="Authentication", state=TargetState.RUNTIME_VERIFIED)
    state = _state(target)

    response = _FakeResponse(json.dumps({"decision": "VALIDATED", "reason": "looks fine"}))
    monkeypatch.setattr(llm_validator_module, "OpenAI", lambda: _FakeClient(response))

    LLMValidator().validate_target(state, target)

    assert target.state == TargetState.INSUFFICIENT_EVIDENCE


def test_validate_target_falls_back_on_unparseable_response(monkeypatch):
    target = _runtime_verified_target()
    state = _state(target)

    response = _FakeResponse("not json")
    monkeypatch.setattr(llm_validator_module, "OpenAI", lambda: _FakeClient(response))

    LLMValidator().validate_target(state, target)

    assert target.state == TargetState.INSUFFICIENT_EVIDENCE


def test_validate_target_falls_back_on_api_error(monkeypatch):
    target = _runtime_verified_target()
    state = _state(target)

    error = openai.APIConnectionError(message="boom", request=None)
    monkeypatch.setattr(llm_validator_module, "OpenAI", lambda: _FakeClient(error=error))

    LLMValidator().validate_target(state, target)

    assert target.state == TargetState.INSUFFICIENT_EVIDENCE


def test_mark_insufficient_evidence_does_not_override_terminal_state(monkeypatch):
    target = InvestigationTarget(name="Authentication", state=TargetState.VALIDATED)
    state = _state(target)
    monkeypatch.setattr(llm_validator_module, "OpenAI", lambda: _FakeClient(_FakeResponse("")))

    LLMValidator().mark_insufficient_evidence(state, target, "some reason")

    assert target.state == TargetState.VALIDATED


def test_cascade_guardrail_limit_marks_all_non_terminal_targets(monkeypatch):
    validated = InvestigationTarget(name="A", state=TargetState.VALIDATED)
    pending = InvestigationTarget(name="B", state=TargetState.PENDING)
    state = _state(validated, pending)
    monkeypatch.setattr(llm_validator_module, "OpenAI", lambda: _FakeClient(_FakeResponse("")))

    LLMValidator().cascade_guardrail_limit(state, "max iterations reached")

    assert validated.state == TargetState.VALIDATED
    assert pending.state == TargetState.INSUFFICIENT_EVIDENCE
