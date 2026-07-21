from __future__ import annotations

from runtime.docker import collect_logs


def capture_container_logs(container_name: str, tail: int = 200) -> str:
    """Thin, named wrapper over docker.collect_logs() — kept separate per phases.md's Phase 3
    deliverables so log capture has its own explicit module, distinct from the raw Docker CLI wrapper."""

    return collect_logs(container_name, tail=tail)
