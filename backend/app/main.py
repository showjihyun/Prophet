"""Prophet Backend - FastAPI Application.
SPEC: docs/spec/00_ARCHITECTURE.md
"""
from fastapi import FastAPI

from app.api import agents, communities, llm_dashboard, network, simulations, ws

app = FastAPI(
    title="Prophet (MCASP)",
    description="Multi-Community Agent Simulation Platform",
    version="0.1.0",
)

# --- Register routers (SPEC: docs/spec/06_API_SPEC.md) ---
app.include_router(simulations.router)
app.include_router(agents.router)
app.include_router(communities.router)
app.include_router(network.router)
app.include_router(llm_dashboard.router)
app.include_router(ws.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
