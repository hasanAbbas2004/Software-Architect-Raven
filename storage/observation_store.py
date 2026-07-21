from __future__ import annotations

from models.observation import Observation


class ObservationStore:
    """First-class architectural component owned by RepositoryState (see architecture.md's Shared
    State). Append-only — the Investigator and Executor may only add to it, never mutate or remove.
    """

    def __init__(self) -> None:
        self._observations: list[Observation] = []

    def add(self, observation: Observation) -> None:
        self._observations.append(observation)

    def all(self) -> list[Observation]:
        return list(self._observations)

    def by_category(self, category: str) -> list[Observation]:
        return [o for o in self._observations if o.category == category]

    def by_source(self, source: str) -> list[Observation]:
        return [o for o in self._observations if o.source == source]

    def __len__(self) -> int:
        return len(self._observations)
