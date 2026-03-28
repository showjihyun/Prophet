"""LLM Dashboard endpoints.
SPEC: docs/spec/06_API_SPEC.md#6-llm-dashboard-endpoints
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_orchestrator
from app.api.schemas import LLMCallsResponse, LLMImpactResponse, LLMStatsResponse
from app.api.simulations import _get_state_or_404

router = APIRouter(
    prefix="/api/v1/simulations/{simulation_id}/llm",
    tags=["llm"],
)


@router.get("/stats", response_model=LLMStatsResponse)
async def get_llm_stats(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> LLMStatsResponse:
    """LLM usage statistics for the simulation.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idllmstats
    """
    _get_state_or_404(orchestrator, simulation_id)

    try:
        result = orchestrator.get_llm_stats(simulation_id)
        if isinstance(result, dict):
            return LLMStatsResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    return LLMStatsResponse()


@router.get("/calls", response_model=LLMCallsResponse)
async def get_llm_calls(
    simulation_id: str,
    step: int | None = Query(None),
    agent_id: str | None = Query(None),
    provider: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    orchestrator: Any = Depends(get_orchestrator),
) -> LLMCallsResponse:
    """Recent LLM call logs.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idllmcalls
    """
    _get_state_or_404(orchestrator, simulation_id)

    try:
        result = orchestrator.get_llm_calls(
            simulation_id, step=step, agent_id=agent_id, provider=provider, limit=limit
        )
        if isinstance(result, dict):
            return LLMCallsResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    return LLMCallsResponse(calls=[])


@router.get("/impact", response_model=LLMImpactResponse)
async def get_llm_impact(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> LLMImpactResponse:
    """Get current engine impact assessment.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idllmimpact
    """
    _get_state_or_404(orchestrator, simulation_id)

    try:
        result = orchestrator.get_llm_impact(simulation_id)
        if isinstance(result, dict):
            return LLMImpactResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    return LLMImpactResponse()
