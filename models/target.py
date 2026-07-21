from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TargetState(str, Enum):
    PENDING = "PENDING"
    INVESTIGATING = "INVESTIGATING"
    STATIC_VERIFIED = "STATIC_VERIFIED"
    RUNTIME_VERIFIED = "RUNTIME_VERIFIED"
    VALIDATED = "VALIDATED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


TERMINAL_STATES = frozenset({TargetState.VALIDATED, TargetState.INSUFFICIENT_EVIDENCE})


@dataclass
class InvestigationTarget:
    """One objective from investigation_targets.md, tracked through its own lifecycle (see architecture.md's Shared State)."""

    name: str
    state: TargetState = TargetState.PENDING
    requires_runtime_verification: Optional[bool] = None
    static_evidence: list[str] = field(default_factory=list)
    runtime_evidence: list[str] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES
