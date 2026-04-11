"""Network endpoints.
SPEC: docs/spec/06_API_SPEC.md#4-network-endpoints
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response

from app.api.deps import get_orchestrator
from app.api.schemas import NetworkFormat, NetworkGraphResponse, NetworkMetricsResponse
from app.api.simulations import _get_state_or_404, _sim_id_to_uuid

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/simulations/{simulation_id}/network",
    tags=["network"],
)


def _network_etag(simulation_id: str, step: int, *, summary: bool, format: str) -> str:
    """Weak ETag keyed by (sim_id, current_step). Graph topology is invariant
    between steps, so the same (sim, step, view) always yields the same payload.
    """
    return f'W/"{simulation_id}-{step}-{format}-{"s" if summary else "f"}"'


@router.get("/", response_model=NetworkGraphResponse)
async def get_network(
    simulation_id: str,
    response: Response,
    format: NetworkFormat = Query(NetworkFormat.CYTOSCAPE),
    summary: bool = Query(False, description="If true, return only counts (fast path)"),
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    orchestrator: Any = Depends(get_orchestrator),
) -> NetworkGraphResponse:
    """Get network graph data (for visualization).
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idnetwork

    ?summary=true returns an empty nodes/edges payload plus counts so the
    frontend can render a skeleton while the full graph loads in parallel.
    Full-graph serialization runs on a worker thread to avoid blocking the
    event loop for multi-thousand-node networks.
    """
    _sim_id_to_uuid(simulation_id)  # invalid UUIDs still 404
    # Historical sims (DB-only after restart) have no in-memory network.
    # Return empty graph instead of 404 — frontend handles it gracefully.
    try:
        state = _get_state_or_404(orchestrator, simulation_id)
    except HTTPException as e:
        if e.status_code != 404:
            raise
        return NetworkGraphResponse(nodes=[], edges=[])
    etag = _network_etag(simulation_id, state.current_step, summary=summary, format=format.value)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "private, max-age=0, must-revalidate"
    if if_none_match == etag:
        response.status_code = 304
        return NetworkGraphResponse(nodes=[], edges=[])

    if summary:
        try:
            s = orchestrator.get_network_summary(simulation_id)
            return NetworkGraphResponse(
                nodes=[],
                edges=[],
                total_nodes=s.get("total_nodes", 0),
                total_edges=s.get("total_edges", 0),
            )
        except (ValueError, TypeError):
            return NetworkGraphResponse(nodes=[], edges=[])

    try:
        # Offload the 4-pass graph walk + JSON construction to a thread so
        # large networks don't stall the event loop.
        result = await asyncio.to_thread(
            orchestrator.get_network, simulation_id, format.value
        )
        return NetworkGraphResponse(**result)
    except ValueError as e:
        logger.warning("Network unavailable for %s: %s", simulation_id, e)
        return NetworkGraphResponse(nodes=[], edges=[])


@router.get("/metrics", response_model=NetworkMetricsResponse)
async def get_network_metrics(
    simulation_id: str,
    response: Response,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    orchestrator: Any = Depends(get_orchestrator),
) -> NetworkMetricsResponse:
    """Current network metrics.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idnetworkmetrics
    """
    _sim_id_to_uuid(simulation_id)
    try:
        state = _get_state_or_404(orchestrator, simulation_id)
    except HTTPException as e:
        if e.status_code != 404:
            raise
        return NetworkMetricsResponse()
    etag = f'W/"{simulation_id}-{state.current_step}-metrics"'
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "private, max-age=0, must-revalidate"
    if if_none_match == etag:
        response.status_code = 304
        return NetworkMetricsResponse()

    try:
        # Heavy NetworkX algorithms (clustering, shortest path, modularity)
        # run on a worker thread. Results are memoized per (sim_id, step)
        # inside the orchestrator.
        result = await asyncio.to_thread(
            orchestrator.get_network_metrics, simulation_id
        )
        return NetworkMetricsResponse(**result)
    except ValueError as e:
        logger.warning("Network metrics unavailable for %s: %s", simulation_id, e)
        return NetworkMetricsResponse()
