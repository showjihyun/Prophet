"""Repository Protocol definitions — abstract data access contracts.

SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#2.1

These Protocols describe the **exact** shape the Service layer depends on.
Every method signature here — including kwarg-only ``session`` — must match
the concrete :class:`SqlSimulationRepository` implementation so that typing
the service against the Protocol is safe at both static-check time and
runtime.
"""
from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class SimulationRepository(Protocol):
    """Data access abstraction for simulation persistence.

    SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#2.1

    Implementations:
      - :class:`SqlSimulationRepository` (wraps SimulationPersistence)
      - ``InMemorySimulationRepository`` (test doubles)
    """

    # ---- Writes -------------------------------------------------------- #

    async def save_creation(
        self,
        sim_id: UUID,
        config: Any,
        agents: list[Any],
        edges: list[tuple[Any, Any, dict]],
        *,
        session: AsyncSession,
    ) -> None: ...

    async def save_step(
        self,
        sim_id: UUID,
        result: Any,
        agents: list[Any] | None = None,
        *,
        session: AsyncSession,
    ) -> None: ...

    async def save_status(
        self,
        sim_id: UUID,
        status: str,
        step: int | None = None,
        *,
        session: AsyncSession,
    ) -> None: ...

    async def persist_llm_calls(
        self,
        sim_id: UUID,
        call_logs: list,
        *,
        session: AsyncSession,
    ) -> None: ...

    async def persist_expert_opinions(
        self,
        sim_id: UUID,
        step: int,
        opinions: list[dict],
        *,
        session: AsyncSession,
    ) -> None: ...

    async def persist_agent_memories(
        self,
        sim_id: UUID,
        memories: list[dict],
        *,
        session: AsyncSession,
    ) -> None: ...

    async def persist_thread_messages(
        self,
        messages: list,
        *,
        session: AsyncSession,
    ) -> None: ...

    async def persist_event(
        self,
        sim_id: UUID,
        event_type: str,
        step: int,
        data: dict,
        *,
        session: AsyncSession,
    ) -> None: ...

    # ---- Reads --------------------------------------------------------- #

    async def find_by_id(
        self, sim_id: UUID, *, session: AsyncSession,
    ) -> dict | None: ...

    async def list_all(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        session: AsyncSession,
    ) -> list[dict]: ...

    async def count(
        self, status: str | None = None, *, session: AsyncSession,
    ) -> int: ...

    async def load_steps(
        self, sim_id: UUID, *, session: AsyncSession,
    ) -> list[dict]: ...

    async def restore_state(
        self, sim_id: UUID, *, session: AsyncSession,
    ) -> dict | None: ...

    async def row_exists(
        self, sim_id: UUID, *, session: AsyncSession,
    ) -> bool: ...

    # ---- Misc ---------------------------------------------------------- #

    @property
    def failed_queue(self) -> list[dict]: ...


class ProjectRepository(Protocol):
    """Data access abstraction for project/scenario CRUD.

    SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#2.2
    """

    async def create(self, name: str) -> dict: ...
    async def find_by_id(self, project_id: UUID) -> dict | None: ...
    async def list_all(self) -> list[dict]: ...
    async def delete(self, project_id: UUID) -> None: ...
    async def create_scenario(self, project_id: UUID, data: dict) -> dict: ...
    async def list_scenarios(self, project_id: UUID) -> list[dict]: ...
    async def delete_scenario(
        self, project_id: UUID, scenario_id: UUID,
    ) -> None: ...


__all__ = ["SimulationRepository", "ProjectRepository"]
