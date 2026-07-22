from __future__ import annotations

import json
from typing import Optional

import openai
from openai import OpenAI

from config.settings import LLMSettings, load_llm_settings
from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState

TERMINAL_STATES = frozenset({TargetState.VALIDATED, TargetState.INSUFFICIENT_EVIDENCE})

SYSTEM_PROMPT = """You are the Planner agent in RAVEN, an autonomous repository investigation system.

You own the investigation. Your only job is deciding which investigation target to work on next —
you never read repository files yourself, and you never decide HOW a target gets investigated
(that is the Investigator's and Executor's job). Pick the single most valuable target to advance
next, given what has already been investigated.

Prefer resuming a target that is partway through its lifecycle (STATIC_VERIFIED, RUNTIME_VERIFIED)
over starting a fresh one — finishing what is already started reaches a validated answer faster.
Among fresh (PENDING/INVESTIGATING) targets, prefer ones more central to the repository's
architecture (e.g. Authentication and Database usually matter more to get right early than
peripheral concerns) — but this is a judgment call, not a fixed rule.

Respond with a JSON object only.
"""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "next_target": {"type": ["string", "null"]},
        "reasoning": {"type": "string"},
    },
    "required": ["next_target", "reasoning"],
    "additionalProperties": False,
}


class LLMPlanner:
    """LLM-backed Planner — see architecture.md's Planner Agent. Reasons over state only; never
    reads files directly. Same `next_task()` interface as agents.planner.Planner (the deterministic
    stand-in), so orchestrator.py can use either interchangeably.

    Falls back to deterministic first-open-target selection on any API error, refusal, or
    unparseable response — an external LLM outage should degrade the investigation, not crash it.
    """

    def __init__(self, settings: Optional[LLMSettings] = None):
        self.settings = settings or load_llm_settings()
        self.client = OpenAI()

    def next_task(self, state: RepositoryState) -> Optional[InvestigationTarget]:
        open_targets = [t for t in state.investigation_targets if t.state not in TERMINAL_STATES]
        if not open_targets:
            return None
        if len(open_targets) == 1:
            state.log(f"Planner: selected {open_targets[0].name} (only open target, skipped LLM call)")
            return open_targets[0]  # no real choice to make — skip the API call

        target_summary = [
            {
                "name": t.name,
                "state": t.state.value,
                "static_evidence_count": len(t.static_evidence),
                "runtime_evidence_count": len(t.runtime_evidence),
            }
            for t in open_targets
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.settings.model,
                max_completion_tokens=self.settings.max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "planner_decision", "schema": OUTPUT_SCHEMA, "strict": True},
                },
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Repository framework: {state.repository_metadata.framework or 'unknown'}\n"
                            f"Open investigation targets:\n{json.dumps(target_summary, indent=2)}"
                        ),
                    },
                ],
            )
        except openai.APIError as exc:
            state.log(f"Planner: LLM call failed ({exc}); falling back to {open_targets[0].name}")
            return open_targets[0]

        choice = response.choices[0]
        if choice.finish_reason == "content_filter" or choice.message.refusal:
            state.log(f"Planner: LLM declined to plan; falling back to {open_targets[0].name}")
            return open_targets[0]

        text = choice.message.content or ""
        try:
            decision = json.loads(text)
        except json.JSONDecodeError:
            state.log(f"Planner: LLM response was not valid JSON; falling back to {open_targets[0].name}")
            return open_targets[0]

        target = state.get_target(decision.get("next_target") or "")
        if target not in open_targets:
            state.log(
                f"Planner: LLM chose an invalid target ({decision.get('next_target')!r}); "
                f"falling back to {open_targets[0].name}"
            )
            return open_targets[0]

        state.log(f"Planner: selected {target.name} — {decision.get('reasoning', '')}")
        return target
