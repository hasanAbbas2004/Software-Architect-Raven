from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Optional

from models.observation import Observation
from models.repository import RuntimeConfig
from models.target import InvestigationTarget, TargetState
from repository.analyzer import RepositoryAnalyzer
from runtime.docker import DockerError, build_image, exec_in_container, remove_image, run_container, stop_container
from runtime.gateway_runner import GatewayOutputError, run_gateway
from runtime.log_capture import capture_container_logs
from state.state import RepositoryState

MEMORY_LIMIT = "512m"
CPU_LIMIT = "1"


class RuntimeFailureLimitExceeded(Exception):
    """Raised once the Runtime Failure Limit (architecture.md's Guardrails & Termination) is reached."""


class SessionLifetimeExceeded(Exception):
    """Raised once the Session Lifetime guardrail is reached."""


class Executor:
    """Runs the repository inside Docker and produces runtime observations. Never makes decisions —
    only executes instructions (architecture.md's Executor Agent). Exactly one container per
    investigation, started lazily on first need — see Container Lifecycle / Per-Target Runtime
    Verification.
    """

    def __init__(self, repository_root: Path, runtime_failure_limit: int):
        self.repository_root = Path(repository_root).resolve()
        self.runtime_failure_limit = runtime_failure_limit
        self._output_schema = RepositoryAnalyzer(self.repository_root).load_output_schema()

        self._container_name: Optional[str] = None
        self._image_tag: Optional[str] = None
        self._session_started_at: Optional[float] = None
        self._session_timeout_seconds: Optional[int] = None
        self._runtime_failures = 0
        self._tests_run = False

    @property
    def runtime_failures(self) -> int:
        return self._runtime_failures

    def ensure_container_running(self, state: RepositoryState) -> None:
        if self._container_name is not None:
            if self._session_expired():
                raise SessionLifetimeExceeded("session lifetime guardrail reached")
            return

        runtime = state.repository_metadata.runtime
        if runtime.docker_reference and runtime.docker_reference.lower().endswith((".yml", ".yaml")):
            raise NotImplementedError(
                "docker-compose based repositories are not yet supported by the Executor (Phase 3 scope)"
            )

        dockerfile_name = runtime.docker_reference or "Dockerfile"
        name = f"raven-{state.repository_profile.name.lower()}-{uuid.uuid4().hex[:8]}"

        try:
            build_image(self.repository_root, dockerfile_name, name, runtime.build_timeout_seconds)
            run_container(
                image_tag=name,
                container_name=name,
                network_disabled=not runtime.network_required,
                memory_limit=MEMORY_LIMIT,
                cpu_limit=CPU_LIMIT,
                timeout_seconds=runtime.timeout_seconds,
            )
            self._wait_for_health(name, runtime)
        except DockerError as exc:
            self._record_failure(state, str(exc))
            raise

        self._container_name = name
        self._image_tag = name
        self._session_started_at = time.monotonic()
        self._session_timeout_seconds = runtime.session_timeout_seconds
        state.runtime_metadata["container_name"] = name
        state.log(f"Executor: container '{name}' started and healthy")

        if not self._tests_run:
            self._run_tests_once(state, runtime)

    def run_target(self, state: RepositoryState, target: InvestigationTarget) -> InvestigationTarget:
        if target.state != TargetState.STATIC_VERIFIED:
            return target
        if self._session_expired():
            raise SessionLifetimeExceeded("session lifetime guardrail reached")

        self.ensure_container_running(state)
        runtime = state.repository_metadata.runtime

        try:
            payload = run_gateway(self._container_name, self._output_schema, runtime.timeout_seconds)
        except (DockerError, GatewayOutputError) as exc:
            self._record_failure(state, str(exc))
            raise

        evidence_entry = f"gateway.py --input sample_input.json (status={payload.get('status')})"
        target.runtime_evidence.append(evidence_entry)
        target.state = TargetState.RUNTIME_VERIFIED

        observation = Observation(
            category=target.name,
            claim=f"Runtime verification for '{target.name}': gateway.py returned status={payload.get('status')}",
            evidence=(evidence_entry,),
            source="Executor",
            runtime_verified=True,
        )
        state.observation_store.add(observation)
        state.log(f"Executor: {target.name} -> RUNTIME_VERIFIED (gateway status={payload.get('status')})")

        return target

    def stop(self, state: RepositoryState) -> None:
        if self._container_name is None:
            return

        state.runtime_metadata["container_logs"] = capture_container_logs(self._container_name)[-4000:]
        stop_container(self._container_name)
        state.log(f"Executor: container '{self._container_name}' stopped")

        if self._image_tag is not None:
            remove_image(self._image_tag)
            state.log(f"Executor: image '{self._image_tag}' removed")
            self._image_tag = None

        self._container_name = None

    def _wait_for_health(self, container_name: str, runtime: RuntimeConfig) -> None:
        deadline = time.monotonic() + runtime.timeout_seconds
        endpoint = runtime.health_endpoint or "/health"
        check = [
            "python", "-c",
            f"import urllib.request as u; u.urlopen('http://localhost:{runtime.health_port}{endpoint}', timeout=3)",
        ]

        last_error = ""
        while time.monotonic() < deadline:
            result = exec_in_container(container_name, check, timeout_seconds=5)
            if result.exit_code == 0:
                return
            last_error = result.stderr
            time.sleep(1)

        raise DockerError(f"health endpoint did not pass within {runtime.timeout_seconds}s: {last_error}")

    def _run_tests_once(self, state: RepositoryState, runtime: RuntimeConfig) -> None:
        self._tests_run = True
        command = (runtime.test_command or "pytest").split()
        result = exec_in_container(self._container_name, command, timeout_seconds=runtime.timeout_seconds)
        passed = result.exit_code == 0
        state.runtime_metadata["tests_passed"] = passed
        state.runtime_metadata["test_output"] = (result.stdout + result.stderr)[-4000:]
        state.log(f"Executor: test suite {'passed' if passed else 'failed'}")

    def _session_expired(self) -> bool:
        if self._session_started_at is None or self._session_timeout_seconds is None:
            return False
        return (time.monotonic() - self._session_started_at) >= self._session_timeout_seconds

    def _record_failure(self, state: RepositoryState, message: str) -> None:
        self._runtime_failures += 1
        state.log(f"Executor: runtime failure ({self._runtime_failures}/{self.runtime_failure_limit}): {message}")
        if self._runtime_failures >= self.runtime_failure_limit:
            raise RuntimeFailureLimitExceeded(message)
