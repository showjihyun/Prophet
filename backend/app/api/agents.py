"""Agent endpoints.
SPEC: docs/spec/06_API_SPEC.md#3-agent-endpoints
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_orchestrator
from app.api.schemas import (
    AgentDetailResponse,
    AgentPatchRequest,
    AgentSummaryResponse,
    ErrorResponse,
    MemoryRecordResponse,
    PaginatedResponse,
    SimulationStatus,
)

# Import the in-memory store from simulations module
from app.api.simulations import _get_sim_or_404, _require_status

router = APIRouter(
    prefix="/api/v1/simulations/{simulation_id}/agents",
    tags=["agents"],
)


@router.get("/", response_model=PaginatedResponse)
async def list_agents(
    simulation_id: str,
    community_id: str | None = Query(None),
    action: str | None = Query(None),
    adopted: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    orchestrator: Any = Depends(get_orchestrator),
) -> PaginatedResponse:
    """List agents with current state.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idagents
    """
    _get_sim_or_404(simulation_id)

    try:
        result = orchestrator.list_agents(
            simulation_id,
            community_id=community_id,
            action=action,
            adopted=adopted,
            limit=limit,
            offset=offset,
        )
        if isinstance(result, dict):
            return PaginatedResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    # Fallback: empty list
    return PaginatedResponse(items=[], total=0)


@router.get("/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(
    simulation_id: str,
    agent_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> AgentDetailResponse:
    """Get full agent state at current step.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idagentsagent_id
    """
    _get_sim_or_404(simulation_id)

    try:
        result = orchestrator.get_agent(simulation_id, agent_id)
        if isinstance(result, dict):
            return AgentDetailResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    raise HTTPException(
        status_code=404,
        detail=ErrorResponse(
            type="https://prophet.io/errors/not-found",
            title="Agent Not Found",
            status=404,
            detail=f"Agent uuid={agent_id} not found in simulation {simulation_id}",
            instance=f"/api/v1/simulations/{simulation_id}/agents/{agent_id}",
        ).model_dump(),
    )


@router.patch("/{agent_id}", response_model=AgentDetailResponse)
async def patch_agent(
    simulation_id: str,
    agent_id: str,
    body: AgentPatchRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> AgentDetailResponse:
    """Modify agent (simulation must be PAUSED).
    SPEC: docs/spec/06_API_SPEC.md#patch-simulationssimulation_idagentsagent_id
    """
    sim = _get_sim_or_404(simulation_id)
    _require_status(sim, SimulationStatus.PAUSED)

    try:
        result = orchestrator.patch_agent(simulation_id, agent_id, body.model_dump(exclude_none=True))
        if isinstance(result, dict):
            return AgentDetailResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    raise HTTPException(
        status_code=404,
        detail=ErrorResponse(
            type="https://prophet.io/errors/not-found",
            title="Agent Not Found",
            status=404,
            detail=f"Agent uuid={agent_id} not found in simulation {simulation_id}",
            instance=f"/api/v1/simulations/{simulation_id}/agents/{agent_id}",
        ).model_dump(),
    )


@router.get("/{agent_id}/memory", response_model=MemoryRecordResponse)
async def get_agent_memory(
    simulation_id: str,
    agent_id: str,
    memory_type: str | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    orchestrator: Any = Depends(get_orchestrator),
) -> MemoryRecordResponse:
    """Get agent memory records.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idagentsagent_idmemory
    """
    _get_sim_or_404(simulation_id)

    try:
        result = orchestrator.get_agent_memory(
            simulation_id, agent_id, memory_type=memory_type, limit=limit
        )
        if isinstance(result, dict):
            return MemoryRecordResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    return MemoryRecordResponse(memories=[])
