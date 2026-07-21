from __future__ import annotations

import re
from pathlib import Path


def grep(paths: list[Path], pattern: str) -> dict[Path, list[int]]:
    """Deterministic case-insensitive regex search across a set of files. Returns matching line
    numbers per file that had at least one match."""
    compiled = re.compile(pattern, re.IGNORECASE)
    matches: dict[Path, list[int]] = {}
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lines = [i + 1 for i, line in enumerate(text.splitlines()) if compiled.search(line)]
        if lines:
            matches[path] = lines
    return matches


def search_imports(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    matches = re.findall(r"^\s*(?:from\s+(\S+)\s+import|import\s+(\S+))", text, re.MULTILINE)
    return [a or b for a, b in matches]


def search_classes(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return re.findall(r"^\s*class\s+(\w+)", text, re.MULTILINE)


def search_functions(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return re.findall(r"^\s*(?:async\s+)?def\s+(\w+)", text, re.MULTILINE)
