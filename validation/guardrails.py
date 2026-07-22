from __future__ import annotations

from dataclasses import dataclass, field

from config.settings import GuardrailSettings
from models.target import InvestigationTarget


@dataclass
class GuardrailTracker:
    """Tracks the bounded-autonomy guardrails that aren't already owned by the Executor — Runtime
    Failure Limit and Session Lifetime live there instead, since they're intrinsically tied to the
    one container it manages (see agents/executor.py). See architecture.md's Guardrails & Termination.

    `iterations` only counts dispatches to the Investigator or Executor — the "real work" stages.
    Validator's bookkeeping pass (stamping VALIDATED/INSUFFICIENT_EVIDENCE) is instantaneous and
    costs no external resources, so it doesn't consume iteration budget.
    """

    settings: GuardrailSettings
    iterations: int = 0
    _no_progress_attempts: dict = field(default_factory=dict)

    def record_iteration(self) -> None:
        self.iterations += 1

    def max_iterations_reached(self) -> bool:
        return self.iterations >= self.settings.max_iterations

    def record_investigation_attempt(self, target: InvestigationTarget, made_progress: bool) -> None:
        if made_progress:
            self._no_progress_attempts.pop(target.name, None)
        else:
            self._no_progress_attempts[target.name] = self._no_progress_attempts.get(target.name, 0) + 1

    def duplicate_limit_exceeded(self, target: InvestigationTarget) -> bool:
        return self._no_progress_attempts.get(target.name, 0) >= self.settings.duplicate_investigation_limit
