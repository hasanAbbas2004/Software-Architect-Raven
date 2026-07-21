from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE_REPO = Path(__file__).resolve().parent.parent / "examples" / "sample_repo"


@pytest.fixture
def sample_repo_path() -> Path:
    return SAMPLE_REPO


@pytest.fixture
def invalid_repo_path(tmp_path: Path) -> Path:
    (tmp_path / "README.md").write_text("# incomplete repo\n")
    return tmp_path
