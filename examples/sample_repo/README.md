# Sample Repo

A minimal RAVEN-compliant demo application, shipped inside RAVEN's own repository so a fresh clone can run a real, end-to-end investigation with zero external setup — no separate repository to go find.

It's deliberately tiny: one health endpoint, one real API route, and nothing else. That's intentional — see `.raven/running_instructions.md` for why `Authentication` and `Database` are expected to resolve to `INSUFFICIENT_EVIDENCE` rather than being padded out with fake functionality just to make every target pass.

For fuller applications exercising every investigation category, see the sibling repositories documented in [repo.md](../../repo.md): `Test-repo` (TaskFlow) and `Test-repo2` (BoardFlow).

## Running

```bash
docker build -t sample-repo .
docker run -d -p 8000:8000 --name sample-repo sample-repo
curl http://localhost:8000/health
```

## RAVEN

```bash
raven report examples/sample_repo
```
