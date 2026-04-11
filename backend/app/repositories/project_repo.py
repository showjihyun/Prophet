"""SQL implementation of ProjectRepository.
SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#2.2
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, Scenario

logger = logging.getLogger(__name__)


class SqlProjectRepository:
    """SQLAlchemy implementation of ProjectRepository Protocol.

    SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#2.2
    """

    async def create(self, name: str, *, session: AsyncSession) -> dict:
        project = Project(project_id=uuid4(), name=name)
        session.add(project)
        await session.commit()
        return self._project_to_dict(project)

    async def find_by_id(self, project_id: UUID, *, session: AsyncSession) -> dict | None:
        result = await session.execute(
            select(Project).where(Project.project_id == project_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._project_to_dict(row)

    async def list_all(self, *, session: AsyncSession) -> list[dict]:
        result = await session.execute(
            select(Project).order_by(Project.created_at.desc())
        )
        return [self._project_to_dict(r) for r in result.scalars().all()]

    async def delete(self, project_id: UUID, *, session: AsyncSession) -> None:
        await session.execute(
            delete(Scenario).where(Scenario.project_id == project_id)
        )
        await session.execute(
            delete(Project).where(Project.project_id == project_id)
        )
        await session.commit()

    async def create_scenario(
        self, project_id: UUID, data: dict, *, session: AsyncSession,
    ) -> dict:
        scenario = Scenario(
            scenario_id=uuid4(),
            project_id=project_id,
            name=data.get("name", "Unnamed Scenario"),
            config=data.get("config", {}),
        )
        session.add(scenario)
        await session.commit()
        return self._scenario_to_dict(scenario)

    async def list_scenarios(
        self, project_id: UUID, *, session: AsyncSession,
    ) -> list[dict]:
        result = await session.execute(
            select(Scenario).where(Scenario.project_id == project_id)
        )
        return [self._scenario_to_dict(r) for r in result.scalars().all()]

    async def delete_scenario(
        self, project_id: UUID, scenario_id: UUID, *, session: AsyncSession,
    ) -> None:
        await session.execute(
            delete(Scenario).where(
                Scenario.project_id == project_id,
                Scenario.scenario_id == scenario_id,
            )
        )
        await session.commit()

    @staticmethod
    def _project_to_dict(p: Project) -> dict:
        return {
            "project_id": str(p.project_id),
            "name": p.name,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }

    @staticmethod
    def _scenario_to_dict(s: Scenario) -> dict:
        return {
            "scenario_id": str(s.scenario_id),
            "project_id": str(s.project_id),
            "name": s.name,
            "config": s.config or {},
            "simulation_id": str(s.simulation_id) if s.simulation_id else None,
            "status": s.status or "draft",
        }


__all__ = ["SqlProjectRepository"]
