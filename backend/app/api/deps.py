"""Dependency injection for Prophet API routes.
SPEC: docs/spec/06_API_SPEC.md
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class _StubOrchestrator:
    """Lightweight stub when SimulationOrchestrator is not yet available.

    Every method raises NotImplementedError so API routes can return 501
    without importing the real orchestrator (which may not be wired yet).
    """

    def __getattr__(self, name: str) -> Any:
        def _not_implemented(*args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError(
                f"SimulationOrchestrator.{name} not yet implemented"
            )
        return _not_implemented


# Singleton orchestrator instance
_orchestrator: Any | None = None


def get_orchestrator() -> Any:
    """Return the SimulationOrchestrator singleton.

    Tries to import the real orchestrator first; falls back to a stub
    that raises NotImplementedError on every call so routes return 501.
    """
    global _orchestrator
    if _orchestrator is None:
        try:
            from app.engine.simulation.orchestrator import SimulationOrchestrator
            _orchestrator = SimulationOrchestrator()
            logger.info("Using real SimulationOrchestrator")
        except Exception:
            _orchestrator = _StubOrchestrator()
            logger.warning(
                "SimulationOrchestrator unavailable — using stub (501 for all ops)"
            )
    return _orchestrator
