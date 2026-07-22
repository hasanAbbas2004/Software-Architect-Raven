from __future__ import annotations

import json
from typing import Optional

import openai
from openai import OpenAI

from config.settings import LLMSettings, load_llm_settings
from models.target import InvestigationTarget, TargetState
from state.state import RepositoryState

SYSTEM_PROMPT = """You are the Validator agent in RAVEN, an autonomous repository investigation system.

You decide whether one investigation target's evidence is trustworthy enough to accept. A target
must have both static evidence (real files found by the Investigator) and runtime evidence (an
actual verified execution by the Executor), and the two must not contradict each other, to be
VALIDATED. If evidence is missing, weak, or the static and runtime findings disagree, the correct
outcome is INSUFFICIENT_EVIDENCE — that is not a failure, it is the honest answer when the
investigation could not establish something confidently.

Respond with a JSON object only.
"""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["VALIDATED", "INSUFFICIENT_EVIDENCE"]},
        "reason": {"type": "string"},
    },
    "required": ["decision", "reason"],
    "additionalProperties": False,
}


class LLMValidator:
    """LLM-backed Validator — see architecture.md's Validator Agent. Same interface as
    agents.validator.Validator (the deterministic stand-in) — still the only agent allowed to set
    VALIDATED or INSUFFICIENT_EVIDENCE, and orchestrator.py's guardrail cascades call the same
    mark_insufficient_evidence()/cascade_guardrail_limit() methods regardless of which Validator is in use.

    A hard invariant is enforced in code, not just in the prompt: the model can never produce
    VALIDATED for a target that doesn't actually have both static and runtime evidence recorded,
    even if it says so — LLMs can err, and evidence-before-conclusions is not negotiable.
    """

    def __init__(self, settings: Optional[LLMSettings] = None):
        self.settings = settings or load_llm_settings()
        self.client = OpenAI()

    def validate_target(self, state: RepositoryState, target: InvestigationTarget) -> InvestigationTarget:
        if target.is_terminal or target.state != TargetState.RUNTIME_VERIFIED:
            return target

        observations = state.observation_store.by_category(target.name)
        payload = {
            "target": target.name,
            "static_evidence": target.static_evidence,
            "runtime_evidence": target.runtime_evidence,
            "observations": [
                {
                    "claim": o.claim,
                    "evidence": list(o.evidence),
                    "source": o.source,
                    "runtime_verified": o.runtime_verified,
                }
                for o in observations
            ],
        }

        try:
            response = self.client.chat.completions.create(
                model=self.settings.model,
                max_completion_tokens=self.settings.max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "validator_decision", "schema": OUTPUT_SCHEMA, "strict": True},
                },
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, indent=2)},
                ],
            )
        except openai.APIError as exc:
            self.mark_insufficient_evidence(state, target, f"LLM call failed ({exc})")
            return target

        choice = response.choices[0]
        if choice.finish_reason == "content_filter" or choice.message.refusal:
            self.mark_insufficient_evidence(state, target, "LLM declined to validate this target")
            return target

        text = choice.message.content or ""
        try:
            decision = json.loads(text)
        except json.JSONDecodeError:
            self.mark_insufficient_evidence(state, target, "LLM validation response was not valid JSON")
            return target

        has_evidence = bool(target.static_evidence) and bool(target.runtime_evidence)
        if decision.get("decision") == "VALIDATED" and has_evidence:
            target.state = TargetState.VALIDATED
            state.log(f"Validator: {target.name} -> VALIDATED ({decision.get('reason', '')})")
        else:
            reason = decision.get("reason", "LLM judged evidence insufficient")
            if decision.get("decision") == "VALIDATED" and not has_evidence:
                reason = "LLM said VALIDATED but required evidence is missing — overridden"
            self.mark_insufficient_evidence(state, target, reason)

        return target

    def mark_insufficient_evidence(self, state: RepositoryState, target: InvestigationTarget, reason: str) -> None:
        if target.is_terminal:
            return
        target.state = TargetState.INSUFFICIENT_EVIDENCE
        state.log(f"Validator: {target.name} -> INSUFFICIENT_EVIDENCE ({reason})")

    def cascade_guardrail_limit(self, state: RepositoryState, reason: str) -> None:
        for target in state.investigation_targets:
            self.mark_insufficient_evidence(state, target, reason)
