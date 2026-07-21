from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class RuntimeConfig:
    """Parsed from .raven/repository.yaml's `runtime`/`health`/`tests`/`network` sections."""

    docker_compose_file: Optional[str] = None
    startup_command: Optional[str] = None
    timeout_seconds: int = 60
    session_timeout_seconds: int = 600
    health_endpoint: Optional[str] = None
    test_command: Optional[str] = None
    network_required: bool = False


@dataclass
class RepositoryMetadata:
    """Declared repository capabilities — the contents of .raven/repository.yaml."""

    framework: Optional[str] = None
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)


@dataclass
class RepositoryProfile:
    """Deterministic scan result: does this repository satisfy the RAVEN Repository Specification."""

    path: Path
    name: str
    has_dockerfile: bool
    has_docker_compose: bool
    has_raven_directory: bool
    contract_valid: bool
    missing_requirements: list[str] = field(default_factory=list)
