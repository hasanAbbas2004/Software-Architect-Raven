from __future__ import annotations

from pathlib import Path

from core.exceptions import RepositoryValidationError
from repository.analyzer import RepositoryAnalyzer
from state.state import RepositoryState


def build_initial_state(repository_path: Path) -> RepositoryState:
    """Repository Analysis → Repository Validation → Repository State Builder (architecture.md's High-Level Architecture)."""

    analyzer = RepositoryAnalyzer(repository_path)

    profile = analyzer.build_profile()
    if not profile.contract_valid:
        raise RepositoryValidationError(profile.missing_requirements)

    metadata = analyzer.parse_repository_yaml()
    targets = analyzer.parse_investigation_targets()

    state = RepositoryState(
        repository_profile=profile,
        repository_metadata=metadata,
        investigation_targets=targets,
    )

    state.log(f"Repository validated: {profile.path}")
    state.log(f"Framework detected: {metadata.framework or 'unknown'}")
    state.log(f"Docker detected: {profile.has_dockerfile or profile.has_docker_compose}")
    state.log(f"Investigation targets loaded: {len(targets)}")
    state.log("Repository state initialized")

    return state
