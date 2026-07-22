from __future__ import annotations

from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState


class Validator:
    """Validates each investigation target and owns investigation termination (architecture.md's
    Validator Agent). The only agent allowed to set VALIDATED or INSUFFICIENT_EVIDENCE — Executor
    only ever produces RUNTIME_VERIFIED on success, or raises on failure.

    Deterministic stand-in — see changes.md for the decision to defer real LLM reasoning.
    """

    def validate_target(self, state: RepositoryState, target: InvestigationTarget) -> InvestigationTarget:
        if target.is_terminal or target.state != TargetState.RUNTIME_VERIFIED:
            return target

        if not target.static_evidence or not target.runtime_evidence:
            self.mark_insufficient_evidence(state, target, "missing evidence despite reaching RUNTIME_VERIFIED")
            return target

        if self._has_contradiction(state, target):
            self.mark_insufficient_evidence(state, target, "observation store contradicts target state")
            return target

        target.state = TargetState.VALIDATED
        state.log(f"Validator: {target.name} -> VALIDATED")
        return target

    def mark_insufficient_evidence(self, state: RepositoryState, target: InvestigationTarget, reason: str) -> None:
        if target.is_terminal:
            return
        target.state = TargetState.INSUFFICIENT_EVIDENCE
        state.log(f"Validator: {target.name} -> INSUFFICIENT_EVIDENCE ({reason})")

    def cascade_guardrail_limit(self, state: RepositoryState, reason: str) -> None:
        for target in state.investigation_targets:
            self.mark_insufficient_evidence(state, target, reason)

    def _has_contradiction(self, state: RepositoryState, target: InvestigationTarget) -> bool:
        """Defensive structural check: Investigator/Executor always update the Observation Store
        and target state together, so this can't currently trigger under normal operation — it
        guards against a future agent (e.g. a real LLM-based Investigator) drifting the two apart.
        """

        runtime_observations = [o for o in state.observation_store.by_category(target.name) if o.runtime_verified]
        return not runtime_observations
