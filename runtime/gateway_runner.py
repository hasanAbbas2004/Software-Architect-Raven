from __future__ import annotations

import json

import jsonschema

from runtime.docker import DockerError, exec_in_container


class GatewayOutputError(Exception):
    """Raised when gateway.py's stdout isn't valid JSON, or doesn't match output_schema.json."""


def run_gateway(container_name: str, output_schema: dict, timeout_seconds: int) -> dict:
    """execute_gateway() — runs gateway.py inside the running container via docker exec, using
    sample_input.json (the required repo-root file — see changes.md). Validates the result against
    output_schema.json before returning it; the Executor never trusts unvalidated gateway output.
    """

    result = exec_in_container(
        container_name, ["python", "gateway.py", "--input", "sample_input.json"], timeout_seconds
    )
    if result.exit_code != 0:
        raise DockerError(f"gateway.py failed (exit {result.exit_code}): {result.stderr[-2000:]}")

    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError as exc:
        raise GatewayOutputError(f"gateway.py did not print valid JSON: {result.stdout[:500]!r}") from exc

    try:
        jsonschema.validate(instance=payload, schema=output_schema)
    except jsonschema.ValidationError as exc:
        raise GatewayOutputError(f"gateway.py output does not match output_schema.json: {exc.message}") from exc

    return payload
