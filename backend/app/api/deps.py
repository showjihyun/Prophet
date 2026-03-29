"""Dependency injection for Prophet API routes.
SPEC: docs/spec/06_API_SPEC.md
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.engine.simulation.persistence import SimulationPersistence

logger = logging.getLogger(__name__)

# Singleton orchestrator instance
_orchestrator: SimulationOrchestrator | None = None

# Shared persistence instance
_persistence = SimulationPersistence()


def get_orchestrator() -> SimulationOrchestrator:
    """Return the SimulationOrchestrator singleton.

    Imports and instantiates the real orchestrator. If it fails, the error
    propagates — no silent stub fallback.
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SimulationOrchestrator()
        logger.info("SimulationOrchestrator initialized")
    return _orchestrator


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session for request-scoped use."""
    async with async_session() as session:
        yield session


def get_persistence() -> SimulationPersistence:
    """Return the shared persistence instance."""
    return _persistence
