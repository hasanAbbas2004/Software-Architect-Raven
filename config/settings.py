from __future__ import annotations

import os
from dataclasses import dataclass


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value is not None else default


@dataclass(frozen=True)
class GuardrailSettings:
    """Bounded-autonomy defaults from architecture.md's Guardrails & Termination section."""

    max_iterations: int = 20
    duplicate_investigation_limit: int = 2
    runtime_failure_limit: int = 3
    default_build_timeout_seconds: int = 300
    default_call_timeout_seconds: int = 60
    default_session_timeout_seconds: int = 600


def load_guardrail_settings() -> GuardrailSettings:
    return GuardrailSettings(
        max_iterations=_int_env("RAVEN_MAX_ITERATIONS", 20),
        duplicate_investigation_limit=_int_env("RAVEN_DUPLICATE_LIMIT", 2),
        runtime_failure_limit=_int_env("RAVEN_RUNTIME_FAILURE_LIMIT", 3),
        default_build_timeout_seconds=_int_env("RAVEN_BUILD_TIMEOUT_SECONDS", 300),
        default_call_timeout_seconds=_int_env("RAVEN_CALL_TIMEOUT_SECONDS", 60),
        default_session_timeout_seconds=_int_env("RAVEN_SESSION_TIMEOUT_SECONDS", 600),
    )


@dataclass(frozen=True)
class LLMSettings:
    """Model configuration for the LLM-backed Planner/Investigator/Validator (--llm mode).
    Requires OPENAI_API_KEY (or another SDK-recognized credential source) in the environment —
    RAVEN does not read or store the key itself, the OpenAI SDK resolves it directly.
    """

    model: str = "gpt-4o"
    max_tokens: int = 4096


def load_llm_settings() -> LLMSettings:
    return LLMSettings(
        model=os.environ.get("RAVEN_LLM_MODEL", "gpt-4o"),
        max_tokens=_int_env("RAVEN_LLM_MAX_TOKENS", 4096),
    )
