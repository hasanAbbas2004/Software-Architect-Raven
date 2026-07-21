from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from models.repository import RepositoryMetadata, RepositoryProfile, RuntimeConfig
from models.target import InvestigationTarget

RAVEN_DIR = ".raven"
REQUIRED_RAVEN_FILES = (
    "repository.yaml",
    "running_instructions.md",
    "investigation_targets.md",
    "input_schema.json",
    "output_schema.json",
)


class RepositoryAnalyzer:
    """Deterministic repository scan and validation against the RAVEN Repository Specification.

    No LLM reasoning. See architecture.md's Repository Analyzer agent and Toolset.
    """

    def __init__(self, repository_path: Path):
        self.path = Path(repository_path).resolve()

    def validate_repository_contract(self) -> list[str]:
        if not self.path.is_dir():
            return [f"repository path does not exist or is not a directory: {self.path}"]

        missing: list[str] = []

        if not (self.path / "README.md").is_file():
            missing.append("README.md")

        if not (self.path / "tests").is_dir():
            missing.append("tests/")

        if not (self.path / "gateway.py").is_file():
            missing.append("gateway.py")

        if not (self.path / "Dockerfile").is_file() and not (self.path / "docker-compose.yml").is_file():
            missing.append("Dockerfile or docker-compose.yml")

        raven_dir = self.path / RAVEN_DIR
        if not raven_dir.is_dir():
            missing.append(f"{RAVEN_DIR}/")
        else:
            for filename in REQUIRED_RAVEN_FILES:
                if not (raven_dir / filename).is_file():
                    missing.append(f"{RAVEN_DIR}/{filename}")

        return missing

    def build_profile(self) -> RepositoryProfile:
        missing = self.validate_repository_contract()
        return RepositoryProfile(
            path=self.path,
            name=self.path.name,
            has_dockerfile=(self.path / "Dockerfile").is_file(),
            has_docker_compose=(self.path / "docker-compose.yml").is_file(),
            has_raven_directory=(self.path / RAVEN_DIR).is_dir(),
            contract_valid=not missing,
            missing_requirements=missing,
        )

    def parse_repository_yaml(self) -> RepositoryMetadata:
        raven_dir = self.path / RAVEN_DIR
        with (raven_dir / "repository.yaml").open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        runtime_raw = raw.get("runtime") or {}
        health_raw = raw.get("health") or {}
        tests_raw = raw.get("tests") or {}
        network_raw = raw.get("network") or {}

        runtime = RuntimeConfig(
            docker_compose_file=runtime_raw.get("docker"),
            startup_command=runtime_raw.get("startup"),
            timeout_seconds=int(runtime_raw.get("timeout_seconds", 60)),
            session_timeout_seconds=int(runtime_raw.get("session_timeout_seconds", 600)),
            health_endpoint=health_raw.get("endpoint"),
            test_command=tests_raw.get("command"),
            network_required=bool(network_raw.get("required", False)),
        )

        return RepositoryMetadata(framework=raw.get("framework"), runtime=runtime)

    def parse_investigation_targets(self) -> list[InvestigationTarget]:
        raven_dir = self.path / RAVEN_DIR
        text = (raven_dir / "investigation_targets.md").read_text(encoding="utf-8")

        targets: list[InvestigationTarget] = []
        for line in text.splitlines():
            stripped = line.strip().strip("#-* ").strip()
            if not stripped or stripped.startswith("```"):
                continue
            targets.append(InvestigationTarget(name=stripped))
        return targets

    def detect_framework(self, metadata: RepositoryMetadata) -> Optional[str]:
        return metadata.framework
