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

`raven run` and `raven report` both accept `--llm`, which swaps the deterministic Planner/Investigator/Validator for real OpenAI-backed reasoning (`agents/llm_planner.py`, `agents/llm_investigator.py`, `agents/llm_validator.py`) — same interfaces, real tool use for the Investigator (it actually reads and searches the repository rather than keyword-grepping), real structured judgment for the Planner and Validator. Requires `OPENAI_API_KEY` set in your own environment (the OpenAI SDK resolves it directly — RAVEN never reads or stores it itself):

```bash
export OPENAI_API_KEY=sk-...
python main.py report examples/sample_repo --llm
```

The model defaults to `gpt-4o` and is configurable via `RAVEN_LLM_MODEL` — override it to whatever model you have access to.

Without `--llm`, everything runs on the deterministic stand-ins — no API key needed, no network calls, fully reproducible, which is also what the whole test suite runs against.

You can also drop `OPENAI_API_KEY=sk-...` into a `.env` file at the repo root instead of exporting it — RAVEN loads it automatically at startup (via `python-dotenv`), so you only need to set it once.

## Investigating Your Own Repository

RAVEN only investigates repositories that satisfy the **RAVEN Repository Specification** below — this section covers where a target repository lives, what it needs, and how to add one (by hand, or by handing an AI assistant the conversion prompt at the bottom of this section).

### Where a target repository lives

**Never inside this repository.** RAVEN's Read-Only Investigation principle means the repository being investigated must be fully separate from RAVEN's own source — a sibling directory with its own independent git history, e.g.:

```
GitHub/
├── Software-Architect-Raven/   ← this repo (RAVEN itself)
├── my-project/                 ← a repository you want RAVEN to investigate
└── another-project/
```

Point every CLI command at that sibling path (absolute or relative):

```bash
python main.py analyze ../my-project
python main.py report ../my-project --output output --llm
```

RAVEN reads, searches, builds, and runs that repository — it never writes to it, never commits to it, and never modifies its files. If the repository doesn't already have its own git history, `git init` it separately before handing it to RAVEN; that boundary is what keeps "investigation" from ever accidentally becoming "modification."

### The RAVEN Repository Specification

A repository is only investigated if it has, at minimum:

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

`raven analyze <path>` checks exactly this list and tells you what's missing — run it first against any candidate repository.

What each piece is actually for:

| Path | Constraint |
|---|---|
| `README.md` | A normal project README — nothing RAVEN-specific required. |
| `Dockerfile` / `docker-compose.yml` | Must build and run the whole service standalone, with no manual steps beyond `docker build` + `docker run`. RAVEN drives its own build/run using only this file's *path* — see `repository.yaml` below. |
| `tests/` | The project's **own** real test suite, run once by the Executor via the `tests.command` declared in `repository.yaml`. RAVEN never writes to it. |
| `gateway.py` | The **only** runtime interface between RAVEN and the repository. See constraints below — this is the file most likely to be gotten wrong. |
| `sample_input.json` | One concrete, valid example input (repo root, next to `gateway.py`) satisfying `.raven/input_schema.json`. This is what RAVEN always passes as `gateway.py --input`. |
| `.raven/repository.yaml` | Declares runtime capabilities — framework, which Dockerfile/compose file to build, health check endpoint + port, test command, timeouts, network requirement. See example below. |
| `.raven/running_instructions.md` | Human-written notes: startup command, what the health check confirms, required/optional env vars, known limitations (e.g. non-persistent storage). |
| `.raven/investigation_targets.md` | A plain list of things to investigate (e.g. `Authentication`, `Database`, `API`), one per blank-line-separated entry — the Planner's initial queue. Only list things that genuinely exist in the codebase; don't invent a target that isn't really there. |
| `.raven/input_schema.json` | JSON Schema for the shape of `gateway.py --input`'s file — just the one scripted interaction, not the app's whole API surface. |
| `.raven/output_schema.json` | JSON Schema for the shape of the single JSON line `gateway.py` prints to stdout. |

**`gateway.py` constraints, precisely:**
- Accepts `--input <path-to-json-file>` matching `input_schema.json`.
- Runs **inside** the already-running application container, invoked by RAVEN via `docker exec` — it is never started as its own container and never run as a standalone process outside Docker. It should talk to the app over loopback (`http://localhost:<port>`), never spawn anything itself.
- Prints **exactly one** JSON line to stdout matching `output_schema.json` — typically `{"status": "success" | "failure" | "error", "output": {...}}` — and nothing else.
- Should perform one realistic, scripted interaction with the service (e.g. register → log in → do the thing → read back the result) so a single call exercises several investigation targets' runtime evidence at once.

**`repository.yaml` example:**

```yaml
framework: fastapi        # or flask, django, etc.

runtime:
  docker: Dockerfile               # or docker-compose.yml
  build_timeout_seconds: 300       # docker build — happens before the container exists
  timeout_seconds: 60              # per-call timeout: health check wait, each docker exec
  session_timeout_seconds: 600     # total container lifetime for one investigation

health:
  endpoint: /health
  port: 8000              # what the health check and gateway.py's loopback calls connect to

tests:
  command: pytest

network:
  required: false          # true only if the service genuinely needs outbound network access
```

`runtime.startup` (e.g. `docker build -t x . && docker run ...`) may be included as a human-readable hint, but RAVEN **never** executes it as a shell command — it only reads the Dockerfile/compose file path and drives its own `docker build`/`docker run` with RAVEN's own flags. This is deliberate: letting a target repository dictate its own container flags would let it bypass RAVEN's resource and network guardrails.

