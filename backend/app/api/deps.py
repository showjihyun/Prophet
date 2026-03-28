"""Dependency injection for Prophet API routes.
SPEC: docs/spec/06_API_SPEC.md
"""
from __future__ import annotations

import logging

from app.engine.simulation.orchestrator import SimulationOrchestrator

logger = logging.getLogger(__name__)

# Singleton orchestrator instance
_orchestrator: SimulationOrchestrator | None = None


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
