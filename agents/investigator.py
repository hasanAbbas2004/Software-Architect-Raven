from __future__ import annotations

from pathlib import Path

from models.observation import Observation
from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState
from tools.filesystem import iter_source_files
from tools.search import grep

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "authentication": ("auth", "jwt", "password", "login", "token"),
    "database": ("database", "sqlalchemy", "session", "sqlite", "query", "model"),
    "api": ("router", "route", "endpoint", "fastapi", "apirouter"),
    "caching": ("cache", "ttl", "lru"),
    "background jobs": ("background", "sweep", "asyncio", "scheduler", "interval", "job"),
    "business logic": ("service", "business", "rule", "limit", "policy"),
}

ALREADY_INVESTIGATED_STATES = frozenset(
    {TargetState.STATIC_VERIFIED, TargetState.RUNTIME_VERIFIED, TargetState.VALIDATED, TargetState.INSUFFICIENT_EVIDENCE}
)


class Investigator:
    """Gathers static evidence for one investigation target: reads files, searches the repository,
    categorizes findings, produces observations (see architecture.md's Investigator Agent).

    Deterministic keyword-search stand-in for Phase 2 — see changes.md for the decision to defer
    real LLM reasoning. No runtime execution; that's the Executor's job (Phase 3).
    """

    def __init__(self, repository_root: Path):
        self.repository_root = Path(repository_root)

    def investigate(self, state: RepositoryState, target: InvestigationTarget) -> InvestigationTarget:
        if target.is_terminal or target.state in ALREADY_INVESTIGATED_STATES:
            return target

        target.state = TargetState.INVESTIGATING

        keywords = CATEGORY_KEYWORDS.get(target.name.strip().lower(), (target.name.lower(),))
        pattern = "|".join(keywords)
        source_files = iter_source_files(self.repository_root)
        matches = grep(source_files, pattern)

        if not matches:
            # No fabricated evidence — the target stays INVESTIGATING (see architecture.md's
            # Evidence Before Conclusions principle). A later phase's Validator/guardrails decide
            # whether that becomes INSUFFICIENT_EVIDENCE.
            state.log(f"Investigator: {target.name} -> no static evidence found")
            return target

        evidence = sorted(path.relative_to(self.repository_root).as_posix() for path in matches)
        for path in evidence:
            if path not in target.static_evidence:
                target.static_evidence.append(path)

        target.state = TargetState.STATIC_VERIFIED

        observation = Observation(
            category=target.name,
            claim=f"Static evidence for '{target.name}' found in {len(evidence)} file(s)",
            evidence=tuple(evidence),
            source="Investigator",
            runtime_verified=False,
        )
        state.observation_store.add(observation)
        state.log(f"Investigator: {target.name} -> STATIC_VERIFIED ({len(evidence)} file(s))")

        return target
