from __future__ import annotations

from pathlib import Path

import pytest

from core.exceptions import RepositoryValidationError
from state.builder import build_initial_state


def test_build_initial_state_for_valid_repository(sample_repo_path: Path):
    state = build_initial_state(sample_repo_path)

    assert state.repository_profile.contract_valid is True
    assert len(state.investigation_targets) == 3
    assert state.observation_store == []
    assert "Repository state initialized" in state.execution_logs


def test_build_initial_state_raises_for_invalid_repository(invalid_repo_path: Path):
    with pytest.raises(RepositoryValidationError) as exc_info:
        build_initial_state(invalid_repo_path)

    assert "gateway.py" in exc_info.value.missing


def test_all_targets_terminal_is_false_for_freshly_built_state(sample_repo_path: Path):
    state = build_initial_state(sample_repo_path)
    assert state.all_targets_terminal() is False


def test_get_target_looks_up_by_name(sample_repo_path: Path):
    state = build_initial_state(sample_repo_path)
    assert state.get_target("Authentication") is not None
    assert state.get_target("Nonexistent") is None
