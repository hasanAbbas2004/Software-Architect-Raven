# Test-repo — Architecture Findings

## Authentication

- Static evidence for 'Authentication' found in 10 file(s) (Investigator)
    - `app/config.py`
    - `app/dependencies.py`
    - `app/main.py`
    - `app/models.py`
    - `app/routers/auth.py`
    - `app/schemas.py`
    - `app/security.py`
    - `gateway.py`
    - `tests/test_auth.py`
    - `tests/test_tasks.py`
- Runtime verification for 'Authentication': gateway.py returned status=success (Executor)
    - `gateway.py --input sample_input.json (status=success)`

## Database

- Static evidence for 'Database' found in 11 file(s) (Investigator)
    - `app/config.py`
    - `app/database.py`
    - `app/dependencies.py`
    - `app/jobs.py`
    - `app/main.py`
    - `app/models.py`
    - `app/routers/auth.py`
    - `app/routers/tasks.py`
    - `app/schemas.py`
    - `app/services/task_service.py`
    - `tests/conftest.py`
- Runtime verification for 'Database': gateway.py returned status=success (Executor)
    - `gateway.py --input sample_input.json (status=success)`

## API

- Static evidence for 'API' found in 5 file(s) (Investigator)
    - `app/dependencies.py`
    - `app/main.py`
    - `app/routers/auth.py`
    - `app/routers/tasks.py`
    - `tests/conftest.py`
- Runtime verification for 'API': gateway.py returned status=success (Executor)
    - `gateway.py --input sample_input.json (status=success)`

## Caching

- Static evidence for 'Caching' found in 5 file(s) (Investigator)
    - `app/cache.py`
    - `app/config.py`
    - `app/services/task_service.py`
    - `tests/conftest.py`
    - `tests/test_tasks.py`
- Runtime verification for 'Caching': gateway.py returned status=success (Executor)
    - `gateway.py --input sample_input.json (status=success)`

## Background Jobs

- Static evidence for 'Background Jobs' found in 3 file(s) (Investigator)
    - `app/config.py`
    - `app/jobs.py`
    - `app/main.py`
- Runtime verification for 'Background Jobs': gateway.py returned status=success (Executor)
    - `gateway.py --input sample_input.json (status=success)`

## Business Logic

- Static evidence for 'Business Logic' found in 3 file(s) (Investigator)
    - `app/routers/tasks.py`
    - `app/services/task_service.py`
    - `tests/test_tasks.py`
- Runtime verification for 'Business Logic': gateway.py returned status=success (Executor)
    - `gateway.py --input sample_input.json (status=success)`
