"""Prophet Backend - FastAPI Application.
SPEC: docs/spec/00_ARCHITECTURE.md
"""
from fastapi import FastAPI

app = FastAPI(
    title="Prophet (MCASP)",
    description="Multi-Community Agent Simulation Platform",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
