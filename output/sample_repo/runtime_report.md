# sample_repo — Runtime Report

Test suite passed: True

## Per-Target Runtime Evidence

- **Authentication**: 0 runtime entr(y/ies)
- **Database**: 0 runtime entr(y/ies)
- **API**: 1 runtime entr(y/ies)
    - gateway.py --input sample_input.json (status=success)

## Test Output

```
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
rootdir: /app
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 2 items

tests/test_app.py ..                                                     [100%]

=============================== warnings summary ===============================
../usr/local/lib/python3.11/site-packages/fastapi/testclient.py:1
  /usr/local/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
========================= 2 passed, 1 warning in 0.36s =========================

```
