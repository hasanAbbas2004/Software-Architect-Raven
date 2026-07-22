# BoardFlow — RAVEN Full Investigation Result

Generated: 2026-07-22T00:11:19.560088+00:00
RAVEN phase: Phase 4 — Validation Loop (full autonomous run)
**Investigation signal: COMPLETE**

## Repository

- Path: `C:\Users\AA\Documents\GitHub\Test-repo2`
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
| Authentication | VALIDATED | 12 file(s) | 1 entr(y/ies) |
| Authorization | VALIDATED | 5 file(s) | 1 entr(y/ies) |
| Database | VALIDATED | 13 file(s) | 1 entr(y/ies) |
| API | VALIDATED | 7 file(s) | 1 entr(y/ies) |
| Caching | VALIDATED | 5 file(s) | 1 entr(y/ies) |
| Background Jobs | VALIDATED | 4 file(s) | 1 entr(y/ies) |
| Rate Limiting | VALIDATED | 6 file(s) | 1 entr(y/ies) |
| Business Logic | VALIDATED | 9 file(s) | 1 entr(y/ies) |

## Observations

- **Authentication** (Investigator, runtime_verified=False): Static evidence for 'Authentication' found in 12 file(s)
    - app/config.py
    - app/dependencies.py
    - app/main.py
    - app/models.py
    - app/routers/auth.py
    - app/schemas.py
    - app/security.py
    - gateway.py
    - tests/test_auth.py
    - tests/test_projects.py
    - tests/test_rate_limit.py
    - tests/test_tasks.py
- **Authentication** (Executor, runtime_verified=True): Runtime verification for 'Authentication': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)
- **Authorization** (Investigator, runtime_verified=False): Static evidence for 'Authorization' found in 5 file(s)
    - app/dependencies.py
    - app/models.py
    - app/routers/auth.py
    - tests/conftest.py
    - tests/test_auth.py
- **Authorization** (Executor, runtime_verified=True): Runtime verification for 'Authorization': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)
- **Database** (Investigator, runtime_verified=False): Static evidence for 'Database' found in 13 file(s)
    - app/config.py
    - app/database.py
    - app/dependencies.py
    - app/main.py
    - app/models.py
    - app/routers/auth.py
    - app/routers/notifications.py
    - app/routers/projects.py
    - app/routers/tasks.py
    - app/schemas.py
    - app/services/project_service.py
    - app/services/task_service.py
    - tests/conftest.py
- **Database** (Executor, runtime_verified=True): Runtime verification for 'Database': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)
- **API** (Investigator, runtime_verified=False): Static evidence for 'API' found in 7 file(s)
    - app/dependencies.py
    - app/main.py
    - app/routers/auth.py
    - app/routers/notifications.py
    - app/routers/projects.py
    - app/routers/tasks.py
    - tests/conftest.py
- **API** (Executor, runtime_verified=True): Runtime verification for 'API': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)
- **Caching** (Investigator, runtime_verified=False): Static evidence for 'Caching' found in 5 file(s)
    - app/cache.py
    - app/config.py
    - app/services/task_service.py
    - tests/conftest.py
    - tests/test_tasks.py
- **Caching** (Executor, runtime_verified=True): Runtime verification for 'Caching': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)
- **Background Jobs** (Investigator, runtime_verified=False): Static evidence for 'Background Jobs' found in 4 file(s)
    - app/main.py
    - app/notifications.py
    - gateway.py
    - tests/test_tasks.py
- **Background Jobs** (Executor, runtime_verified=True): Runtime verification for 'Background Jobs': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)
- **Rate Limiting** (Investigator, runtime_verified=False): Static evidence for 'Rate Limiting' found in 6 file(s)
    - app/config.py
    - app/dependencies.py
    - app/rate_limit.py
    - app/routers/tasks.py
    - tests/conftest.py
    - tests/test_rate_limit.py
- **Rate Limiting** (Executor, runtime_verified=True): Runtime verification for 'Rate Limiting': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)
- **Business Logic** (Investigator, runtime_verified=False): Static evidence for 'Business Logic' found in 9 file(s)
    - app/config.py
    - app/dependencies.py
    - app/rate_limit.py
    - app/routers/projects.py
    - app/routers/tasks.py
    - app/services/task_service.py
    - tests/conftest.py
    - tests/test_rate_limit.py
    - tests/test_tasks.py
- **Business Logic** (Executor, runtime_verified=True): Runtime verification for 'Business Logic': gateway.py returned status=success
    - gateway.py --input sample_input.json (status=success)

## Runtime Metadata

- container_name: `raven-test-repo2-b096989d`
- tests_passed: `True`
- test_output: `============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
rootdir: /app
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 19 items

tests/test_auth.py ....                                                  [ 21%]
tests/test_projects.py ......                                            [ 52%]
tests/test_rate_limit.py ..                                              [ 63%]
tests/test_tasks.py .......                                              [100%]

=============================== warnings summary ===============================
../usr/local/lib/python3.11/site-packages/fastapi/testclient.py:1
  /usr/local/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 19 passed, 1 warning in 5.06s =========================
`

## Execution Log

```
Repository validated: C:\Users\AA\Documents\GitHub\Test-repo2
Framework detected: fastapi
Docker detected: True
Investigation targets loaded: 8
Repository state initialized
Investigator: Authentication -> STATIC_VERIFIED (12 file(s))
Executor: container 'raven-test-repo2-b096989d' started and healthy
Executor: test suite passed
Executor: Authentication -> RUNTIME_VERIFIED (gateway status=success)
Validator: Authentication -> VALIDATED
Investigator: Authorization -> STATIC_VERIFIED (5 file(s))
Executor: Authorization -> RUNTIME_VERIFIED (gateway status=success)
Validator: Authorization -> VALIDATED
Investigator: Database -> STATIC_VERIFIED (13 file(s))
Executor: Database -> RUNTIME_VERIFIED (gateway status=success)
Validator: Database -> VALIDATED
Investigator: API -> STATIC_VERIFIED (7 file(s))
Executor: API -> RUNTIME_VERIFIED (gateway status=success)
Validator: API -> VALIDATED
Investigator: Caching -> STATIC_VERIFIED (5 file(s))
Executor: Caching -> RUNTIME_VERIFIED (gateway status=success)
Validator: Caching -> VALIDATED
Investigator: Background Jobs -> STATIC_VERIFIED (4 file(s))
Executor: Background Jobs -> RUNTIME_VERIFIED (gateway status=success)
Validator: Background Jobs -> VALIDATED
Investigator: Rate Limiting -> STATIC_VERIFIED (6 file(s))
Executor: Rate Limiting -> RUNTIME_VERIFIED (gateway status=success)
Validator: Rate Limiting -> VALIDATED
Investigator: Business Logic -> STATIC_VERIFIED (9 file(s))
Executor: Business Logic -> RUNTIME_VERIFIED (gateway status=success)
Validator: Business Logic -> VALIDATED
Executor: container 'raven-test-repo2-b096989d' stopped
Executor: image 'raven-test-repo2-b096989d' removed
```