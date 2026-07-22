from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class DockerError(Exception):
    """Raised when a docker CLI invocation fails or times out."""


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str


def build_image(repository_root: Path, dockerfile_name: str, image_tag: str, timeout_seconds: int) -> None:
    """docker_build() — see architecture.md's Toolset. Only reads the file path; never executes
    anything the repository declares as a command (see changes.md's Executor security decision)."""

    dockerfile_path = Path(repository_root) / dockerfile_name
    if not dockerfile_path.is_file():
        raise DockerError(f"Dockerfile not found: {dockerfile_path}")

    result = _run(["docker", "build", "-t", image_tag, str(repository_root)], timeout_seconds)
    if result.exit_code != 0:
        raise DockerError(f"docker build failed (exit {result.exit_code}): {result.stderr[-2000:]}")


def run_container(
    image_tag: str,
    container_name: str,
    network_disabled: bool,
    memory_limit: str,
    cpu_limit: str,
    timeout_seconds: int,
) -> None:
    """docker_run() — starts the one container for the investigation. No host ports are ever
    published; interaction happens exclusively through exec_in_container()."""

    command = [
        "docker", "run", "-d", "--rm",
        "--name", container_name,
        "--memory", memory_limit,
        "--cpus", cpu_limit,
    ]
    if network_disabled:
        command += ["--network", "none"]
    command.append(image_tag)

    result = _run(command, timeout_seconds)
    if result.exit_code != 0:
        raise DockerError(f"docker run failed (exit {result.exit_code}): {result.stderr[-2000:]}")


def exec_in_container(container_name: str, command: list[str], timeout_seconds: int) -> ExecResult:
    """execute_gateway() / wait_for_health() / run_tests() all go through this — the only way the
    Executor talks to a running container."""

    return _run(["docker", "exec", container_name, *command], timeout_seconds)


def stop_container(container_name: str, timeout_seconds: int = 10) -> None:
    """docker_stop() — stops and cleans up (--rm handles container removal)."""

    _run(["docker", "stop", container_name], timeout_seconds)


def remove_image(image_tag: str, timeout_seconds: int = 30) -> None:
    """Each investigation builds its own uniquely-tagged image (see Executor's Container Lifecycle) —
    without this, every run leaves an orphaned image behind and disk usage grows unbounded."""

    _run(["docker", "rmi", "-f", image_tag], timeout_seconds)


def collect_logs(container_name: str, tail: int = 200, timeout_seconds: int = 10) -> str:
    result = _run(["docker", "logs", "--tail", str(tail), container_name], timeout_seconds)
    return result.stdout + result.stderr


def _run(command: list[str], timeout_seconds: int) -> ExecResult:
    try:
        # Explicit UTF-8: Docker/pip build output can contain bytes outside the default Windows
        # codepage (cp1252), which otherwise raises UnicodeDecodeError deep in subprocess's
        # background reader thread — errors="replace" keeps a failed decode from crashing the run.
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout_seconds
        )
    except subprocess.TimeoutExpired as exc:
        raise DockerError(f"command timed out after {timeout_seconds}s: {' '.join(command)}") from exc

    return ExecResult(exit_code=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)
