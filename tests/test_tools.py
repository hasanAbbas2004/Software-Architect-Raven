from __future__ import annotations

from pathlib import Path

import pytest

from tools.filesystem import PathEscapesRepositoryError, file_exists, iter_source_files, list_directory, read_file
from tools.search import grep, search_classes, search_functions, search_imports


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "auth.py").write_text(
        "import jwt\n\nclass AuthService:\n    def login(self):\n        pass\n"
    )
    (tmp_path / "README.md").write_text("# demo\n")
    return tmp_path


def test_list_directory(repo: Path):
    assert list_directory(repo) == ["README.md", "app"]


def test_read_file(repo: Path):
    assert "AuthService" in read_file(repo, "app/auth.py")


def test_file_exists(repo: Path):
    assert file_exists(repo, "README.md") is True
    assert file_exists(repo, "missing.txt") is False


def test_path_escape_is_rejected(repo: Path):
    with pytest.raises(PathEscapesRepositoryError):
        read_file(repo, "../outside.txt")


def test_iter_source_files_skips_pycache(repo: Path):
    (repo / "app" / "__pycache__").mkdir()
    (repo / "app" / "__pycache__" / "auth.cpython-311.pyc").write_text("junk")
    (repo / "app" / "__pycache__" / "fake.py").write_text("should be skipped")

    found = iter_source_files(repo)
    assert (repo / "app" / "auth.py") in found
    assert not any("__pycache__" in str(p) for p in found)


def test_grep_finds_matching_lines(repo: Path):
    matches = grep([repo / "app" / "auth.py"], "login")
    assert matches == {repo / "app" / "auth.py": [4]}


def test_search_imports(repo: Path):
    assert search_imports(repo / "app" / "auth.py") == ["jwt"]


def test_search_classes(repo: Path):
    assert search_classes(repo / "app" / "auth.py") == ["AuthService"]


def test_search_functions(repo: Path):
    assert search_functions(repo / "app" / "auth.py") == ["login"]
