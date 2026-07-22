from __future__ import annotations

from typing import Optional

from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState

TERMINAL_STATES = frozenset({TargetState.VALIDATED, TargetState.INSUFFICIENT_EVIDENCE})


class Planner:
    """Owns the investigation. Decides which target to work on next; never reads files directly
    (see architecture.md's Planner Agent).

    Deterministic priority-order stand-in — see changes.md for the decision to defer real LLM
    reasoning until the pipeline skeleton is proven out. Swappable later without changing this
    class's interface.

    Returns the first target that hasn't reached a terminal state yet, regardless of which stage
    it's at (PENDING/INVESTIGATING need the Investigator, STATIC_VERIFIED needs the Executor,
    RUNTIME_VERIFIED needs the Validator). The orchestrator routes to the right agent based on the
    target's own state — the Planner's job is only picking *which* target, not which agent handles it.
    """

    def next_task(self, state: RepositoryState) -> Optional[InvestigationTarget]:
        for target in state.investigation_targets:
            if target.state not in TERMINAL_STATES:
                return target
        return None
