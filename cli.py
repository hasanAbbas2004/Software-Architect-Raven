from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from agents.investigator import Investigator
from agents.planner import Planner
from config.settings import load_guardrail_settings
from core.exceptions import RepositoryValidationError
from state.builder import build_initial_state


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


def _investigate(path: str) -> int:
    try:
        state = build_initial_state(Path(path))
    except RepositoryValidationError as exc:
        print("Repository validation failed:")
        for item in exc.missing:
            print(f"  - missing {item}")
        return 1

    planner = Planner()
    investigator = Investigator(Path(path))
    max_iterations = load_guardrail_settings().max_iterations

    for _ in range(max_iterations):
        target = planner.next_task(state)
        if target is None:
            break
        print(f"Planner: investigate {target.name}")
        investigator.investigate(state, target)
    else:
        print(f"Stopped after reaching max iterations ({max_iterations})")

    print()
    print("Investigation targets:")
    for target in state.investigation_targets:
        print(f"  - {target.name:<20} state={target.state.value:<18} evidence={len(target.static_evidence)} file(s)")

    print()
    print(f"Observations recorded: {len(state.observation_store)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="raven", description="RAVEN repository investigation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a repository against the RAVEN specification")
    analyze_parser.add_argument("path", help="Path to the target repository")

    investigate_parser = subparsers.add_parser("investigate", help="Run static investigation (Planner + Investigator)")
    investigate_parser.add_argument("path", help="Path to the target repository")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return _analyze(args.path)
    if args.command == "investigate":
        return _investigate(args.path)

    parser.print_help()
    return 1
