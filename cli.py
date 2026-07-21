from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="raven", description="RAVEN repository investigation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a repository against the RAVEN specification")
    analyze_parser.add_argument("path", help="Path to the target repository")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return _analyze(args.path)

    parser.print_help()
    return 1
