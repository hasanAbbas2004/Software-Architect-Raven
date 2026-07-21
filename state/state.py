from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from models.repository import RepositoryMetadata, RepositoryProfile
from models.target import InvestigationTarget
from storage.observation_store import ObservationStore


@dataclass
class RepositoryState:
    """Single source of truth for one investigation. Every agent reads and writes through this object."""

    repository_profile: RepositoryProfile
    repository_metadata: RepositoryMetadata
    investigation_targets: list[InvestigationTarget] = field(default_factory=list)
    observation_store: ObservationStore = field(default_factory=ObservationStore)
    runtime_metadata: dict = field(default_factory=dict)
    validated_findings: list = field(default_factory=list)
    execution_logs: list[str] = field(default_factory=list)

    def get_target(self, name: str) -> Optional[InvestigationTarget]:
        return next((t for t in self.investigation_targets if t.name == name), None)

    def all_targets_terminal(self) -> bool:
        return all(t.is_terminal for t in self.investigation_targets)

    def log(self, message: str) -> None:
        self.execution_logs.append(message)
