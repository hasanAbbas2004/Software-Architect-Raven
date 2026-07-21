from __future__ import annotations

from pathlib import Path

from repository.analyzer import RepositoryAnalyzer


def test_valid_repository_has_no_missing_requirements(sample_repo_path: Path):
    analyzer = RepositoryAnalyzer(sample_repo_path)
    assert analyzer.validate_repository_contract() == []


def test_invalid_repository_reports_all_missing_requirements(invalid_repo_path: Path):
    analyzer = RepositoryAnalyzer(invalid_repo_path)
    missing = analyzer.validate_repository_contract()

    assert "tests/" in missing
    assert "gateway.py" in missing
    assert "Dockerfile or docker-compose.yml" in missing
    assert ".raven/" in missing
    assert "README.md" not in missing


def test_build_profile_marks_valid_repository_as_contract_valid(sample_repo_path: Path):
    profile = RepositoryAnalyzer(sample_repo_path).build_profile()

    assert profile.contract_valid is True
    assert profile.has_dockerfile is True
    assert profile.has_raven_directory is True
    assert profile.missing_requirements == []


def test_parse_repository_yaml_reads_framework_and_runtime(sample_repo_path: Path):
    metadata = RepositoryAnalyzer(sample_repo_path).parse_repository_yaml()

    assert metadata.framework == "fastapi"
    assert metadata.runtime.timeout_seconds == 60
    assert metadata.runtime.session_timeout_seconds == 600
    assert metadata.runtime.health_endpoint == "/health"
    assert metadata.runtime.network_required is False


def test_parse_investigation_targets_reads_target_names(sample_repo_path: Path):
    targets = RepositoryAnalyzer(sample_repo_path).parse_investigation_targets()
    names = [t.name for t in targets]

    assert names == ["Authentication", "Database", "API"]
    assert all(t.state.value == "PENDING" for t in targets)
