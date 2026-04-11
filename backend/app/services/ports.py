"""Service-layer ports (inbound/outbound abstractions).

SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#3.2

The service layer depends on these Protocols/types, never on concrete
infrastructure (WebSocket, Pydantic request models, SQLAlchemy). This
keeps ``services/`` above ``api/`` in the dependency graph and allows
the service to be re-hosted (CLI, worker, tests) with fake adapters.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Protocol
from uuid import UUID


# ==================================================================== #
# Outbound ports — what the service calls
# ==================================================================== #


class NotificationPort(Protocol):
    """Outbound port for real-time notifications.

    The concrete :class:`app.api.ws.ConnectionManager` satisfies this
    Protocol structurally — no explicit subclassing needed. Test doubles
    can provide their own implementation without touching FastAPI/Starlette.
    """

    async def broadcast(self, simulation_id: str, message: dict) -> None: ...

    async def broadcast_agent_updates(
        self, simulation_id: str, agent_state_map: dict[str, dict],
    ) -> None: ...


# ==================================================================== #
# Inbound contracts — what the service accepts as input
# ==================================================================== #


class CampaignInputLike(Protocol):
    """Duck-typed shape the service reads from a campaign payload.

    ``app.api.schemas.CampaignInput`` satisfies this automatically.
    """

    name: str
    budget: float
    channels: list[str]
    message: str
    target_communities: list[str]
    novelty: float
    utility: float
    controversy: float


class CreateSimulationInput(Protocol):
    """Duck-typed shape the service reads from a create-simulation payload.

    ``app.api.schemas.CreateSimulationRequest`` satisfies this automatically.
    Using a Protocol here means ``services/`` does **not** import from
    ``api/`` — the dependency arrow points the right way.
    """

    name: str
    description: str
    campaign: CampaignInputLike
    communities: list[dict[str, Any]] | None
    max_steps: int
    default_llm_provider: str
    random_seed: int | None
    slm_llm_ratio: float
    slm_model: str
    budget_usd: float
    platform: str


# ==================================================================== #
# Return types — strict discriminated outcomes
# ==================================================================== #


class StopOutcome(str, Enum):
    """Result of :meth:`SimulationService.stop`.

    Replaces the former ``dict`` sentinel return. The API layer can
    ``match`` on this enum rather than comparing magic strings.
    """

    COMPLETED = "completed"
    RESET = "created"  # reset to "created" so it can be restarted


# ==================================================================== #
# Domain exceptions — the service raises these; the API maps to HTTP
# ==================================================================== #


class ServiceError(Exception):
    """Base for service-layer domain errors."""


class SimulationNotFoundError(ServiceError):
    """Raised when a simulation cannot be found in memory or in the DB.

    The API layer maps this to HTTP 404.
    """

    def __init__(self, simulation_id: UUID | str) -> None:
        super().__init__(f"Simulation {simulation_id} not found")
        self.simulation_id = str(simulation_id)


__all__ = [
    "NotificationPort",
    "CampaignInputLike",
    "CreateSimulationInput",
    "StopOutcome",
    "ServiceError",
    "SimulationNotFoundError",
]
