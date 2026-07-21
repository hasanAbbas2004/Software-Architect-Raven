from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from runtime.docker import DockerError, _run, build_image


def test_run_returns_exec_result_on_success(monkeypatch):
    class FakeCompleted:
        returncode = 0
        stdout = "ok\n"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeCompleted())

    result = _run(["echo", "ok"], timeout_seconds=5)

    assert result.exit_code == 0
    assert result.stdout == "ok\n"


def test_run_raises_docker_error_on_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="docker", timeout=1)

    monkeypatch.setattr(subprocess, "run", raise_timeout)

    with pytest.raises(DockerError):
        _run(["docker", "build", "."], timeout_seconds=1)


def test_build_image_raises_when_dockerfile_missing(tmp_path: Path):
    with pytest.raises(DockerError):
        build_image(tmp_path, "Dockerfile", "tag", timeout_seconds=5)
