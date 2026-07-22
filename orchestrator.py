from __future__ import annotations

from pathlib import Path
from typing import Optional

from agents.executor import Executor, RuntimeFailureLimitExceeded, SessionLifetimeExceeded
from agents.investigator import Investigator
from agents.planner import Planner
from agents.validator import Validator
from config.settings import GuardrailSettings, load_guardrail_settings
from models.target import TargetState
from runtime.docker import DockerError
from runtime.gateway_runner import GatewayOutputError
from state.builder import build_initial_state
from state.state import RepositoryState
from validation.guardrails import GuardrailTracker
from validation.termination import InvestigationSignal, evaluate


def run_investigation(repository_path: Path, guardrails: Optional[GuardrailSettings] = None) -> RepositoryState:
    """The full autonomous loop: Planner picks a target, its current state determines which agent
    acts on it next, repeat until every target reaches a terminal state or a guardrail cuts the
    loop short. See architecture.md's Investigation Lifecycle.
    """

    guardrails = guardrails or load_guardrail_settings()
    state = build_initial_state(repository_path)

    planner = Planner()
    investigator = Investigator(repository_path)
    executor = Executor(repository_path, runtime_failure_limit=guardrails.runtime_failure_limit)
    validator = Validator()
    tracker = GuardrailTracker(settings=guardrails)

    try:
        while evaluate(state) == InvestigationSignal.MORE_INVESTIGATION:
            if tracker.max_iterations_reached():
                validator.cascade_guardrail_limit(state, "max iterations reached")
                break

            target = planner.next_task(state)
            if target is None:
                break  # defensive only — evaluate() already guarantees a non-terminal target here

            if target.state in (TargetState.PENDING, TargetState.INVESTIGATING):
                tracker.record_iteration()
                previous_state = target.state
                investigator.investigate(state, target)
                made_progress = target.state != previous_state
                tracker.record_investigation_attempt(target, made_progress)
                if not made_progress and tracker.duplicate_limit_exceeded(target):
                    validator.mark_insufficient_evidence(state, target, "duplicate investigation limit reached")
                continue

            if target.state == TargetState.STATIC_VERIFIED:
                tracker.record_iteration()
                try:
                    executor.run_target(state, target)
                except (DockerError, GatewayOutputError):
                    continue  # Executor already logged and counted this attempt — retry next time
                except RuntimeFailureLimitExceeded:
                    validator.cascade_guardrail_limit(state, "runtime failure limit reached")
                    break
                except SessionLifetimeExceeded:
                    validator.cascade_guardrail_limit(state, "session lifetime exceeded")
                    break
                continue

            if target.state == TargetState.RUNTIME_VERIFIED:
                validator.validate_target(state, target)
                continue
    finally:
        executor.stop(state)

    return state
