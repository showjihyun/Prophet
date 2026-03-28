"""Network endpoints.
SPEC: docs/spec/06_API_SPEC.md#4-network-endpoints
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_orchestrator
from app.api.schemas import NetworkFormat, NetworkGraphResponse, NetworkMetricsResponse
from app.api.simulations import _get_state_or_404

router = APIRouter(
    prefix="/api/v1/simulations/{simulation_id}/network",
    tags=["network"],
)


@router.get("/", response_model=NetworkGraphResponse)
async def get_network(
    simulation_id: str,
    format: NetworkFormat = Query(NetworkFormat.CYTOSCAPE),
    orchestrator: Any = Depends(get_orchestrator),
) -> NetworkGraphResponse:
    """Get network graph data (for visualization).
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idnetwork
    """
    _get_state_or_404(orchestrator, simulation_id)

    try:
        result = orchestrator.get_network(simulation_id, format=format.value)
        if isinstance(result, dict):
            return NetworkGraphResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    return NetworkGraphResponse(nodes=[], edges=[])


@router.get("/metrics", response_model=NetworkMetricsResponse)
async def get_network_metrics(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> NetworkMetricsResponse:
    """Current network metrics.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idnetworkmetrics
    """
    _get_state_or_404(orchestrator, simulation_id)

    try:
        result = orchestrator.get_network_metrics(simulation_id)
        if isinstance(result, dict):
            return NetworkMetricsResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    return NetworkMetricsResponse()
