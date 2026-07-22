from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from state.state import RepositoryState
from validation.termination import evaluate

STATE_MARKERS = {
    "VALIDATED": "[VALIDATED]",
    "INSUFFICIENT_EVIDENCE": "[INSUFFICIENT EVIDENCE]",
}


class ReportGenerator:
    """Generates the final investigation reports (architecture.md's Report Generator).

    Consumes only `state.observation_store` and each target's final state — the things the
    Validator has already vetted. Never reads repository source code directly; if a finding isn't
    in the Observation Store, it doesn't appear in a report.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)

    def generate(self, state: RepositoryState) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        (self.output_dir / "summary.md").write_text(self._render_summary(state), encoding="utf-8")
        (self.output_dir / "architecture.md").write_text(self._render_architecture(state), encoding="utf-8")
        (self.output_dir / "runtime_report.md").write_text(self._render_runtime_report(state), encoding="utf-8")
        (self.output_dir / "repository_summary.json").write_text(
            json.dumps(self._build_repository_summary(state), indent=2), encoding="utf-8"
        )
        (self.output_dir / "investigation_log.json").write_text(
            json.dumps(self._build_investigation_log(state), indent=2), encoding="utf-8"
        )

    def _render_summary(self, state: RepositoryState) -> str:
        signal = evaluate(state)
        validated_count = sum(1 for t in state.investigation_targets if t.state.value == "VALIDATED")
        total = len(state.investigation_targets)

        lines = [
            f"# {state.repository_profile.name} — Investigation Summary",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Framework: {state.repository_metadata.framework or 'unknown'}",
            f"Investigation signal: **{signal.value}**",
            "",
            f"{validated_count}/{total} investigation targets validated.",
            "",
            "## Targets",
            "",
        ]
        for target in state.investigation_targets:
            marker = STATE_MARKERS.get(target.state.value, f"[{target.state.value}]")
            lines.append(f"- {marker} **{target.name}**")
        return "\n".join(lines) + "\n"

    def _render_architecture(self, state: RepositoryState) -> str:
        lines = [f"# {state.repository_profile.name} — Architecture Findings", ""]

        for target in state.investigation_targets:
            lines.append(f"## {target.name}")
            lines.append("")

            if target.state.value == "VALIDATED":
                for observation in state.observation_store.by_category(target.name):
                    lines.append(f"- {observation.claim} ({observation.source})")
                    for item in observation.evidence:
                        lines.append(f"    - `{item}`")
            elif target.state.value == "INSUFFICIENT_EVIDENCE":
                lines.append(f"**Insufficient evidence** — {self._insufficient_reason(state, target)}")
            else:
                lines.append(f"_Investigation did not complete (state: {target.state.value})_")

            lines.append("")

        return "\n".join(lines)

    def _render_runtime_report(self, state: RepositoryState) -> str:
        lines = [
            f"# {state.repository_profile.name} — Runtime Report",
            "",
            f"Test suite passed: {state.runtime_metadata.get('tests_passed', 'not run')}",
            "",
            "## Per-Target Runtime Evidence",
            "",
        ]
        for target in state.investigation_targets:
            lines.append(f"- **{target.name}**: {len(target.runtime_evidence)} runtime entr(y/ies)")
            for item in target.runtime_evidence:
                lines.append(f"    - {item}")

        if "test_output" in state.runtime_metadata:
            lines += ["", "## Test Output", "", "```", state.runtime_metadata["test_output"], "```"]

        return "\n".join(lines) + "\n"

    def _build_repository_summary(self, state: RepositoryState) -> dict:
        return {
            "name": state.repository_profile.name,
            "path": str(state.repository_profile.path),
            "framework": state.repository_metadata.framework,
            "contract_valid": state.repository_profile.contract_valid,
            "investigation_signal": evaluate(state).value,
            "targets": [
                {
                    "name": target.name,
                    "state": target.state.value,
                    "static_evidence_count": len(target.static_evidence),
                    "runtime_evidence_count": len(target.runtime_evidence),
                }
                for target in state.investigation_targets
            ],
        }

    def _build_investigation_log(self, state: RepositoryState) -> dict:
        return {
            "execution_logs": state.execution_logs,
            "observations": [
                {
                    "category": observation.category,
                    "claim": observation.claim,
                    "evidence": list(observation.evidence),
                    "source": observation.source,
                    "runtime_verified": observation.runtime_verified,
                }
                for observation in state.observation_store.all()
            ],
        }

    def _insufficient_reason(self, state: RepositoryState, target) -> str:
        prefix = f"Validator: {target.name} -> INSUFFICIENT_EVIDENCE ("
        for line in reversed(state.execution_logs):
            if line.startswith(prefix) and line.endswith(")"):
                return line[len(prefix):-1]
        return "no evidence-backed claim could be established for this target."
