"""Standardized runtime interface between RAVEN and this sample app.

Always executed inside the already-running application container via `docker exec` — never
started as its own container. Talks to the app over loopback HTTP since it runs alongside the
already-running Uvicorn process (see .raven/running_instructions.md).
"""

from __future__ import annotations

import argparse
import json

import requests

BASE_URL = "http://localhost:8000"


def run_smoke_test() -> dict:
    result = {"health_ok": False, "greeting": None}

    health_response = requests.get(f"{BASE_URL}/health", timeout=10)
    result["health_ok"] = health_response.status_code == 200

    greet_response = requests.get(f"{BASE_URL}/greet", timeout=10)
    if greet_response.status_code == 200:
        result["greeting"] = greet_response.json().get("message")

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to a JSON file matching .raven/input_schema.json")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if payload.get("action") != "smoke_test":
        print(json.dumps({"status": "error", "output": {"reason": f"unsupported action: {payload.get('action')!r}"}}))
        return

    output = run_smoke_test()
    ok = output["health_ok"] and output["greeting"] is not None
    print(json.dumps({"status": "success" if ok else "failure", "output": output}))


if __name__ == "__main__":
    main()
