from __future__ import annotations

import json
from pathlib import Path

import openai

import agents.llm_planner as llm_planner_module
from agents.llm_planner import LLMPlanner
from models.repository import RepositoryMetadata, RepositoryProfile
from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState


class _FakeMessage:
    def __init__(self, content: str, refusal=None):
        self.content = content
        self.refusal = refusal
        self.tool_calls = None


class _FakeChoice:
    def __init__(self, message: _FakeMessage, finish_reason: str = "stop"):
        self.message = message
        self.finish_reason = finish_reason


class _FakeResponse:
    def __init__(self, choices):
        self.choices = choices


class _FakeCompletions:
    def __init__(self, response=None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
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
        repository_profile=profile,
        repository_metadata=RepositoryMetadata(framework="fastapi"),
        investigation_targets=list(targets),
    )


def test_next_task_skips_the_api_call_with_a_single_open_target(monkeypatch):
    target = InvestigationTarget(name="Authentication")
    state = _state(target)
    fake_client = _FakeClient(_FakeResponse([_FakeChoice(_FakeMessage(""))]))
    monkeypatch.setattr(llm_planner_module, "OpenAI", lambda: fake_client)

    result = LLMPlanner().next_task(state)

    assert result is target
    assert fake_client.chat.completions.calls == 0


def test_next_task_uses_the_llms_choice(monkeypatch):
    target_a = InvestigationTarget(name="Authentication")
    target_b = InvestigationTarget(name="Database")
    state = _state(target_a, target_b)

    response = _FakeResponse(
        [_FakeChoice(_FakeMessage(json.dumps({"next_target": "Database", "reasoning": "test"})))]
    )
    monkeypatch.setattr(llm_planner_module, "OpenAI", lambda: _FakeClient(response))

    result = LLMPlanner().next_task(state)

    assert result is target_b


def test_next_task_falls_back_on_unparseable_response(monkeypatch):
    target_a = InvestigationTarget(name="Authentication")
    target_b = InvestigationTarget(name="Database")
    state = _state(target_a, target_b)

    response = _FakeResponse([_FakeChoice(_FakeMessage("not json"))])
    monkeypatch.setattr(llm_planner_module, "OpenAI", lambda: _FakeClient(response))

    result = LLMPlanner().next_task(state)

    assert result is target_a


def test_next_task_falls_back_on_refusal(monkeypatch):
    target_a = InvestigationTarget(name="Authentication")
    target_b = InvestigationTarget(name="Database")
    state = _state(target_a, target_b)

    response = _FakeResponse([_FakeChoice(_FakeMessage(None, refusal="cannot help with that"))])
    monkeypatch.setattr(llm_planner_module, "OpenAI", lambda: _FakeClient(response))

    result = LLMPlanner().next_task(state)

    assert result is target_a


def test_next_task_falls_back_on_api_error(monkeypatch):
    target_a = InvestigationTarget(name="Authentication")
    target_b = InvestigationTarget(name="Database")
    state = _state(target_a, target_b)

    error = openai.APIConnectionError(message="boom", request=None)
    monkeypatch.setattr(llm_planner_module, "OpenAI", lambda: _FakeClient(error=error))

    result = LLMPlanner().next_task(state)

    assert result is target_a


def test_next_task_returns_none_when_all_targets_terminal(monkeypatch):
    state = _state(
        InvestigationTarget(name="A", state=TargetState.VALIDATED),
        InvestigationTarget(name="B", state=TargetState.INSUFFICIENT_EVIDENCE),
    )
    monkeypatch.setattr(llm_planner_module, "OpenAI", lambda: _FakeClient(_FakeResponse([_FakeChoice(_FakeMessage(""))])))

    assert LLMPlanner().next_task(state) is None
