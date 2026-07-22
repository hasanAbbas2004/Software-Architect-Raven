# RAVEN

**Repository Analysis, Validation & Execution Network**

RAVEN is an autonomous, evidence-driven multi-agent system that investigates containerized Python repositories — not by summarizing source code, but by planning an investigation, gathering static evidence, verifying runtime behavior in Docker, validating every finding, and only then producing a report.

It is intentionally constrained: RAVEN only investigates repositories that follow the **RAVEN Repository Specification** (see below). That constraint is what makes investigations deterministic, reproducible, and explainable instead of a pile of heuristics.

## Why this exists

Most "AI reads your repo and tells you about it" tools are a single prompt over a pile of source files. RAVEN is built around **bounded autonomy** instead: a Planner decides what to investigate next, an Investigator gathers static evidence, an Executor verifies claims by actually running the repository in an isolated Docker container, and a Validator decides whether each finding is trustworthy enough to accept — with hard guardrails (iteration caps, duplicate-investigation limits, runtime failure limits, session lifetime) ensuring the loop always terminates. Nothing gets reported without evidence; if evidence is missing, RAVEN says so explicitly rather than guessing.

## Installation

Requires Python 3.10+ and Docker.

```bash
git clone <this-repository>
cd Software-Architect-Raven
pip install -r requirements.txt
```

## Quick Start

RAVEN ships with a minimal working example repository at `examples/sample_repo` — no external setup needed.

```bash
python main.py report examples/sample_repo
```

This runs the full investigation loop and writes reports to `output/sample_repo/`. Expect `API` to reach `VALIDATED` and `Authentication`/`Database` to honestly reach `INSUFFICIENT_EVIDENCE` — this example app deliberately has no auth or database layer, and RAVEN doesn't fabricate findings for things that aren't there.

## CLI Commands

Each command is a progressively more complete slice of the pipeline — useful for diagnosing which stage something breaks at, not just for running the whole thing.

| Command | What it does |
|---|---|
| `raven analyze <path>` | Validates the repository against the RAVEN contract, parses `.raven/repository.yaml` and `investigation_targets.md`, builds initial state. No agents, no Docker. |
| `raven investigate <path>` | Adds the Planner + Investigator: static evidence gathering across all investigation targets. Still no Docker. |
| `raven verify <path>` | Adds the Executor: builds and runs the repository in Docker, executes `gateway.py` per target, runs the existing test suite. |
| `raven run <path>` | The full autonomous loop: Planner → Investigator → Executor → Validator, repeated until every target reaches a terminal state (`VALIDATED` or `INSUFFICIENT_EVIDENCE`) or a guardrail cuts it short. |
| `raven report <path> [--output DIR]` | Runs the full loop and generates the final reports (`summary.md`, `architecture.md`, `runtime_report.md`, `repository_summary.json`, `investigation_log.json`) under `<DIR>/<repository_name>/`. Default output directory is `./output`. |

