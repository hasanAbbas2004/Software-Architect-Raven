# Test-repo2 — Runtime Report

Test suite passed: True

## Per-Target Runtime Evidence

- **Authentication**: 1 runtime entr(y/ies)
    - gateway.py --input sample_input.json (status=success)
- **Authorization**: 0 runtime entr(y/ies)
- **Database**: 1 runtime entr(y/ies)
    - gateway.py --input sample_input.json (status=success)
- **API**: 0 runtime entr(y/ies)
- **Caching**: 0 runtime entr(y/ies)
- **Background Jobs**: 0 runtime entr(y/ies)
- **Rate Limiting**: 1 runtime entr(y/ies)
    - gateway.py --input sample_input.json (status=success)
- **Business Logic**: 0 runtime entr(y/ies)

## Test Output

```
============================= test session starts ==============================
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
======================== 19 passed, 1 warning in 3.27s =========================

```
