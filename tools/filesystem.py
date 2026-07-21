from __future__ import annotations

from pathlib import Path

SKIP_DIRS = frozenset({".git", "__pycache__", ".venv", "venv", "node_modules", ".raven", ".pytest_cache"})


class PathEscapesRepositoryError(Exception):
    """Raised when a requested path would resolve outside the repository root."""


def _resolve_within(repository_root: Path, relative_path: str) -> Path:
    root = Path(repository_root).resolve()
    target = (root / relative_path).resolve()
    if target != root and root not in target.parents:
        raise PathEscapesRepositoryError(f"{relative_path!r} escapes repository root {root}")
    return target


def list_directory(repository_root: Path, relative_path: str = ".") -> list[str]:
    target = _resolve_within(repository_root, relative_path)
    return sorted(p.name for p in target.iterdir())


def read_file(repository_root: Path, relative_path: str) -> str:
    target = _resolve_within(repository_root, relative_path)
    return target.read_text(encoding="utf-8", errors="ignore")


def read_markdown(repository_root: Path, relative_path: str) -> str:
    if not relative_path.endswith(".md"):
        raise ValueError(f"{relative_path!r} is not a markdown file")
    return read_file(repository_root, relative_path)


def file_exists(repository_root: Path, relative_path: str) -> bool:
    target = _resolve_within(repository_root, relative_path)
    return target.is_file()


def iter_source_files(repository_root: Path, extensions: tuple[str, ...] = (".py",)) -> list[Path]:
    """Deterministic file discovery for the Investigator, skipping noise directories."""
    root = Path(repository_root).resolve()
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in extensions and not any(part in SKIP_DIRS for part in path.parts)
    )