(There's no globally-installed `raven` command yet in this repo — invoke via `python main.py <command> <path>` from the repo root, or `pip install -e .` first to get the `raven` console script from `pyproject.toml`.)

### `--llm` mode

`raven run` and `raven report` both accept `--llm`, which swaps the deterministic Planner/Investigator/Validator for real Claude-backed reasoning (`agents/llm_planner.py`, `agents/llm_investigator.py`, `agents/llm_validator.py`) — same interfaces, real tool use for the Investigator (it actually reads and searches the repository rather than keyword-grepping), real structured judgment for the Planner and Validator. Requires `ANTHROPIC_API_KEY` set in your own environment (the Anthropic SDK resolves it directly — RAVEN never reads or stores it itself):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python main.py report examples/sample_repo --llm
```

Without `--llm`, everything runs on the deterministic stand-ins — no API key needed, no network calls, fully reproducible, which is also what the whole test suite runs against.

## The RAVEN Repository Specification

A repository is only investigated if it has:

```
README.md
Dockerfile (or docker-compose.yml)
tests/
gateway.py
sample_input.json
.raven/
    repository.yaml
    running_instructions.md
    investigation_targets.md
    input_schema.json
    output_schema.json
```

- **`gateway.py`** is the single runtime interface between RAVEN and the repository — a script that accepts `--input <file>`, does one scripted interaction with the running application over loopback HTTP, and prints one JSON line matching `output_schema.json`. RAVEN always invokes it via `docker exec` against the one container it starts for the whole investigation — never as its own container, never via a published host port.
- **`investigation_targets.md`** is a plain list of things to investigate (e.g. `Authentication`, `Database`, `API`) — the Planner's initial queue.
- **`repository.yaml`** declares runtime capabilities: which Dockerfile/compose file to build, the health check endpoint and port, the test command, timeouts, and whether the container needs outbound network access. RAVEN builds and runs the container itself using only the declared *paths* — it never executes anything the repository declares as a shell command, to keep a target repository from being able to override RAVEN's own resource/network limits.

Two fuller example applications built against this contract — with real authentication, database layers, caching, background jobs, rate limiting, and role-based authorization — exist as separate sibling repositories for more thorough testing than the minimal bundled example supports.

## Architecture

```
User
  │
  ▼
Repository Analyzer  (deterministic — validates contract, parses metadata)
  │
  ▼
Planner              (picks the next investigation target that isn't done yet)
  │
  ├──────────────┬───────────────┐
  ▼              ▼               ▼
Investigator   Executor       Validator
(static         (Docker:       (accepts or
 evidence,       health check,  rejects each
 keyword         gateway.py,    target based
 search)         test suite)    on evidence)
  │              │               │
  └──────────────┴───────────────┘
                 │
                 ▼
        Observation Store  (append-only; every claim references evidence)
                 │
                 ▼
        Report Generator  (reads only the Observation Store — never source files)
                 │
                 ▼
        summary.md / architecture.md / runtime_report.md / *.json
```

Each investigation target moves through its own lifecycle independently:

```
PENDING → INVESTIGATING → STATIC_VERIFIED → RUNTIME_VERIFIED → VALIDATED
                                                              ↘ INSUFFICIENT_EVIDENCE
```

`INSUFFICIENT_EVIDENCE` is a legitimate, expected outcome — not a failure state. A target reaches it when evidence genuinely can't be established (nothing found, runtime verification failed repeatedly, a guardrail cut the investigation short), and the final report explains why. The investigation as a whole is `COMPLETE` once every target has reached one terminal state or the other — never once every target is `VALIDATED`, since forcing everything to validate would mean fabricating evidence for things that aren't there.

**Guardrails** (all configurable via environment variables, see `config/settings.py`): a maximum iteration budget for the whole investigation, a per-target duplicate-investigation limit, a runtime failure limit, a Docker build timeout, a per-call timeout, and a total session lifetime for the one container an investigation runs. Any of these being hit cascades remaining open targets to `INSUFFICIENT_EVIDENCE` rather than leaving the loop to hang.

**Deterministic by default, real reasoning on request:** the Planner, Investigator, and Validator each have two implementations behind the same interface — a deterministic stand-in (priority-order target selection, keyword-based evidence search, structural evidence checks; no API key, no network, what the test suite runs against) and a real Claude-backed one (`agents/llm_*.py`, opt in with `--llm`; see above). Both were built deliberately in that order: prove the pipeline, guardrails, and Docker integration with the cheap deterministic version first, then swap in real reasoning behind the same interface. The Executor and Repository Analyzer are deterministic by design permanently — they do Docker/filesystem I/O, not reasoning.

## Testing

```bash
pytest
```

The test suite (`tests/`) covers the Repository Analyzer, Planner, Investigator, Executor (against a mocked Docker layer), Validator, guardrails, the orchestration loop, and the Report Generator — including the LLM-backed variants of Planner/Investigator/Validator, tested against a mocked `anthropic.Anthropic` client. It does not require Docker or an `ANTHROPIC_API_KEY` to run — only manual end-to-end verification against real repositories (with or without `--llm`) needs those.

## Contributing

- Keep every agent's responsibility singular: the Planner decides, the Investigator gathers static evidence, the Executor runs Docker, the Validator accepts/rejects, the Report Generator only reads the Observation Store. Don't merge responsibilities across agents.
- Never fabricate a finding. If there's no evidence, the correct outcome is `INSUFFICIENT_EVIDENCE` with a clear reason — not a best-effort guess.
- New guardrails should be built into the component that owns the resource they bound (e.g. Docker-related limits live on the Executor), not bolted on afterward in the orchestrator.
- To add a new test repository for exercising RAVEN against a fuller application: build a normal small project, satisfy the Repository Specification above, verify it with `raven analyze` → `raven report` before considering it done, and keep it as its own separate git repository (RAVEN's Read-Only Principle means target repositories are never part of RAVEN's own repository).
