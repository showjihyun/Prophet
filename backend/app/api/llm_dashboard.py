"""LLM Dashboard endpoints.
SPEC: docs/spec/06_API_SPEC.md#6-llm-dashboard-endpoints
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_orchestrator
from app.api.schemas import LLMCallsResponse, LLMImpactResponse, LLMStatsResponse
from app.api.simulations import _get_state_or_404

logger = logging.getLogger(__name__)

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
        return LLMStatsResponse(**result)
    except ValueError as e:
        logger.warning("LLM stats unavailable for %s: %s", simulation_id, e)
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
            simulation_id, step=step, agent_id=agent_id, provider=provider, limit=limit,
        )
        return LLMCallsResponse(**result)
    except ValueError as e:
        logger.warning("LLM calls unavailable for %s: %s", simulation_id, e)
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
        return LLMImpactResponse(**result)
    except ValueError as e:
        logger.warning("LLM impact unavailable for %s: %s", simulation_id, e)
        return LLMImpactResponse()