### Converting an existing repository (prompt for an AI assistant)

If you have an existing repository that isn't RAVEN-compliant yet, the fastest path is to hand an AI coding assistant (Claude, or similar) the prompt below inside that repository's own session. It only *adds* the compatibility layer above — it never touches your existing application code.

> You are converting this repository into a RAVEN-compliant target repository so an external tool (RAVEN) can investigate it. **Do not modify, remove, or refactor any existing application code, business logic, or tests.** You are only adding a thin compatibility layer on top of what already exists.
>
> First, understand the repository: its language/framework, how it's started, what port (if any) it listens on, what a health/readiness signal looks like (add a minimal `/health` endpoint if none exists), and what command runs its existing test suite.
>
> Then add exactly the following, without changing anything else:
>
> 1. **`README.md`** — only if one doesn't already exist; a minimal description of what the project does and how to run it.
> 2. **`Dockerfile`** (or `docker-compose.yml` only if the app genuinely needs multiple services) — builds and runs the app standalone, listening on a fixed port, no manual steps beyond `docker build` + `docker run`.
> 3. **`tests/`** — reuse the existing test suite if there is one; only add tests if none exist at all.
> 4. **`gateway.py`** (repo root) — the only runtime interface this tool will ever call:
>    - Accepts `--input <path-to-json-file>`.
>    - Assumes it runs **inside** the already-running application container (invoked via `docker exec`) — it must talk to the app over `http://localhost:<port>`, never start the app itself.
>    - Performs one realistic, scripted interaction that exercises as much of the real functionality as reasonably possible in a single call (e.g. register → log in → perform the core action → read back the result).
>    - Prints **exactly one** line of JSON to stdout shaped like `{"status": "success" | "failure" | "error", "output": {...}}`, and nothing else.
> 5. **`sample_input.json`** (repo root) — one concrete, valid example satisfying `.raven/input_schema.json` below.
> 6. **`.raven/`** directory containing:
>    - `repository.yaml` — framework name; `runtime.docker` (path to the Dockerfile/compose file), `build_timeout_seconds` (default 300), `timeout_seconds` (default 60), `session_timeout_seconds` (default 600); `health.endpoint` + `health.port`; `tests.command`; `network.required` (true only if genuinely needed). `runtime.startup` may be included as a human-readable note only — it will never be executed as a shell command by the investigating tool.
>    - `running_instructions.md` — plain-language startup notes, required env vars, known limitations.
>    - `investigation_targets.md` — a plain list, one per blank-line-separated entry, naming things that **actually exist** in this codebase (common categories: Authentication, Authorization, Database, API, Caching, Background Jobs, Rate Limiting, Business Logic) — don't invent a target that isn't really there.
>    - `input_schema.json` — JSON Schema for `gateway.py --input`'s file shape.
>    - `output_schema.json` — JSON Schema for the one JSON line `gateway.py` prints.
>
> Before finishing, verify it yourself: the existing test suite still passes unmodified; `docker build` + `docker run` + a manual `docker exec <container> python gateway.py --input sample_input.json` produces exactly one valid JSON line matching `output_schema.json`; and confirm no required top-level file is missing.

### Verifying a new target repository

```bash
# 1. Structural contract check — no agents, no Docker
python main.py analyze /path/to/target

# 2. Full autonomous loop + reports (deterministic — no API key needed)
python main.py report /path/to/target --output output

# 3. Same, but with real LLM reasoning
python main.py report /path/to/target --output output --llm
```

If step 1 reports missing requirements, fix them before moving on. Two fuller reference repositories built against this exact contract — with real authentication, database layers, caching, background jobs, rate limiting, and role-based authorization — are described in `repo.md` (kept local/untracked, since it's a working note rather than a shipped artifact) for anyone extending this project's test fixtures further.

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

**Deterministic by default, real reasoning on request:** the Planner, Investigator, and Validator each have two implementations behind the same interface — a deterministic stand-in (priority-order target selection, keyword-based evidence search, structural evidence checks; no API key, no network, what the test suite runs against) and a real OpenAI-backed one (`agents/llm_*.py`, opt in with `--llm`; see above). Both were built deliberately in that order: prove the pipeline, guardrails, and Docker integration with the cheap deterministic version first, then swap in real reasoning behind the same interface. The Executor and Repository Analyzer are deterministic by design permanently — they do Docker/filesystem I/O, not reasoning.

## Testing

```bash
pytest
```

The test suite (`tests/`) covers the Repository Analyzer, Planner, Investigator, Executor (against a mocked Docker layer), Validator, guardrails, the orchestration loop, and the Report Generator — including the LLM-backed variants of Planner/Investigator/Validator, tested against a mocked `openai.OpenAI` client. It does not require Docker or an `OPENAI_API_KEY` to run — only manual end-to-end verification against real repositories (with or without `--llm`) needs those.

## Contributing

- Keep every agent's responsibility singular: the Planner decides, the Investigator gathers static evidence, the Executor runs Docker, the Validator accepts/rejects, the Report Generator only reads the Observation Store. Don't merge responsibilities across agents.
- Never fabricate a finding. If there's no evidence, the correct outcome is `INSUFFICIENT_EVIDENCE` with a clear reason — not a best-effort guess.
- New guardrails should be built into the component that owns the resource they bound (e.g. Docker-related limits live on the Executor), not bolted on afterward in the orchestrator.
- To add a new test/target repository, see **Investigating Your Own Repository** above — it covers where it lives, the contract it must satisfy, and a ready-to-use prompt for converting an existing repository into a compliant one.
