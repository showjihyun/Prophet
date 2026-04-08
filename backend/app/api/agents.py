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
from app.api.simulations import _get_state_or_404, _require_status, _sim_id_to_uuid

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
    # Validate UUID format first — invalid IDs should always 404.
    _sim_id_to_uuid(simulation_id)
    # Historical sims (DB-only, no in-memory state after restart) return an
    # empty list instead of 404 — the frontend handles empty gracefully.
    try:
        _get_state_or_404(orchestrator, simulation_id)
    except HTTPException as e:
        if e.status_code != 404:
            raise
        return PaginatedResponse(items=[], total=0)

    result = orchestrator.list_agents(
        simulation_id,
        community_id=community_id,
        action=action,
        adopted=adopted,
        limit=limit,
        offset=offset,
    )
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                type="https://prophet.io/errors/orchestrator-contract",
                title="Orchestrator Contract Violation",
                status=500,
                detail="list_agents returned a non-dict payload",
                instance=f"/api/v1/simulations/{simulation_id}/agents",
            ).model_dump(),
        )
    return PaginatedResponse(**result)


@router.get("/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(
    simulation_id: str,
    agent_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> AgentDetailResponse:
    """Get full agent state at current step.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idagentsagent_id
    """
    _sim_id_to_uuid(simulation_id)
    # Historical sims (DB-only after restart) have no in-memory agent state.
    try:
        _get_state_or_404(orchestrator, simulation_id)
    except HTTPException as e:
        if e.status_code != 404:
            raise
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                type="https://prophet.io/errors/historical-simulation",
                title="Agent Data Unavailable",
                status=404,
                detail=f"Agent detail unavailable — simulation {simulation_id} is historical (server was restarted). Re-run the simulation to view agent data.",
                instance=f"/api/v1/simulations/{simulation_id}/agents/{agent_id}",
            ).model_dump(),
        )

    # Orchestrator raises ValueError with "not found" text when the agent
    # doesn't exist. Everything else is a real bug and must surface.
    try:
        result = orchestrator.get_agent(simulation_id, agent_id)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                type="https://prophet.io/errors/not-found",
                title="Agent Not Found",
                status=404,
                detail=str(e),
                instance=f"/api/v1/simulations/{simulation_id}/agents/{agent_id}",
            ).model_dump(),
        ) from e
    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="get_agent returned non-dict")
    return AgentDetailResponse(**result)


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
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(state, SimulationStatus.PAUSED)

    try:
        result = orchestrator.patch_agent(simulation_id, agent_id, body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                type="https://prophet.io/errors/not-found",
                title="Agent Not Found",
                status=404,
                detail=str(e),
                instance=f"/api/v1/simulations/{simulation_id}/agents/{agent_id}",
            ).model_dump(),
        ) from e
    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="patch_agent returned non-dict")
    return AgentDetailResponse(**result)


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
    _sim_id_to_uuid(simulation_id)
    try:
        _get_state_or_404(orchestrator, simulation_id)
    except HTTPException as e:
        if e.status_code != 404:
            raise
        return MemoryRecordResponse(memories=[])

    try:
        result = orchestrator.get_agent_memory(
            simulation_id, agent_id, memory_type=memory_type, limit=limit
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                type="https://prophet.io/errors/not-found",
                title="Agent Not Found",
                status=404,
                detail=str(e),
                instance=f"/api/v1/simulations/{simulation_id}/agents/{agent_id}/memory",
            ).model_dump(),
        ) from e
    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="get_agent_memory returned non-dict")
    return MemoryRecordResponse(**result)
