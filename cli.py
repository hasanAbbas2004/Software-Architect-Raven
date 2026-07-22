from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from agents.executor import Executor, RuntimeFailureLimitExceeded, SessionLifetimeExceeded
from agents.investigator import Investigator
from agents.planner import Planner
from config.settings import load_guardrail_settings
from core.exceptions import RepositoryValidationError
from models.target import TargetState
from orchestrator import run_investigation
from runtime.docker import DockerError
from runtime.gateway_runner import GatewayOutputError
from state.builder import build_initial_state
from state.state import RepositoryState
from validation.termination import evaluate


def _analyze(path: str) -> int:
    try:
        state = build_initial_state(Path(path))
    except RepositoryValidationError as exc:
        print("Repository validation failed:")
        for item in exc.missing:
            print(f"  - missing {item}")
        return 1

    for line in state.execution_logs:
        print(line)
    return 0


def _run_static_investigation(state: RepositoryState, path: str, max_iterations: int) -> None:
    planner = Planner()
    investigator = Investigator(Path(path))

    for _ in range(max_iterations):
        target = planner.next_task(state)
        if target is None:
            break
        print(f"Planner: investigate {target.name}")
        investigator.investigate(state, target)
    else:
        print(f"Stopped after reaching max iterations ({max_iterations})")


def _print_target_summary(state: RepositoryState) -> None:
    print()
    print("Investigation targets:")
    for target in state.investigation_targets:
        print(
            f"  - {target.name:<20} state={target.state.value:<18} "
            f"static_evidence={len(target.static_evidence)} runtime_evidence={len(target.runtime_evidence)}"
        )
    print()
    print(f"Observations recorded: {len(state.observation_store)}")


def _investigate(path: str) -> int:
    try:
        state = build_initial_state(Path(path))
    except RepositoryValidationError as exc:
        print("Repository validation failed:")
        for item in exc.missing:
            print(f"  - missing {item}")
        return 1

    _run_static_investigation(state, path, load_guardrail_settings().max_iterations)
    _print_target_summary(state)
    return 0


def _verify(path: str) -> int:
    try:
        state = build_initial_state(Path(path))
    except RepositoryValidationError as exc:
        print("Repository validation failed:")
        for item in exc.missing:
            print(f"  - missing {item}")
        return 1

    guardrails = load_guardrail_settings()
    _run_static_investigation(state, path, guardrails.max_iterations)

    executor = Executor(Path(path), runtime_failure_limit=guardrails.runtime_failure_limit)
    exit_code = 0
    try:
        for target in state.investigation_targets:
            if target.state != TargetState.STATIC_VERIFIED:
                continue
            print(f"Executor: verify {target.name}")
            executor.run_target(state, target)
    except NotImplementedError as exc:
        print(f"Executor: {exc}")
        exit_code = 1
    except (DockerError, GatewayOutputError) as exc:
        print(f"Executor: runtime failure — {exc}")
        exit_code = 1
    except RuntimeFailureLimitExceeded:
        print(f"Executor: runtime failure limit ({guardrails.runtime_failure_limit}) reached — switching to static-only")
    except SessionLifetimeExceeded:
        print("Executor: session lifetime guardrail reached — stopping runtime verification")
    finally:
        executor.stop(state)

    _print_target_summary(state)
    if "tests_passed" in state.runtime_metadata:
        print(f"Test suite passed: {state.runtime_metadata['tests_passed']}")
    return exit_code


def _run(path: str) -> int:
    try:
        state = run_investigation(Path(path))
    except RepositoryValidationError as exc:
        print("Repository validation failed:")
        for item in exc.missing:
            print(f"  - missing {item}")
        return 1

    for line in state.execution_logs:
        print(line)

    _print_target_summary(state)
    print(f"Investigation signal: {evaluate(state).value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="raven", description="RAVEN repository investigation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a repository against the RAVEN specification")
    analyze_parser.add_argument("path", help="Path to the target repository")

    investigate_parser = subparsers.add_parser("investigate", help="Run static investigation (Planner + Investigator)")
    investigate_parser.add_argument("path", help="Path to the target repository")

    verify_parser = subparsers.add_parser(
        "verify", help="Run static investigation, then runtime verification (Executor + Docker)"
    )
    verify_parser.add_argument("path", help="Path to the target repository")

    run_parser = subparsers.add_parser(
        "run", help="Run the full autonomous investigation loop (Planner + Investigator + Executor + Validator)"
    )
    run_parser.add_argument("path", help="Path to the target repository")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return _analyze(args.path)
    if args.command == "investigate":
        return _investigate(args.path)
    if args.command == "verify":
        return _verify(args.path)
    if args.command == "run":
        return _run(args.path)

    parser.print_help()
    return 1
