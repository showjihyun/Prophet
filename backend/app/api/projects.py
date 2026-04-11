"""Project & Scenario endpoints.
SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_orchestrator, get_session, get_simulation_repo
from app.api.schemas import (
    CreateProjectRequest,
    CreateScenarioRequest,
    ErrorResponse,
    ProjectDetailResponse,
    ProjectResponse,
    ScenarioResponse,
    UpdateProjectRequest,
)
from app.engine.network.schema import CommunityConfig
from app.engine.simulation.schema import CampaignConfig, SimulationConfig
from app.models.project import Project, Scenario
from app.repositories.protocols import SimulationRepository

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


# ---- helpers ----

def _project_not_found(project_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=ErrorResponse(
            type="https://prophet.io/errors/not-found",
            title="Project Not Found",
            status=404,
            detail=f"Project {project_id} does not exist",
            instance=f"/api/v1/projects/{project_id}",
        ).model_dump(),
    )


def _scenario_not_found(scenario_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=ErrorResponse(
            type="https://prophet.io/errors/not-found",
            title="Scenario Not Found",
            status=404,
            detail=f"Scenario {scenario_id} does not exist",
            instance=f"/api/v1/projects/scenarios/{scenario_id}",
        ).model_dump(),
    )


def _scenario_to_response(s: Scenario) -> ScenarioResponse:
    return ScenarioResponse(
        scenario_id=str(s.scenario_id),
        name=s.name,
        description=s.description or "",
        status=s.status,
        simulation_id=str(s.simulation_id) if s.simulation_id else None,
        config=s.config or {},
        created_at=s.created_at,
    )


# ---- Default communities for scenario /run ----

_DEFAULT_COMMUNITIES: list[CommunityConfig] = [
    CommunityConfig(id="A", name="early_adopters", size=100, agent_type="early_adopter"),
    CommunityConfig(id="B", name="general_consumers", size=500, agent_type="consumer"),
    CommunityConfig(id="C", name="skeptics", size=200, agent_type="skeptic"),
    CommunityConfig(id="D", name="experts", size=30, agent_type="expert"),
    CommunityConfig(id="E", name="influencers", size=170, agent_type="influencer"),
]


# ---- Endpoints ----

@router.post("/", status_code=201, response_model=ProjectResponse)
async def create_project(
    body: CreateProjectRequest,
    session: AsyncSession = Depends(get_session),
) -> ProjectResponse:
    """Create a new project.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    project = Project(
        project_id=uuid.uuid4(),
        name=body.name,
        description=body.description or None,
        status="active",
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)

    return ProjectResponse(
        project_id=str(project.project_id),
        name=project.name,
        description=project.description or "",
        status=project.status,
        scenario_count=0,
        created_at=project.created_at,
    )


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_session),
) -> list[ProjectResponse]:
    """List all projects with scenario count.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    # Fetch all projects
    result = await session.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()

    # Count scenarios per project
    count_result = await session.execute(
        select(Scenario.project_id, func.count(Scenario.scenario_id).label("cnt"))
        .group_by(Scenario.project_id)
    )
    counts: dict[uuid.UUID, int] = {row.project_id: row.cnt for row in count_result}

    return [
        ProjectResponse(
            project_id=str(p.project_id),
            name=p.name,
            description=p.description or "",
            status=p.status,
            scenario_count=counts.get(p.project_id, 0),
            created_at=p.created_at,
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> ProjectDetailResponse:
    """Get project detail with scenarios.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    try:
        pid = uuid.UUID(project_id)
    except (ValueError, AttributeError):
        raise _project_not_found(project_id)

    result = await session.execute(select(Project).where(Project.project_id == pid))
    project = result.scalar_one_or_none()
    if project is None:
        raise _project_not_found(project_id)

    sc_result = await session.execute(
        select(Scenario).where(Scenario.project_id == pid).order_by(Scenario.created_at.desc())
    )
    scenarios = sc_result.scalars().all()

    return ProjectDetailResponse(
        project_id=str(project.project_id),
        name=project.name,
        description=project.description or "",
        status=project.status,
        scenarios=[_scenario_to_response(s) for s in scenarios],
        created_at=project.created_at,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: UpdateProjectRequest,
    session: AsyncSession = Depends(get_session),
) -> ProjectResponse:
    """Update project name and/or description.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    try:
        pid = uuid.UUID(project_id)
    except (ValueError, AttributeError):
        raise _project_not_found(project_id)

    result = await session.execute(select(Project).where(Project.project_id == pid))
    project = result.scalar_one_or_none()
    if project is None:
        raise _project_not_found(project_id)

    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description or None

    await session.commit()
    await session.refresh(project)

    # Count scenarios for the response
    count_result = await session.execute(
        select(func.count(Scenario.scenario_id)).where(Scenario.project_id == pid)
    )
    scenario_count: int = count_result.scalar_one() or 0

    return ProjectResponse(
        project_id=str(project.project_id),
        name=project.name,
        description=project.description or "",
        status=project.status,
        scenario_count=scenario_count,
        created_at=project.created_at,
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a project and all its scenarios.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    try:
        pid = uuid.UUID(project_id)
    except (ValueError, AttributeError):
        raise _project_not_found(project_id)

    result = await session.execute(select(Project).where(Project.project_id == pid))
    project = result.scalar_one_or_none()
    if project is None:
        raise _project_not_found(project_id)

    # Bulk-delete child scenarios in one statement, then the project.
    await session.execute(delete(Scenario).where(Scenario.project_id == pid))
    await session.delete(project)
    await session.commit()


@router.post("/{project_id}/scenarios", status_code=201, response_model=ScenarioResponse)
async def create_scenario(
    project_id: str,
    body: CreateScenarioRequest,
    session: AsyncSession = Depends(get_session),
) -> ScenarioResponse:
    """Create a scenario within a project.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    try:
        pid = uuid.UUID(project_id)
    except (ValueError, AttributeError):
        raise _project_not_found(project_id)

    result = await session.execute(select(Project).where(Project.project_id == pid))
    if result.scalar_one_or_none() is None:
        raise _project_not_found(project_id)

    scenario = Scenario(
        scenario_id=uuid.uuid4(),
        project_id=pid,
        name=body.name,
        description=body.description or None,
        status="draft",
        config=body.config or {},
    )
    session.add(scenario)
    await session.commit()
    await session.refresh(scenario)

    return _scenario_to_response(scenario)


