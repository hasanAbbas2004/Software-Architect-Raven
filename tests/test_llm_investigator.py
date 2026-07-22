from __future__ import annotations

import json
from pathlib import Path

import openai
import pytest

import agents.llm_investigator as llm_investigator_module
from agents.llm_investigator import MAX_TOOL_ROUNDS, LLMInvestigator
from models.repository import RepositoryMetadata, RepositoryProfile
from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState


class _FakeFunction:
    def __init__(self, name: str, arguments: dict):
        self.name = name
        self.arguments = json.dumps(arguments)


class _FakeToolCall:
    def __init__(self, name: str, arguments: dict, call_id: str = "tool_1"):
        self.id = call_id
        self.function = _FakeFunction(name, arguments)


class _FakeMessage:
    def __init__(self, tool_calls=None, content=None, refusal=None):
        self.tool_calls = tool_calls or []
        self.content = content
        self.refusal = refusal


class _FakeChoice:
    def __init__(self, message: _FakeMessage, finish_reason: str = "tool_calls"):
        self.message = message
        self.finish_reason = finish_reason


class _FakeResponse:
    def __init__(self, tool_calls=None, content=None, refusal=None, finish_reason: str = "tool_calls"):
        self.choices = [_FakeChoice(_FakeMessage(tool_calls, content, refusal), finish_reason)]


class _FakeCompletions:
    def __init__(self, responses=None, error: Exception | None = None):
        self._responses = list(responses or [])
        self._error = error
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._responses.pop(0)


class _FakeChat:
    def __init__(self, responses=None, error: Exception | None = None):
        self.completions = _FakeCompletions(responses, error)


class _FakeClient:
    def __init__(self, responses=None, error: Exception | None = None):
        self.chat = _FakeChat(responses, error)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "auth.py").write_text("import jwt\n\ndef login():\n    pass\n")
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
        repository_profile=profile, repository_metadata=RepositoryMetadata(), investigation_targets=list(targets)
    )


def test_investigate_skips_already_resolved_targets(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Authentication", state=TargetState.STATIC_VERIFIED)
    state = _state(repo, target)
    fake_client = _FakeClient([])
    monkeypatch.setattr(llm_investigator_module, "OpenAI", lambda: fake_client)

    LLMInvestigator(repo).investigate(state, target)

    assert fake_client.chat.completions.calls == 0


def test_investigate_reaches_static_verified_with_real_evidence(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Authentication")
    state = _state(repo, target)

    responses = [
        _FakeResponse(tool_calls=[_FakeToolCall("search_repository", {"pattern": "jwt"}, "t1")]),
        _FakeResponse(
            tool_calls=[
                _FakeToolCall("submit_findings", {"claim": "uses jwt", "evidence": ["app/auth.py"]}, "t2")
            ]
        ),
    ]
    monkeypatch.setattr(llm_investigator_module, "OpenAI", lambda: _FakeClient(responses))

    LLMInvestigator(repo).investigate(state, target)

    assert target.state == TargetState.STATIC_VERIFIED
    assert target.static_evidence == ["app/auth.py"]
    assert len(state.observation_store) == 1
    observation = state.observation_store.all()[0]
    assert observation.source == "Investigator"
    assert observation.runtime_verified is False


def test_investigate_stays_open_when_llm_submits_no_evidence(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Caching")
    state = _state(repo, target)

    responses = [_FakeResponse(tool_calls=[_FakeToolCall("submit_findings", {"claim": "nothing found", "evidence": []}, "t1")])]
    monkeypatch.setattr(llm_investigator_module, "OpenAI", lambda: _FakeClient(responses))

    LLMInvestigator(repo).investigate(state, target)

    assert target.state == TargetState.INVESTIGATING
    assert len(state.observation_store) == 0


def test_investigate_rejects_fabricated_evidence_paths(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Authentication")
    state = _state(repo, target)

    responses = [
        _FakeResponse(
            tool_calls=[
                _FakeToolCall("submit_findings", {"claim": "uses auth", "evidence": ["app/does_not_exist.py"]}, "t1")
            ]
        )
    ]
    monkeypatch.setattr(llm_investigator_module, "OpenAI", lambda: _FakeClient(responses))

    LLMInvestigator(repo).investigate(state, target)

    assert target.state == TargetState.INVESTIGATING
    assert target.static_evidence == []
    assert len(state.observation_store) == 0


def test_investigate_stops_after_max_tool_rounds_without_submitting(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Authentication")
    state = _state(repo, target)

    # Every round returns a non-submit tool call — never concludes within the budget.
    responses = [
        _FakeResponse(tool_calls=[_FakeToolCall("list_directory", {"path": "."}, f"t{i}")])
        for i in range(MAX_TOOL_ROUNDS)
    ]
    fake_client = _FakeClient(responses)
    monkeypatch.setattr(llm_investigator_module, "OpenAI", lambda: fake_client)

    LLMInvestigator(repo).investigate(state, target)

    assert target.state == TargetState.INVESTIGATING
    assert fake_client.chat.completions.calls == MAX_TOOL_ROUNDS


def test_investigate_forces_submit_when_model_concludes_in_prose(repo: Path, monkeypatch):
    # Reproduces a real observed failure mode: the model gathers real evidence, then replies
    # with a plain-text conclusion instead of calling submit_findings. The loop must force one
    # more call requiring submit_findings rather than discarding the findings as "no evidence".
    target = InvestigationTarget(name="Authentication")
    state = _state(repo, target)

    responses = [
        _FakeResponse(tool_calls=[_FakeToolCall("search_repository", {"pattern": "jwt"}, "t1")]),
        _FakeResponse(content="I found JWT-based authentication in app/auth.py.", finish_reason="stop"),
        _FakeResponse(
            tool_calls=[
                _FakeToolCall("submit_findings", {"claim": "uses jwt", "evidence": ["app/auth.py"]}, "t2")
            ]
        ),
    ]
    fake_client = _FakeClient(responses)
    monkeypatch.setattr(llm_investigator_module, "OpenAI", lambda: fake_client)

    LLMInvestigator(repo).investigate(state, target)

    assert target.state == TargetState.STATIC_VERIFIED
    assert target.static_evidence == ["app/auth.py"]
    assert fake_client.chat.completions.calls == 3


def test_investigate_gives_up_when_forced_submit_also_yields_no_tool_call(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Authentication")
    state = _state(repo, target)

    responses = [
        _FakeResponse(content="Still not sure what to conclude.", finish_reason="stop"),
        _FakeResponse(content="I really don't know.", finish_reason="stop"),
    ]
    fake_client = _FakeClient(responses)
    monkeypatch.setattr(llm_investigator_module, "OpenAI", lambda: fake_client)

    LLMInvestigator(repo).investigate(state, target)

    assert target.state == TargetState.INVESTIGATING
    assert len(state.observation_store) == 0
    assert fake_client.chat.completions.calls == 2


def test_investigate_handles_api_error_gracefully(repo: Path, monkeypatch):
    target = InvestigationTarget(name="Authentication")
    state = _state(repo, target)

    error = openai.APIConnectionError(message="boom", request=None)
    monkeypatch.setattr(llm_investigator_module, "OpenAI", lambda: _FakeClient(error=error))

    LLMInvestigator(repo).investigate(state, target)

    assert target.state == TargetState.INVESTIGATING
    assert len(state.observation_store) == 0
