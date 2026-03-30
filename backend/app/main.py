"""Prophet Backend - FastAPI Application.
SPEC: docs/spec/00_ARCHITECTURE.md
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, communities, llm_dashboard, network, settings as settings_api, simulations, ws
from app.api.projects import router as projects_router
from app.config import settings
import sqlalchemy
from app.database import engine, Base


import app.models  # noqa: F401 — register all models for Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup (dev mode). Production uses Alembic migrations."""
    async with engine.begin() as conn:
        await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Prophet (MCASP)",
    description="Multi-Community Agent Simulation Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers (SPEC: docs/spec/06_API_SPEC.md) ---
app.include_router(simulations.router)
app.include_router(agents.router)
app.include_router(communities.router)
app.include_router(network.router)
app.include_router(llm_dashboard.router)
app.include_router(settings_api.router)
app.include_router(ws.router)
app.include_router(projects_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
