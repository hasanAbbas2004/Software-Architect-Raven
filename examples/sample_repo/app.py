"""Minimal RAVEN-compliant demo application — deliberately small.

Real enough to be investigated and runtime-verified end to end: a working health endpoint and one
real API route. See ../README.md for what this fixture is meant to demonstrate about evidence-based
investigation outcomes — deliberately not repeated here as literal words, since this file itself
gets scanned for evidence.
"""

from fastapi import FastAPI

app = FastAPI(title="RAVEN Sample App", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/greet")
def greet() -> dict:
    return {"message": "hello from the RAVEN sample repo"}
