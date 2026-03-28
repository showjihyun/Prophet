"""Community endpoints.
SPEC: docs/spec/06_API_SPEC.md#5-community-endpoints
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_orchestrator
from app.api.schemas import CommunitiesListResponse
from app.api.simulations import _get_state_or_404

router = APIRouter(
    prefix="/api/v1/simulations/{simulation_id}/communities",
    tags=["communities"],
)


@router.get("/", response_model=CommunitiesListResponse)
async def list_communities(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> CommunitiesListResponse:
    """List all communities with current metrics.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idcommunities
    """
    _get_state_or_404(orchestrator, simulation_id)

    try:
        result = orchestrator.list_communities(simulation_id)
        if isinstance(result, dict):
            return CommunitiesListResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    return CommunitiesListResponse(communities=[])
