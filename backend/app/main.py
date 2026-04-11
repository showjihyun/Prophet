"""Prophet Backend - FastAPI Application.
SPEC: docs/spec/00_ARCHITECTURE.md
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, communities, llm_dashboard, network, settings as settings_api, simulations, ws
from app.api.projects import router as projects_router
from app.api.community_templates import router as community_templates_router
from app.api.auth import router as auth_router
from app.config import settings
import sqlalchemy
from sqlalchemy import update
from app.database import engine, Base
from app.models.simulation import Simulation


import app.models  # noqa: F401 — register all models for Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run schema setup and stale-sim cleanup as two short transactions.

    Both phases run **in their own short-lived transaction** with a
    ``lock_timeout`` so a lock wait can never stall server boot forever.

    **Why two phases.** Production observed a transient deadlock pattern
    where a request hitting ``GET /api/v1/projects/`` during startup would
    be rolled back as a deadlock victim, with the rival transaction
    holding ``AccessExclusiveLock`` on ``scenarios`` and wanting the same
    on ``projects``. The exact DDL source is unconfirmed — the suspect is
    ``metadata.create_all`` queued alongside the UPDATE inside one
    ``engine.begin()`` block, which extends the startup transaction's
    lock footprint to both tables. Splitting the phases narrows each
    transaction's scope to exactly one logical operation, closing the
    window regardless of which statement actually acquired the lock.

    **Schema setup is also conditionally skipped.** If the database
    already has an ``alembic_version`` row, we treat Alembic as the
    schema authority and don't run ``metadata.create_all`` at all — that
    removes the DDL path entirely in production and confines it to first
    boot on an empty database.
    """
    # Phase 1: extensions + schema (only on empty database; Alembic owns
    # schema once its version row is present).
    async with engine.begin() as conn:
        await conn.execute(sqlalchemy.text("SET LOCAL lock_timeout = '10s'"))
        alembic_present = await conn.scalar(
            sqlalchemy.text(
                "SELECT to_regclass('public.alembic_version') IS NOT NULL"
            )
        )
        if not alembic_present:
            await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
            await conn.run_sync(Base.metadata.create_all)

    # Phase 2: flip stale ``running``/``paused`` sims to ``failed``.
    #
    # Any simulation whose row says ``running`` but whose in-memory runtime
    # state was wiped by this process restart is effectively dead: the
    # orchestrator only holds the NetworkX graph + per-step runner in RAM,
    # never on disk. Without that runtime state, POST /step, /stop, /network
    # all return 404 and the UI is stuck on a "running" sim that can never
    # be stopped. Flip those rows to ``failed`` so the frontend shows the
    # right state and the user can recover.
    async with engine.begin() as conn:
        await conn.execute(sqlalchemy.text("SET LOCAL lock_timeout = '10s'"))
        await conn.execute(
            update(Simulation)
            .where(Simulation.status.in_(["running", "paused"]))
            .values(status="failed")
        )
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
app.include_router(community_templates_router)
app.include_router(auth_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
