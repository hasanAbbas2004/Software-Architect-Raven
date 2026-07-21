from __future__ import annotations

from typing import Optional

from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState

RESOLVED_STATES = frozenset(
    {
        TargetState.STATIC_VERIFIED,
        TargetState.RUNTIME_VERIFIED,
        TargetState.VALIDATED,
        TargetState.INSUFFICIENT_EVIDENCE,
    }
)


class Planner:
    """Owns the investigation. Decides what to investigate next; never reads files directly
    (see architecture.md's Planner Agent).

    Deterministic priority-order stand-in for Phase 2 — see changes.md for the decision to defer
    real LLM reasoning until the pipeline skeleton is proven out. Swappable later without changing
    this class's interface.
    """

    def next_task(self, state: RepositoryState) -> Optional[InvestigationTarget]:
        # Phase 3/4 will need to also re-select STATIC_VERIFIED targets that still need runtime
        # verification — out of scope here since there's no Executor yet (phases.md Phase 2).
        for target in state.investigation_targets:
            if target.state not in RESOLVED_STATES:
                return target
        return None