@router.post("/{project_id}/scenarios/{scenario_id}/run", status_code=200)
async def run_scenario(
    project_id: str,
    scenario_id: str,
    session: AsyncSession = Depends(get_session),
    orchestrator: Any = Depends(get_orchestrator),
    repo: SimulationRepository = Depends(get_simulation_repo),
) -> dict[str, Any]:
    """Create and start a simulation from a scenario config.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    try:
        pid = uuid.UUID(project_id)
    except (ValueError, AttributeError):
        raise _project_not_found(project_id)

    try:
        sid = uuid.UUID(scenario_id)
    except (ValueError, AttributeError):
        raise _scenario_not_found(scenario_id)

    sc_result = await session.execute(
        select(Scenario).where(Scenario.scenario_id == sid, Scenario.project_id == pid)
    )
    scenario = sc_result.scalar_one_or_none()
    if scenario is None:
        raise _scenario_not_found(scenario_id)

    # Build simulation config from scenario config
    cfg = scenario.config or {}
    sim_id = uuid.uuid4()

    # Build communities from scenario config or use defaults
    raw_communities = cfg.get("communities")
    if raw_communities and isinstance(raw_communities, list):
        communities = [
            CommunityConfig(
                id=c.get("id", str(i)),
                name=c.get("name", f"community_{i}"),
                size=c.get("size", 100),
                agent_type=c.get("agent_type", "consumer"),
            )
            for i, c in enumerate(raw_communities)
        ]
    else:
        communities = list(_DEFAULT_COMMUNITIES)

    raw_campaign = cfg.get("campaign", {})
    campaign = CampaignConfig(
        name=raw_campaign.get("name", scenario.name),
        budget=raw_campaign.get("budget", 0.0),
        channels=raw_campaign.get("channels", ["social_media"]),
        message=raw_campaign.get("message", scenario.name),
        target_communities=raw_campaign.get("target_communities", ["all"]),
        novelty=raw_campaign.get("novelty", 0.5),
        utility=raw_campaign.get("utility", 0.5),
        controversy=raw_campaign.get("controversy", 0.1),
    )

    sim_config = SimulationConfig(
        simulation_id=sim_id,
        name=cfg.get("name", scenario.name),
        description=cfg.get("description", scenario.description or ""),
        communities=communities,
        campaign=campaign,
        max_steps=cfg.get("max_steps", 50),
        random_seed=cfg.get("random_seed"),
        default_llm_provider=cfg.get("default_llm_provider", "ollama"),
        slm_llm_ratio=cfg.get("slm_llm_ratio", 0.5),
        slm_model=cfg.get("slm_model", "phi4"),
        budget_usd=cfg.get("budget_usd", 10.0),
    )

    state = orchestrator.create_simulation(sim_config)

    # Persist simulation to DB. ``save_creation`` is STRICT (wraps
    # ``persist_creation`` which re-raises on failure), so a successful
    # return guarantees the DB row exists and FK references are safe.
    # On failure, we must still clean up the ghost in-memory state.
    edges = list(state.network.graph.edges(data=True)) if state.network else []
    try:
        await repo.save_creation(
            state.simulation_id, sim_config, state.agents, edges, session=session,
        )
    except Exception:
        logger.exception(
            "run_scenario: save_creation failed for %s — cleaning up memory",
            state.simulation_id,
        )
        try:
            await orchestrator.delete_simulation(state.simulation_id)
        except KeyError:
            pass  # already gone
        raise HTTPException(
            status_code=500,
            detail="Simulation could not be persisted to database. Please retry.",
        )

    # Row is guaranteed to exist — link the scenario and start the simulation.
    await orchestrator.start(state.simulation_id)
    scenario.simulation_id = state.simulation_id
    scenario.status = "running"
    try:
        await session.commit()
    except Exception:
        logger.exception(
            "FK commit failed for scenario %s → simulation %s",
            scenario_id, state.simulation_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Scenario could not be linked to simulation. Please retry.",
        )

    return {"simulation_id": str(state.simulation_id), "status": "running"}


@router.delete("/{project_id}/scenarios/{scenario_id}", status_code=204)
async def delete_scenario(
    project_id: str,
    scenario_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a scenario.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    try:
        pid = uuid.UUID(project_id)
    except (ValueError, AttributeError):
        raise _project_not_found(project_id)

    try:
        sid = uuid.UUID(scenario_id)
    except (ValueError, AttributeError):
        raise _scenario_not_found(scenario_id)

    sc_result = await session.execute(
        select(Scenario).where(Scenario.scenario_id == sid, Scenario.project_id == pid)
    )
    scenario = sc_result.scalar_one_or_none()
    if scenario is None:
        raise _scenario_not_found(scenario_id)

    await session.delete(scenario)
    await session.commit()
