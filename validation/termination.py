from __future__ import annotations

from enum import Enum

from models.target import TargetState
from state.state import RepositoryState

TERMINAL_STATES = frozenset({TargetState.VALIDATED, TargetState.INSUFFICIENT_EVIDENCE})


class InvestigationSignal(str, Enum):
    COMPLETE = "COMPLETE"
    MORE_INVESTIGATION = "MORE_INVESTIGATION"


def evaluate(state: RepositoryState) -> InvestigationSignal:
    """architecture.md's Guardrails & Termination: COMPLETE once every target has reached a
    terminal state (VALIDATED or INSUFFICIENT_EVIDENCE) — not necessarily that every target was
    fully validated, just that each one has a definitive, evidence-backed answer.
    """

    if all(target.state in TERMINAL_STATES for target in state.investigation_targets):
        return InvestigationSignal.COMPLETE
    return InvestigationSignal.MORE_INVESTIGATION
