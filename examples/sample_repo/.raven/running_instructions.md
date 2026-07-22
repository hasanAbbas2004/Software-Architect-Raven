# Running Instructions

This is a minimal FastAPI app: one health endpoint, one real API route, nothing else.

## Startup

```bash
docker build -t sample-repo .
docker run -d -p 8000:8000 --name sample-repo sample-repo
```

## Health Check

`GET /health` returns `{"status": "ok"}` once Uvicorn has finished starting — typically within a few seconds.

## Runtime Interaction

`gateway.py` is executed inside the running container via:

```bash
docker exec sample-repo python gateway.py --input sample_input.json
```

It calls `/health` then `/greet` over loopback HTTP and prints a single JSON line matching `.raven/output_schema.json`.

## Environment Variables

None required.

## Known Limitations

This app deliberately has no authentication or database layer — it exists to demonstrate the full RAVEN investigation loop working end to end with minimal setup, not to be a realistic application. Expect `Authentication` and `Database` to honestly resolve to `INSUFFICIENT_EVIDENCE` — there's genuinely nothing there to find. See `../../Test-repo` and `../../Test-repo2` for fuller applications that exercise every investigation category.
