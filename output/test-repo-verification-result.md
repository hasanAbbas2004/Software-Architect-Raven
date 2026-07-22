# TaskFlow (Test-repo) — RAVEN Verification Result

Generated: 2026-07-21T23:37:56.486336+00:00
RAVEN phase: Phase 3 — Runtime Verification

## Repository

- Path: `C:\Users\AA\Documents\GitHub\Test-repo`
- Framework: `fastapi`
- Contract valid: True

## Runtime Configuration

- docker_reference: `Dockerfile`
- build_timeout_seconds: `300`
- call_timeout_seconds: `60`
- session_timeout_seconds: `600`
- health_endpoint: `/health`
- health_port: `8000`
- test_command: `pytest`
- network_required: `False`

## Investigation Targets

| Target | State | Static Evidence | Runtime Evidence |
|---|---|---|---|
| Authentication | RUNTIME_VERIFIED | 10 file(s) | 1 entr(y/ies) |
| Database | RUNTIME_VERIFIED | 11 file(s) | 1 entr(y/ies) |
| API | RUNTIME_VERIFIED | 5 file(s) | 1 entr(y/ies) |
| Caching | RUNTIME_VERIFIED | 5 file(s) | 1 entr(y/ies) |
| Background Jobs | RUNTIME_VERIFIED | 3 file(s) | 1 entr(y/ies) |
| Business Logic | RUNTIME_VERIFIED | 3 file(s) | 1 entr(y/ies) |

## Observations

- **Authentication** (Investigator, runtime_verified=False): Static evidence for 'Authentication' found in 10 file(s)
    - app/config.py
    - app/dependencies.py
    - app/main.py
    - app/models.py
    - app/routers/auth.py
    - app/schemas.py
    - app/security.py
    - gateway.py
    - tests/test_auth.py
    - tests/test_tasks.py
- **Database** (Investigator, runtime_verified=False): Static evidence for 'Database' found in 11 file(s)
    - app/config.py
    - app/database.py
    - app/dependencies.py
    - app/jobs.py
    - app/main.py
    - app/models.py
    - app/routers/auth.py
    - app/routers/tasks.py
    - app/schemas.py
    - app/services/task_service.py
    - tests/conftest.py
- **API** (Investigator, runtime_verified=False): Static evidence for 'API' found in 5 file(s)
    - app/dependencies.py
    - app/main.py
    - app/routers/auth.py
    - app/routers/tasks.py
    - tests/conftest.py
- **Caching** (Investigator, runtime_verified=False): Static evidence for 'Caching' found in 5 file(s)
    - app/cache.py
    - app/config.py
    - app/services/task_service.py
    - tests/conftest.py
    - tests/test_tasks.py
- **Background Jobs** (Investigator, runtime_verified=False): Static evidence for 'Background Jobs' found in 3 file(s)
    - app/config.py
    - app/jobs.py
    - app/main.py
- **Business Logic** (Investigator, runtime_verified=False): Static evidence for 'Business Logic' found in 3 file(s)
    - app/routers/tasks.py
    - app/services/task_service.py
    - tests/test_tasks.py
- **Authentication** (Executor, runtime_verified=True): Runtime verification for 'Authentication': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)
- **Database** (Executor, runtime_verified=True): Runtime verification for 'Database': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)
- **API** (Executor, runtime_verified=True): Runtime verification for 'API': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)
- **Caching** (Executor, runtime_verified=True): Runtime verification for 'Caching': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)
- **Background Jobs** (Executor, runtime_verified=True): Runtime verification for 'Background Jobs': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)
- **Business Logic** (Executor, runtime_verified=True): Runtime verification for 'Business Logic': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)

## Runtime Metadata

- container_name: `raven-test-repo-278746ed`
- tests_passed: `True`
- test_output: `============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
rootdir: /app
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 8 items

tests/test_auth.py ....                                                  [ 50%]
tests/test_tasks.py ....                                                 [100%]

=============================== warnings summary ===============================
../usr/local/lib/python3.11/site-packages/fastapi/testclient.py:1
  /usr/local/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
========================= 8 passed, 1 warning in 1.09s =========================
`

## Execution Log

```
Repository validated: C:\Users\AA\Documents\GitHub\Test-repo
Framework detected: fastapi
Docker detected: True
Investigation targets loaded: 6
Repository state initialized
Investigator: Authentication -> STATIC_VERIFIED (10 file(s))
Investigator: Database -> STATIC_VERIFIED (11 file(s))
Investigator: API -> STATIC_VERIFIED (5 file(s))
Investigator: Caching -> STATIC_VERIFIED (5 file(s))
Investigator: Background Jobs -> STATIC_VERIFIED (3 file(s))
Investigator: Business Logic -> STATIC_VERIFIED (3 file(s))
Executor: container 'raven-test-repo-278746ed' started and healthy
Executor: test suite passed
Executor: Authentication -> RUNTIME_VERIFIED (gateway status=success)
Executor: Database -> RUNTIME_VERIFIED (gateway status=success)
Executor: API -> RUNTIME_VERIFIED (gateway status=success)
Executor: Caching -> RUNTIME_VERIFIED (gateway status=success)
Executor: Background Jobs -> RUNTIME_VERIFIED (gateway status=success)
Executor: Business Logic -> RUNTIME_VERIFIED (gateway status=success)
Executor: container 'raven-test-repo-278746ed' stopped
Executor: image 'raven-test-repo-278746ed' removed
```