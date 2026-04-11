"""SQL implementation of SimulationRepository — delegates to SimulationPersistence.
SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#2.1
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.simulation_persistence import SimulationPersistence


class SqlSimulationRepository:
    """Wraps the existing SimulationPersistence behind the Repository Protocol.

    SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#2.1

    This adapter layer allows the Service to depend on the Protocol, not on
    SQLAlchemy internals. The session is injected per-call (request-scoped).
    """

    def __init__(self, persistence: SimulationPersistence | None = None) -> None:
        self._p = persistence or SimulationPersistence()

    # ---- Writes ---------------------------------------------------------- #

    async def save_creation(
        self, sim_id: UUID, config: Any, agents: list[Any],
        edges: list[tuple[Any, Any, dict]], *, session: AsyncSession,
    ) -> None:
        await self._p.persist_creation(session, sim_id, config, agents, edges)

    async def save_step(
        self, sim_id: UUID, result: Any, agents: list[Any] | None = None,
        *, session: AsyncSession,
    ) -> None:
        await self._p.persist_step(session, sim_id, result, agents=agents)

    async def save_status(
        self, sim_id: UUID, status: str, step: int | None = None,
        *, session: AsyncSession,
    ) -> None:
        await self._p.persist_status(session, sim_id, status, step)

    # ---- Reads ----------------------------------------------------------- #

    async def find_by_id(self, sim_id: UUID, *, session: AsyncSession) -> dict | None:
        return await self._p.load_simulation(session, sim_id)

    async def list_all(
        self, *, status: str | None = None, limit: int = 50, offset: int = 0,
        session: AsyncSession,
    ) -> list[dict]:
        return await self._p.load_simulations(session, status=status, limit=limit, offset=offset)

    async def count(self, status: str | None = None, *, session: AsyncSession) -> int:
        return await self._p.count_simulations(session, status=status)

    async def load_steps(self, sim_id: UUID, *, session: AsyncSession) -> list[dict]:
        return await self._p.load_steps(session, sim_id)

    async def restore_state(self, sim_id: UUID, *, session: AsyncSession) -> dict | None:
        return await self._p.restore_simulation_state(session, sim_id)

    async def row_exists(self, sim_id: UUID, *, session: AsyncSession) -> bool:
        return await self._p.simulation_row_exists(session, sim_id)

    # ---- Misc ------------------------------------------------------------ #

    @property
    def failed_queue(self) -> list[dict]:
        return self._p.failed_queue

    async def persist_event(
        self, sim_id: UUID, event_type: str, step: int, data: dict,
        *, session: AsyncSession,
    ) -> None:
        await self._p.persist_event(session, sim_id, event_type, step, data)

    async def persist_llm_calls(
        self, sim_id: UUID, call_logs: list, *, session: AsyncSession,
    ) -> None:
        await self._p.persist_llm_calls(session, sim_id, call_logs)

    async def persist_thread_messages(
        self, messages: list, *, session: AsyncSession,
    ) -> None:
        await self._p.persist_thread_messages(session, messages)

    async def persist_expert_opinions(
        self, sim_id: UUID, step: int, opinions: list[dict],
        *, session: AsyncSession,
    ) -> None:
        await self._p.persist_expert_opinions(session, sim_id, step, opinions)

    async def persist_agent_memories(
        self, sim_id: UUID, memories: list[dict],
        *, session: AsyncSession,
    ) -> None:
        await self._p.persist_agent_memories(session, sim_id, memories)


__all__ = ["SqlSimulationRepository"]
