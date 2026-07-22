from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import openai
from openai import OpenAI

from config.settings import LLMSettings, load_llm_settings
from models.observation import Observation
from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState
from tools.filesystem import PathEscapesRepositoryError, file_exists, iter_source_files, list_directory, read_file
from tools.search import grep, search_classes, search_functions, search_imports

MAX_TOOL_ROUNDS = 6
MAX_FILE_CHARS = 20_000

ALREADY_INVESTIGATED_STATES = frozenset(
    {TargetState.STATIC_VERIFIED, TargetState.RUNTIME_VERIFIED, TargetState.VALIDATED, TargetState.INSUFFICIENT_EVIDENCE}
)

SYSTEM_PROMPT = """You are the Investigator agent in RAVEN, an autonomous repository investigation system.

You gather static evidence for exactly one investigation target by reading and searching the
repository using the tools available to you. Every claim you make must be backed by at least one
real file path from this repository — never invent evidence.

When you have gathered enough evidence (or have determined there genuinely is none), call
`submit_findings` exactly once with your conclusion. If you find no real evidence after a
reasonable search, call submit_findings with an empty evidence list and say so honestly in the
claim — do not fabricate a finding just to have something to report.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List the contents of a directory within the repository (relative path from repository root).",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative directory path, e.g. 'app' or '.'"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file's contents within the repository (relative path from repository root). Large files are truncated.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative file path, e.g. 'app/auth.py'"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_repository",
            "description": "Regex search (case-insensitive) across every Python source file in the repository. Returns matching file paths and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {"pattern": {"type": "string", "description": "Regex pattern to search for"}},
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_symbols",
            "description": "Extract imports, class names, and function names from one file, to understand its structure without reading it in full.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative file path"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_findings",
            "description": "Submit your final conclusion for this investigation target. Call this exactly once, when done.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim": {
                        "type": "string",
                        "description": "One or two sentence evidence-backed claim, or an honest statement that no evidence was found",
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Relative file paths that back the claim. Empty list if no evidence was found.",
                    },
                },
                "required": ["claim", "evidence"],
            },
        },
    },
]


class LLMInvestigator:
    """LLM-backed Investigator — see architecture.md's Investigator Agent. Reads files, searches
    the repository, and produces one evidence-backed observation per target using real tool calls,
    bounded by MAX_TOOL_ROUNDS. Same `investigate()` interface as agents.investigator.Investigator
    (the deterministic keyword-search stand-in), so orchestrator.py can use either interchangeably.
    """

    def __init__(self, repository_root: Path, settings: Optional[LLMSettings] = None):
        # Resolved to match tools.filesystem.iter_source_files()'s own resolution — see the
        # deterministic Investigator's identical comment for the bug this avoids.
        self.repository_root = Path(repository_root).resolve()
        self.settings = settings or load_llm_settings()
        self.client = OpenAI()

    def investigate(self, state: RepositoryState, target: InvestigationTarget) -> InvestigationTarget:
        if target.is_terminal or target.state in ALREADY_INVESTIGATED_STATES:
            return target

        target.state = TargetState.INVESTIGATING

        try:
            claim, evidence = self._run_tool_loop(target)
        except openai.APIError as exc:
            state.log(f"Investigator: {target.name} -> LLM call failed ({exc}); no static evidence found")
            return target

        if not evidence:
            state.log(f"Investigator: {target.name} -> no static evidence found")
            return target

        # Never trust the model's claimed paths on their own — verify each one is real and inside
        # the repository before accepting it as evidence.
        verified_evidence = sorted({e for e in evidence if self._is_valid_evidence_path(e)})
        if not verified_evidence:
            state.log(f"Investigator: {target.name} -> LLM cited no verifiable evidence")
            return target

        for path in verified_evidence:
            if path not in target.static_evidence:
                target.static_evidence.append(path)
        target.state = TargetState.STATIC_VERIFIED

        observation = Observation(
            category=target.name,
            claim=claim,
            evidence=tuple(verified_evidence),
            source="Investigator",
            runtime_verified=False,
        )
        state.observation_store.add(observation)
        state.log(f"Investigator: {target.name} -> STATIC_VERIFIED ({len(verified_evidence)} file(s), LLM-reasoned)")
        return target

    def _is_valid_evidence_path(self, path: str) -> bool:
        try:
            return file_exists(self.repository_root, path)
        except PathEscapesRepositoryError:
            return False

    def _run_tool_loop(self, target: InvestigationTarget) -> tuple[str, list]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Investigation target: {target.name}\n\n"
                    "Gather evidence for this target in this repository."
                ),
            },
        ]

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model=self.settings.model,
                max_completion_tokens=self.settings.max_tokens,
                tools=TOOLS,
                messages=messages,
            )

            choice = response.choices[0]
            message = choice.message

            if choice.finish_reason == "content_filter" or message.refusal:
                return "LLM declined to investigate this target.", []

            tool_calls = message.tool_calls or []
            submit_call = next((tc for tc in tool_calls if tc.function.name == "submit_findings"), None)
            if submit_call is not None:
                args = json.loads(submit_call.function.arguments)
                return args.get("claim", ""), args.get("evidence", [])

            if not tool_calls:
                # The model concluded in plain text instead of calling submit_findings — this
                # happens often enough in practice that discarding the findings here would throw
                # away real evidence it already gathered. Force one final call that must go
                # through submit_findings rather than treating this as "no evidence found".
                return self._force_submit(messages, message.content)

            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in tool_calls
                    ],
                }
            )

            for tc in tool_calls:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                result = self._execute_tool(tc.function.name, args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        return "Investigation did not conclude within the tool-call budget.", []

    def _force_submit(self, messages: list, last_reply: Optional[str]) -> tuple[str, list]:
        messages.append({"role": "assistant", "content": last_reply})
        messages.append(
            {
                "role": "user",
                "content": "Call submit_findings now with your conclusion and the evidence paths you found.",
            }
        )
        response = self.client.chat.completions.create(
            model=self.settings.model,
            max_completion_tokens=self.settings.max_tokens,
            tools=TOOLS,
            tool_choice={"type": "function", "function": {"name": "submit_findings"}},
            messages=messages,
        )
        tool_calls = response.choices[0].message.tool_calls or []
        if not tool_calls:
            return "Investigation did not conclude within the tool-call budget.", []
        args = json.loads(tool_calls[0].function.arguments)
        return args.get("claim", ""), args.get("evidence", [])

    def _execute_tool(self, name: str, tool_input: dict) -> str:
        try:
            if name == "list_directory":
                result = list_directory(self.repository_root, tool_input.get("path", "."))
                return json.dumps(result)
            if name == "read_file":
                text = read_file(self.repository_root, tool_input["path"])
                return text[:MAX_FILE_CHARS]
            if name == "search_repository":
                matches = grep(iter_source_files(self.repository_root), tool_input["pattern"])
                result = {path.relative_to(self.repository_root).as_posix(): lines for path, lines in matches.items()}
                return json.dumps(result)
            if name == "search_symbols":
                path = self.repository_root / tool_input["path"]
                result = {
                    "imports": search_imports(path),
                    "classes": search_classes(path),
                    "functions": search_functions(path),
                }
                return json.dumps(result)
            return f"error: unknown tool: {name}"
        except (PathEscapesRepositoryError, OSError, KeyError) as exc:
            return f"error: {exc}"
