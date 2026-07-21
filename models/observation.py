from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    """One evidence-backed finding. Immutable once created — see architecture.md's Observation Model.

    Validation happens here, at construction, so a malformed observation can never exist in the
    first place — the Observation Store doesn't need to re-check what it's handed.
    """

    category: str
    claim: str
    evidence: tuple[str, ...]
    source: str
    runtime_verified: bool = False

    def __post_init__(self) -> None:
        if not self.category.strip():
            raise ValueError("observation category must not be empty")
        if not self.claim.strip():
            raise ValueError("observation claim must not be empty")
        if not self.evidence:
            raise ValueError("observation must reference at least one piece of evidence")
        if not self.source.strip():
            raise ValueError("observation source must not be empty")
