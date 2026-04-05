"""Simulation endpoints.
SPEC: docs/spec/06_API_SPEC.md#2-simulation-endpoints
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_orchestrator, get_session, get_persistence
from app.api.ws import manager as ws_manager
from app.engine.simulation.persistence import SimulationPersistence
from app.api.schemas import (
    CreateSimulationRequest,
    EngineControlRequest,
    EngineControlResponse,
    ErrorResponse,
    InjectEventRequest,
    InjectEventResponse,
    MonteCarloRequest,
    MonteCarloStatusResponse,
    PaginatedResponse,
    RecommendEngineRequest,
    RecommendEngineResponse,
    ReplayResponse,
    RunAllResponse,
    ScenarioComparisonResponse,
    SimulationDetailResponse,
    SimulationResponse,
    SimulationStatus,
    StatusResponse,
    StepHistoryResponse,
    StepResultResponse,
)
from app.engine.agent.group_chat import GroupChatManager, GroupChat, GroupMessage
from app.engine.agent.interview import AgentInterviewer, InterviewResponse
from app.engine.network.schema import CommunityConfig
from app.engine.simulation.monte_carlo import MonteCarloRunner
from app.engine.simulation.schema import (
    CampaignConfig,
    SimulationConfig,
)
from app.llm.engine_control import EngineController

router = APIRouter(prefix="/api/v1/simulations", tags=["simulations"])

# ---- Monte Carlo jobs (Phase 6 placeholder until Celery is wired) ----
_monte_carlo_jobs: dict[str, dict[str, Any]] = {}

# ---- Default communities when none are provided ----
_DEFAULT_COMMUNITIES: list[CommunityConfig] = [
    CommunityConfig(id="A", name="early_adopters", size=100, agent_type="early_adopter"),
    CommunityConfig(id="B", name="general_consumers", size=500, agent_type="consumer"),
    CommunityConfig(id="C", name="skeptics", size=200, agent_type="skeptic"),
    CommunityConfig(id="D", name="experts", size=30, agent_type="expert"),
    CommunityConfig(id="E", name="influencers", size=170, agent_type="influencer"),
]


def _community_metric_dict(metric: Any) -> dict:
    """Convert CommunityStepMetrics to a plain dict (handles dataclass and dict)."""
    if isinstance(metric, dict):
        return metric
    # Dataclass / object with attributes
    result: dict = {}
    for attr in ("community_id", "adoption_count", "adoption_rate", "mean_belief",
                 "sentiment_variance", "active_agents", "dominant_action",
                 "new_propagation_count"):
        val = getattr(metric, attr, None)
        if val is not None:
            result[attr] = str(val) if attr == "community_id" else val
    return result


def _sim_id_to_uuid(simulation_id: str) -> UUID:
    """Convert string simulation_id to UUID, raising 404 on invalid format."""
    try:
        return UUID(simulation_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                type="https://prophet.io/errors/not-found",
                title="Simulation Not Found",
                status=404,
                detail=f"Simulation uuid={simulation_id} does not exist",
                instance=f"/api/v1/simulations/{simulation_id}",
            ).model_dump(),
        )


def _get_state_or_404(orchestrator: Any, simulation_id: str) -> Any:
    """Retrieve SimulationState from orchestrator or raise 404."""
    sim_uuid = _sim_id_to_uuid(simulation_id)
    try:
        return orchestrator.get_state(sim_uuid)
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                type="https://prophet.io/errors/not-found",
                title="Simulation Not Found",
                status=404,
                detail=f"Simulation uuid={simulation_id} does not exist",
                instance=f"/api/v1/simulations/{simulation_id}",
            ).model_dump(),
        )


def _require_status(state: Any, *allowed: SimulationStatus) -> None:
    """Raise 409 if simulation is not in one of the allowed statuses."""
    current = state.status
    allowed_values = {s.value for s in allowed}
    if current not in allowed_values:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                type="https://prophet.io/errors/simulation-running",
                title="Action Not Allowed",
                status=409,
                detail=f"Simulation is '{current}', expected one of {[s.value for s in allowed]}",
                instance=f"/api/v1/simulations/{state.simulation_id}",
            ).model_dump(),
        )


# ---- Endpoints ----


@router.post("/", status_code=201, response_model=SimulationResponse)
async def create_simulation(
    body: CreateSimulationRequest,
    orchestrator: Any = Depends(get_orchestrator),
    session: AsyncSession = Depends(get_session),
    persist: SimulationPersistence = Depends(get_persistence),
) -> SimulationResponse:
    """Create a new simulation run.
    SPEC: docs/spec/06_API_SPEC.md#post-simulations
    """
    sim_id = uuid.uuid4()

    # Build communities from request or use defaults
    if body.communities and isinstance(body.communities, list):
        communities = [
            CommunityConfig(
                id=c.get("id", str(i)),
                name=c.get("name", f"community_{i}"),
                size=c.get("size", 100),
                agent_type=c.get("agent_type", "consumer"),
                personality_profile=c.get("personality_profile", {}),
            )
            for i, c in enumerate(body.communities)
        ]
    else:
        communities = list(_DEFAULT_COMMUNITIES)

    config = SimulationConfig(
        simulation_id=sim_id,
        name=body.name,
        description=body.description or "",
        communities=communities,
        campaign=CampaignConfig(
            name=body.campaign.name,
            budget=body.campaign.budget or 0,
            channels=body.campaign.channels,
            message=body.campaign.message,
            target_communities=body.campaign.target_communities,
            novelty=body.campaign.novelty or 0.5,
            utility=body.campaign.utility or 0.5,
            controversy=body.campaign.controversy or 0.0,
        ),
        max_steps=body.max_steps or 50,
        random_seed=body.random_seed,
        default_llm_provider=body.default_llm_provider,
        slm_llm_ratio=body.slm_llm_ratio,
        slm_model=body.slm_model,
        budget_usd=body.budget_usd,
        platform=body.platform,
    )

    state = orchestrator.create_simulation(config)

    # Persist to DB (fire-and-forget, does not block response)
    edges = list(state.network.graph.edges(data=True)) if state.network else []
    await persist.persist_creation(session, state.simulation_id, config, state.agents, edges)

    # Compute real network metrics from generated graph
    net_metrics = {"clustering_coefficient": 0.0, "avg_path_length": 0.0}
    try:
        metrics = orchestrator.get_network_metrics(str(state.simulation_id))
        net_metrics = {
            "clustering_coefficient": metrics.get("clustering_coefficient", 0.0),
            "avg_path_length": metrics.get("avg_path_length", 0.0),
        }
    except (ValueError, KeyError):
        pass

    return SimulationResponse(
        simulation_id=str(state.simulation_id),
        status=SimulationStatus(state.status),
        total_agents=len(state.agents),
        network_metrics=net_metrics,
        created_at=datetime.now(timezone.utc),
    )


@router.get("/", response_model=PaginatedResponse)
async def list_simulations(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    orchestrator: Any = Depends(get_orchestrator),
    session: AsyncSession = Depends(get_session),
    persist: SimulationPersistence = Depends(get_persistence),
) -> PaginatedResponse:
    """List all simulation runs.
    SPEC: docs/spec/06_API_SPEC.md#get-simulations
    """
    # Build a dict of in-memory simulations (live, takes precedence)
    mem_items: dict[str, dict] = {}
    for state in orchestrator._simulations.values():
        mem_items[str(state.simulation_id)] = {
            "simulation_id": str(state.simulation_id),
            "name": state.config.name,
            "status": state.status,
            "current_step": state.current_step,
            "total_agents": len(state.agents),
        }

    # Load DB simulations and fill in any not present in memory
    db_sims = await persist.load_simulations(session)
    for db_sim in db_sims:
        sid = db_sim["simulation_id"]
        if sid not in mem_items:
            mem_items[sid] = {
                "simulation_id": sid,
                "name": db_sim.get("name", ""),
                "status": db_sim.get("status", "completed"),
                "current_step": db_sim.get("current_step", 0),
                "total_agents": 0,
            }

    items = list(mem_items.values())
    if status is not None:
        items = [i for i in items if i["status"] == status]

    total = len(items)
    items = items[offset: offset + limit]
    return PaginatedResponse(items=items, total=total)


@router.get("/{simulation_id}", response_model=SimulationDetailResponse)
async def get_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
    session: AsyncSession = Depends(get_session),
    persist: SimulationPersistence = Depends(get_persistence),
) -> SimulationDetailResponse:
    """Get simulation details.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_id
    """
    # Try in-memory first (live state)
    sim_uuid = _sim_id_to_uuid(simulation_id)
    try:
        state = orchestrator.get_state(sim_uuid)
        return SimulationDetailResponse(
            simulation_id=str(state.simulation_id),
            name=state.config.name,
            description=state.config.description,
            status=SimulationStatus(state.status),
            current_step=state.current_step,
            max_steps=state.config.max_steps,
            total_agents=len(state.agents),
            network_metrics={
                "clustering_coefficient": 0.0,
                "avg_path_length": 0.0,
            },
            config={},
            created_at=datetime.now(timezone.utc),
        )
    except (ValueError, KeyError):
        pass

    # Fallback: load from DB (read-only, completed/historical sims)
    db_sims = await persist.load_simulations(session)
    db_sim = next((s for s in db_sims if s["simulation_id"] == simulation_id), None)
    if db_sim is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                type="https://prophet.io/errors/not-found",
                title="Simulation Not Found",
                status=404,
                detail=f"Simulation uuid={simulation_id} does not exist",
                instance=f"/api/v1/simulations/{simulation_id}",
            ).model_dump(),
        )
    return SimulationDetailResponse(
        simulation_id=db_sim["simulation_id"],
        name=db_sim.get("name", ""),
        description=db_sim.get("description", ""),
        status=SimulationStatus(db_sim.get("status", "completed")),
        current_step=db_sim.get("current_step", 0),
        max_steps=db_sim.get("max_steps", 0),
        total_agents=0,
        network_metrics={
            "clustering_coefficient": 0.0,
            "avg_path_length": 0.0,
        },
        config={},
        created_at=datetime.now(timezone.utc),
    )


@router.post("/{simulation_id}/start", response_model=StatusResponse)
async def start_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
    session: AsyncSession = Depends(get_session),
    persist: SimulationPersistence = Depends(get_persistence),
) -> StatusResponse:
    """Start the simulation.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstart
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(state, SimulationStatus.CONFIGURED, SimulationStatus.PAUSED)
    now = datetime.now(timezone.utc)
    sim_uuid = _sim_id_to_uuid(simulation_id)
    orchestrator.start(sim_uuid)
    await persist.persist_status(session, sim_uuid, "running")
    asyncio.create_task(ws_manager.broadcast(str(sim_uuid), {
        "type": "status_change",
        "data": {"status": "running"},
    }))
    return StatusResponse(status=SimulationStatus.RUNNING, started_at=now)


@router.post("/{simulation_id}/step", response_model=StepResultResponse)
async def step_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
    session: AsyncSession = Depends(get_session),
    persist: SimulationPersistence = Depends(get_persistence),
) -> StepResultResponse:
    """Execute exactly one step.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstep
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(state, SimulationStatus.RUNNING, SimulationStatus.PAUSED)

    sim_uuid = _sim_id_to_uuid(simulation_id)
    result = await orchestrator.run_step(sim_uuid)

    # Persist step result + agent snapshots + status update
    await persist.persist_step(session, sim_uuid, result, agents=state.agents)
    await persist.persist_status(session, sim_uuid, state.status, state.current_step)

    # Persist LLM call summary for this step (one synthetic record per LLM call)
    if result.llm_calls_this_step > 0:
        llm_records = [
            {
                "agent_id": None,
                "step": result.step,
                "provider": "ollama",
                "model": "unknown",
                "prompt_hash": "",
                "latency_ms": None,
                "tokens": None,
                "cached": False,
                "tier": 1,
            }
            for _ in range(result.llm_calls_this_step)
        ]
        await persist.persist_llm_calls(session, sim_uuid, llm_records)

    # Broadcast step result via WebSocket
    asyncio.create_task(ws_manager.broadcast(str(sim_uuid), {
        "type": "step_result",
        "data": {
            "simulation_id": str(sim_uuid),
            "step": result.step,
            "total_adoption": result.total_adoption,
            "adoption_rate": result.adoption_rate,
            "diffusion_rate": result.diffusion_rate,
            "mean_sentiment": result.mean_sentiment,
            "sentiment_variance": result.sentiment_variance,
            "community_metrics": {
                k: _community_metric_dict(v)
                for k, v in result.community_metrics.items()
            },
            "emergent_events": [
                {
                    "event_type": e.event_type,
                    "step": e.step,
                    "community_id": str(e.community_id) if e.community_id else None,
                    "severity": e.severity,
                    "description": e.description,
                }
                for e in result.emergent_events
            ],
            "action_distribution": {k: v for k, v in result.action_distribution.items()},
            "llm_calls_this_step": result.llm_calls_this_step,
            "step_duration_ms": result.step_duration_ms,
        },
    }))

    # Broadcast individual emergent events
    for event in result.emergent_events:
        asyncio.create_task(ws_manager.broadcast(str(sim_uuid), {
            "type": "emergent_event",
            "data": {
                "event_type": event.event_type,
                "step": event.step,
                "community_id": str(event.community_id) if event.community_id else None,
                "severity": event.severity,
                "description": event.description,
            },
        }))

    # C-4: Broadcast agent_update for subscribed agents
    agent_state_map: dict[str, dict] = {}
    for agent in state.agents:
        aid = str(agent.agent_id)
        agent_state_map[aid] = {
            "agent_id": aid,
            "step": result.step,
            "belief": agent.belief,
            "action": agent.action.value if hasattr(agent.action, 'value') else str(agent.action),
            "adopted": agent.adopted,
            "exposure_count": agent.exposure_count,
            "emotion": {
                "interest": agent.emotion.interest,
                "trust": agent.emotion.trust,
                "skepticism": agent.emotion.skepticism,
                "excitement": agent.emotion.excitement,
            },
        }
    asyncio.create_task(
        ws_manager.broadcast_agent_updates(str(sim_uuid), agent_state_map)
    )

    # Broadcast status change if simulation completed
    if state.status == "completed":
        asyncio.create_task(ws_manager.broadcast(str(sim_uuid), {
            "type": "status_change",
            "data": {"status": "completed"},
        }))

    cm_resp: dict[str, Any] = {}
    for cid, metric in result.community_metrics.items():
        cm_resp[str(cid)] = _community_metric_dict(metric)

    return StepResultResponse(
        step=result.step,
        adoption_rate=result.adoption_rate,
        mean_sentiment=result.mean_sentiment,
        sentiment_variance=result.sentiment_variance,
        diffusion_rate=result.diffusion_rate,
        total_adoption=result.total_adoption,
        community_metrics=cm_resp,
        action_distribution=result.action_distribution,
        llm_calls_this_step=result.llm_calls_this_step,
        step_duration_ms=result.step_duration_ms,
        emergent_events=[
            {"type": e.event_type, "step": e.step, "community_id": str(e.community_id) if e.community_id else None}
            for e in result.emergent_events
        ] if result.emergent_events else [],
    )


@router.post("/{simulation_id}/run-all", response_model=RunAllResponse)
async def run_all_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
    session: AsyncSession = Depends(get_session),
    persist: SimulationPersistence = Depends(get_persistence),
) -> RunAllResponse:
    """Run all remaining steps to completion and return a report.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idrun-all
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(state, SimulationStatus.CONFIGURED, SimulationStatus.RUNNING)
    sim_uuid = _sim_id_to_uuid(simulation_id)

    try:
        report = await orchestrator.run_all(sim_uuid)
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                type="https://prophet.io/errors/invalid-state",
                title="Invalid Simulation State",
                status=409,
                detail=str(exc),
                instance=f"/api/v1/simulations/{simulation_id}/run-all",
            ).model_dump(),
        )

    # Persist final status
    await persist.persist_status(session, sim_uuid, report["status"], report["total_steps"])

    # Broadcast completion via WebSocket
    asyncio.create_task(ws_manager.broadcast(str(sim_uuid), {
        "type": "run_all_complete",
        "data": {
            "simulation_id": simulation_id,
            "total_steps": report["total_steps"],
            "final_adoption_rate": report["final_adoption_rate"],
            "final_mean_sentiment": report["final_mean_sentiment"],
            "emergent_events_count": report["emergent_events_count"],
            "duration_ms": report["duration_ms"],
            "status": report["status"],
        },
    }))
    asyncio.create_task(ws_manager.broadcast(str(sim_uuid), {
        "type": "status_change",
        "data": {"status": report["status"]},
    }))

    return RunAllResponse(
        simulation_id=simulation_id,
        status=report["status"],
        total_steps=report["total_steps"],
        final_adoption_rate=report["final_adoption_rate"],
        final_mean_sentiment=report["final_mean_sentiment"],
        community_summary=report["community_breakdown"],
        emergent_events_count=report["emergent_events_count"],
        duration_ms=report["duration_ms"],
    )


@router.post("/{simulation_id}/pause", response_model=StatusResponse)
async def pause_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
    session: AsyncSession = Depends(get_session),
    persist: SimulationPersistence = Depends(get_persistence),
) -> StatusResponse:
    """Pause after current step completes.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idpause
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(state, SimulationStatus.RUNNING)
    sim_uuid = _sim_id_to_uuid(simulation_id)
    await orchestrator.pause(sim_uuid)
    await persist.persist_status(session, sim_uuid, "paused", state.current_step)
    asyncio.create_task(ws_manager.broadcast(str(sim_uuid), {
        "type": "status_change",
        "data": {"status": "paused"},
    }))
    return StatusResponse(
        status=SimulationStatus.PAUSED, current_step=state.current_step,
    )


@router.post("/{simulation_id}/resume", response_model=StatusResponse)
async def resume_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> StatusResponse:
    """Resume from paused state.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idresume
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(state, SimulationStatus.PAUSED)
    sim_uuid = _sim_id_to_uuid(simulation_id)
    await orchestrator.resume(sim_uuid)
    asyncio.create_task(ws_manager.broadcast(str(sim_uuid), {
        "type": "status_change",
        "data": {"status": "running"},
    }))
    return StatusResponse(status=SimulationStatus.RUNNING)


@router.post("/{simulation_id}/stop", response_model=StatusResponse)
async def stop_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
    session: AsyncSession = Depends(get_session),
    persist: SimulationPersistence = Depends(get_persistence),
) -> StatusResponse:
    """Stop and mark as completed.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstop
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(
        state,
        SimulationStatus.RUNNING,
        SimulationStatus.PAUSED,
        SimulationStatus.CONFIGURED,
    )
    state.status = "completed"
    sim_uuid = _sim_id_to_uuid(simulation_id)
    await persist.persist_status(session, sim_uuid, "completed")
    asyncio.create_task(ws_manager.broadcast(str(sim_uuid), {
        "type": "status_change",
        "data": {"status": "completed"},
    }))
    return StatusResponse(status=SimulationStatus.COMPLETED)


@router.get("/{simulation_id}/steps", response_model=StepHistoryResponse)
async def get_steps(
    simulation_id: str,
    from_step: int | None = Query(None, ge=0),
    to_step: int | None = Query(None, ge=0),
    metrics: str | None = Query(None),
    orchestrator: Any = Depends(get_orchestrator),
    session: AsyncSession = Depends(get_session),
    persist: SimulationPersistence = Depends(get_persistence),
) -> StepHistoryResponse:
    """Get step history.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idsteps
    """
    sim_uuid = _sim_id_to_uuid(simulation_id)

    # Try in-memory first
    mem_step_history: list[Any] = []
    try:
        state = orchestrator.get_state(sim_uuid)
        mem_step_history = list(state.step_history)
    except (ValueError, KeyError):
        pass

    steps = []
    if mem_step_history:
        # Build from in-memory step history
        for sr in mem_step_history:
            if from_step is not None and sr.step < from_step:
                continue
            if to_step is not None and sr.step > to_step:
                continue
            cm: dict[str, Any] = {}
            for cid, metric in sr.community_metrics.items():
                cm[str(cid)] = _community_metric_dict(metric)
            steps.append(StepResultResponse(
                step=sr.step,
                adoption_rate=sr.adoption_rate,
                mean_sentiment=sr.mean_sentiment,
                sentiment_variance=sr.sentiment_variance,
                diffusion_rate=sr.diffusion_rate,
                total_adoption=sr.total_adoption,
                community_metrics=cm,
                action_distribution=sr.action_distribution,
                llm_calls_this_step=sr.llm_calls_this_step,
                step_duration_ms=sr.step_duration_ms,
                emergent_events=[
                    {"type": e.event_type, "step": e.step, "community_id": str(e.community_id) if e.community_id else None}
                    for e in sr.emergent_events
                ] if sr.emergent_events else [],
            ))
    else:
        # Fallback: load from DB (completed/historical sims not in memory)
        db_steps = await persist.load_steps(session, sim_uuid)
        for sr in db_steps:
            step_num = sr.get("step", 0)
            if from_step is not None and step_num < from_step:
                continue
            if to_step is not None and step_num > to_step:
                continue
            steps.append(StepResultResponse(
                step=step_num,
                adoption_rate=sr.get("adoption_rate", 0.0),
                mean_sentiment=sr.get("mean_sentiment", 0.0),
                sentiment_variance=sr.get("sentiment_variance", 0.0),
                diffusion_rate=sr.get("diffusion_rate", 0.0),
                total_adoption=sr.get("total_adoption", 0),
                community_metrics=sr.get("community_metrics", {}),
                action_distribution=sr.get("action_distribution", {}),
                llm_calls_this_step=sr.get("llm_calls_this_step", 0),
                step_duration_ms=sr.get("step_duration_ms", 0.0),
                emergent_events=[],
            ))

    return StepHistoryResponse(steps=steps)


@router.post("/{simulation_id}/inject-event", response_model=InjectEventResponse)
async def inject_event(
    simulation_id: str,
    body: InjectEventRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> InjectEventResponse:
    """Inject an external event mid-simulation.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idinject-event
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(state, SimulationStatus.RUNNING, SimulationStatus.PAUSED)

    event_id = str(uuid.uuid4())
    effective_step = state.current_step + 1

    sim_uuid = _sim_id_to_uuid(simulation_id)
    try:
        orchestrator.inject_event(
            sim_uuid,
            event_type=body.event_type,
            payload={"content": body.content, "controversy": body.controversy},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return InjectEventResponse(event_id=event_id, effective_step=effective_step)


@router.post("/{simulation_id}/replay/{step}", response_model=ReplayResponse)
async def replay_from_step(
    simulation_id: str,
    step: int,
    orchestrator: Any = Depends(get_orchestrator),
) -> ReplayResponse:
    """Replay from a specific step (creates branch).
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idreplaystep
    """
    _get_state_or_404(orchestrator, simulation_id)
    replay_id = str(uuid.uuid4())

    sim_uuid = _sim_id_to_uuid(simulation_id)
    try:
        orchestrator.replay_step(sim_uuid, step)
    except (ValueError, NotImplementedError, AttributeError, TypeError) as e:
        import logging
        logging.getLogger(__name__).warning(f"replay_step fallback: {e}")

    return ReplayResponse(replay_id=replay_id, from_step=step)


@router.get(
    "/{simulation_id}/compare/{other_id}",
    response_model=ScenarioComparisonResponse,
)
async def compare_simulations(
    simulation_id: str,
    other_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> ScenarioComparisonResponse:
    """Compare two simulation runs.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idcompareother_simulation_id
    """
    state_a = _get_state_or_404(orchestrator, simulation_id)
    state_b = _get_state_or_404(orchestrator, other_id)

    last_a = state_a.step_history[-1] if state_a.step_history else None
    last_b = state_b.step_history[-1] if state_b.step_history else None

    comparison: dict[str, Any] = {}
    if last_a and last_b:
        viral_a = sum(
            1 for sr in state_a.step_history
            for ev in sr.emergent_events
            if ev.event_type == "viral_cascade"
        )
        viral_b = sum(
            1 for sr in state_b.step_history
            for ev in sr.emergent_events
            if ev.event_type == "viral_cascade"
        )
        winner = (
            str(state_a.simulation_id)
            if last_a.adoption_rate >= last_b.adoption_rate
            else str(state_b.simulation_id)
        )
        comparison = {
            "adoption_rate_a": last_a.adoption_rate,
            "adoption_rate_b": last_b.adoption_rate,
            "mean_sentiment_a": last_a.mean_sentiment,
            "mean_sentiment_b": last_b.mean_sentiment,
            "total_propagation_a": last_a.diffusion_rate,
            "total_propagation_b": last_b.diffusion_rate,
            "viral_cascades_a": viral_a,
            "viral_cascades_b": viral_b,
            "winner": winner,
        }

    return ScenarioComparisonResponse(
        simulation_a=simulation_id,
        simulation_b=other_id,
        comparison=comparison,
    )


async def _run_monte_carlo(job_id: str, simulation_id: str, config: Any, n_runs: int) -> None:
    """Background task to actually run Monte Carlo.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector
    """
    try:
        _monte_carlo_jobs[job_id]["status"] = "running"
        runner = MonteCarloRunner()
        result = await runner.run(config, n_runs=n_runs)
        completed_at = datetime.now(timezone.utc)
        _monte_carlo_jobs[job_id].update({
            "status": "completed",
            "viral_probability": result.viral_probability,
            "expected_reach": result.expected_reach,
            "p5_reach": result.p5_reach,
            "p50_reach": result.p50_reach,
            "p95_reach": result.p95_reach,
            "community_adoption": result.community_adoption,
            "completed_at": completed_at.isoformat(),
        })
        # Persist to PostgreSQL (NF07: DB is source of truth)
        await _persist_monte_carlo(job_id, simulation_id, n_runs, result, completed_at)
    except Exception as e:
        _monte_carlo_jobs[job_id].update({
            "status": "failed",
            "error_message": str(e),
        })
        await _persist_monte_carlo_failure(job_id, simulation_id, n_runs, str(e))


async def _persist_monte_carlo(
    job_id: str, simulation_id: str, n_runs: int, result: Any, completed_at: datetime
) -> None:
    """Persist completed MC results to monte_carlo_runs table."""
    from app.database import async_session
    from app.models.propagation import MonteCarloRun
    try:
        async with async_session() as session:
            run = MonteCarloRun(
                job_id=uuid.UUID(job_id),
                simulation_id=uuid.UUID(simulation_id),
                status="completed",
                n_runs=n_runs,
                viral_probability=result.viral_probability,
                expected_reach=result.expected_reach,
                p5_reach=result.p5_reach,
                p50_reach=result.p50_reach,
                p95_reach=result.p95_reach,
                community_adoption=result.community_adoption,
                started_at=_monte_carlo_jobs.get(job_id, {}).get("started_at"),
                completed_at=completed_at,
            )
            session.add(run)
            await session.commit()
    except Exception:
        pass  # Best-effort persist; in-memory result is still available


async def _persist_monte_carlo_failure(
    job_id: str, simulation_id: str, n_runs: int, error: str
) -> None:
    """Persist failed MC job to monte_carlo_runs table."""
    from app.database import async_session
    from app.models.propagation import MonteCarloRun
    try:
        async with async_session() as session:
            run = MonteCarloRun(
                job_id=uuid.UUID(job_id),
                simulation_id=uuid.UUID(simulation_id),
                status="failed",
                n_runs=n_runs,
                error_message=error,
                started_at=_monte_carlo_jobs.get(job_id, {}).get("started_at"),
            )
            session.add(run)
            await session.commit()
    except Exception:
        pass


@router.post(
    "/{simulation_id}/monte-carlo",
    status_code=202,
    response_model=MonteCarloStatusResponse,
)
async def start_monte_carlo(
    simulation_id: str,
    body: MonteCarloRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> MonteCarloStatusResponse:
    """Run Monte Carlo analysis.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idmonte-carlo
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    job = {
        "job_id": job_id,
        "simulation_id": simulation_id,
        "status": "queued",
        "n_runs": body.n_runs,
        "started_at": now,
    }
    _monte_carlo_jobs[job_id] = job

    # Fire background task using the simulation's config
    asyncio.create_task(_run_monte_carlo(job_id, simulation_id, state.config, body.n_runs))

    return MonteCarloStatusResponse(
        job_id=job_id,
        status="queued",
        n_runs=body.n_runs,
        started_at=now,
    )


@router.get(
    "/{simulation_id}/monte-carlo",
    response_model=MonteCarloStatusResponse | None,
)
async def get_latest_monte_carlo(
    simulation_id: str,
    session: AsyncSession = Depends(get_session),
) -> MonteCarloStatusResponse | None:
    """Get the latest Monte Carlo result for a simulation.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idmonte-carlo
    """
    # Check in-memory first
    for job in reversed(list(_monte_carlo_jobs.values())):
        if job.get("simulation_id") == simulation_id:
            return MonteCarloStatusResponse(**{k: v for k, v in job.items() if k != "simulation_id"})

    # Fallback: PostgreSQL
    from app.models.propagation import MonteCarloRun
    from sqlalchemy import select
    result = await session.execute(
        select(MonteCarloRun)
        .where(MonteCarloRun.simulation_id == uuid.UUID(simulation_id))
        .order_by(MonteCarloRun.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return MonteCarloStatusResponse(
        job_id=str(row.job_id),
        status=row.status,
        n_runs=row.n_runs,
        viral_probability=row.viral_probability,
        expected_reach=row.expected_reach,
        p5_reach=row.p5_reach,
        p50_reach=row.p50_reach,
        p95_reach=row.p95_reach,
        community_adoption=row.community_adoption,
        started_at=row.started_at,
        completed_at=row.completed_at,
        error_message=getattr(row, 'error_message', None),
    )


@router.get(
    "/{simulation_id}/monte-carlo/{job_id}",
    response_model=MonteCarloStatusResponse,
)
async def get_monte_carlo_status(
    simulation_id: str,
    job_id: str,
    orchestrator: Any = Depends(get_orchestrator),
    session: AsyncSession = Depends(get_session),
) -> MonteCarloStatusResponse:
    """Get Monte Carlo job status and results.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idmonte-carlojob_id
    """
    _get_state_or_404(orchestrator, simulation_id)
    job = _monte_carlo_jobs.get(job_id)
    if job is not None:
        return MonteCarloStatusResponse(**job)

    # Fallback: check PostgreSQL (NF07)
    from app.models.propagation import MonteCarloRun
    from sqlalchemy import select
    try:
        result = await session.execute(
            select(MonteCarloRun).where(MonteCarloRun.job_id == uuid.UUID(job_id))
        )
        row = result.scalar_one_or_none()
        if row is not None:
            return MonteCarloStatusResponse(
                job_id=str(row.job_id),
                status=row.status,
                n_runs=row.n_runs,
                viral_probability=row.viral_probability,
                expected_reach=row.expected_reach,
                p5_reach=row.p5_reach,
                p50_reach=row.p50_reach,
                p95_reach=row.p95_reach,
                community_adoption=row.community_adoption,
                started_at=row.started_at,
                completed_at=row.completed_at,
                error_message=getattr(row, 'error_message', None),
            )
    except Exception:
        pass

    raise HTTPException(
        status_code=404,
        detail=ErrorResponse(
            type="https://prophet.io/errors/not-found",
            title="Monte Carlo Job Not Found",
            status=404,
            detail=f"Job uuid={job_id} does not exist",
            instance=f"/api/v1/simulations/{simulation_id}/monte-carlo/{job_id}",
        ).model_dump(),
    )


@router.post("/{simulation_id}/engine-control", response_model=EngineControlResponse)
async def engine_control(
    simulation_id: str,
    body: EngineControlRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> EngineControlResponse:
    """Adjust SLM/LLM ratio at runtime (simulation must be PAUSED).
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idengine-control
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(state, SimulationStatus.PAUSED)

    controller = EngineController()
    dist = controller.compute_tier_distribution(
        total_agents=len(state.agents),
        slm_llm_ratio=body.slm_llm_ratio,
        budget_usd=body.budget_usd,
    )
    impact = controller.get_impact_assessment(dist)

    from app.api.schemas import ImpactAssessment, TierDistribution as ApiTierDistribution
    return EngineControlResponse(
        tier_distribution=ApiTierDistribution(
            tier1_count=dist.tier1_count,
            tier2_count=dist.tier2_count,
            tier3_count=dist.tier3_count,
            estimated_cost_per_step=dist.estimated_cost_per_step,
            estimated_latency_ms=dist.estimated_latency_ms,
        ),
        impact_assessment=ImpactAssessment(
            cost_efficiency=impact.cost_efficiency,
            reasoning_depth=impact.reasoning_depth,
            simulation_velocity=impact.simulation_velocity,
            prediction_type=impact.prediction_type,
        ),
    )


@router.post("/recommend-engine", response_model=RecommendEngineResponse)
async def recommend_engine(
    body: RecommendEngineRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> RecommendEngineResponse:
    """Budget-based auto engine recommendation.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationsrecommend-engine
    """
    # Fallback heuristic
    ratio = min(1.0, body.budget_usd / (body.agent_count * body.max_steps * 0.001))
    return RecommendEngineResponse(
        recommended_ratio=round(ratio, 2),
        recommended_slm_model="gemma2:2b" if ratio < 0.3 else "phi4",
        tier_distribution={
            "tier1_count": int(body.agent_count * (1 - ratio)),
            "tier2_count": int(body.agent_count * ratio * 0.8),
            "tier3_count": int(body.agent_count * ratio * 0.2),
        },
        estimated_total_cost=round(body.budget_usd * 0.9, 2),
        estimated_total_time="N/A",
        mode="SLM 모드" if ratio < 0.3 else "Hybrid",
    )


# ---- Group Chat & Interview (G6, G8) ----

_group_chat_managers: dict[str, GroupChatManager] = {}
_interviewer = AgentInterviewer()


def _get_group_chat_manager(simulation_id: str) -> GroupChatManager:
    if simulation_id not in _group_chat_managers:
        _group_chat_managers[simulation_id] = GroupChatManager()
    return _group_chat_managers[simulation_id]


@router.post("/{simulation_id}/group-chat", status_code=201)
async def create_group_chat(
    simulation_id: str,
    body: dict,
    orchestrator: Any = Depends(get_orchestrator),
) -> dict:
    """Create a group chat session within a simulation.
    SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#group-chat-action
    """
    _get_state_or_404(orchestrator, simulation_id)
    mgr = _get_group_chat_manager(simulation_id)

    member_ids = [UUID(m) for m in body.get("members", [])]
    topic = body.get("topic", "")
    chat = mgr.create_group(members=member_ids, topic=topic)

    return {
        "group_id": str(chat.group_id),
        "topic": chat.topic,
        "member_count": chat.member_count,
    }


@router.get("/{simulation_id}/group-chat/{group_id}")
async def get_group_chat(
    simulation_id: str,
    group_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> dict:
    """Get group chat details and messages.
    SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#group-chat-action
    """
    _get_state_or_404(orchestrator, simulation_id)
    mgr = _get_group_chat_manager(simulation_id)
    try:
        chat = mgr.get_group(UUID(group_id))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found")

    return {
        "group_id": str(chat.group_id),
        "topic": chat.topic,
        "member_count": chat.member_count,
        "message_count": chat.message_count,
        "messages": [
            {
                "agent_id": str(m.agent_id),
                "content": m.content,
                "step": m.step,
                "sentiment": m.sentiment,
            }
            for m in chat.get_messages()
        ],
    }


@router.post("/{simulation_id}/group-chat/{group_id}/message", status_code=201)
async def add_group_chat_message(
    simulation_id: str,
    group_id: str,
    body: dict,
    orchestrator: Any = Depends(get_orchestrator),
) -> dict:
    """Add a message to a group chat.
    SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#group-chat-action
    """
    _get_state_or_404(orchestrator, simulation_id)
    mgr = _get_group_chat_manager(simulation_id)
    try:
        msg = mgr.add_message(
            group_id=UUID(group_id),
            agent_id=UUID(body["agent_id"]),
            content=body["content"],
            step=body.get("step", 0),
            sentiment=body.get("sentiment", 0.0),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "agent_id": str(msg.agent_id),
        "content": msg.content,
        "step": msg.step,
        "sentiment": msg.sentiment,
    }


@router.post("/{simulation_id}/agents/{agent_id}/interview")
async def interview_agent(
    simulation_id: str,
    agent_id: str,
    body: dict,
    orchestrator: Any = Depends(get_orchestrator),
) -> dict:
    """Interview an agent about their current state.
    SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#interview-action
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    target_uuid = UUID(agent_id)

    # Find the agent in the simulation
    agent_state = None
    for a in state.agents:
        if a.agent_id == target_uuid:
            agent_state = a
            break

    if agent_state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_id} not found in simulation {simulation_id}",
        )

    question = body.get("question", "What do you think?")
    result = _interviewer.interview(agent_state, question)

    return {
        "agent_id": str(result.agent_id),
        "question": result.question,
        "answer": result.answer,
        "belief": result.belief,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
    }


# ---- Export (G9) ----

@router.get("/{simulation_id}/export")
async def export_simulation(
    simulation_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
    orchestrator: Any = Depends(get_orchestrator),
) -> StreamingResponse:
    """Export simulation results as JSON or CSV download.
    SPEC: docs/spec/06_API_SPEC.md#simulation-endpoints
    """
    state = _get_state_or_404(orchestrator, simulation_id)

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "step", "adoption_rate", "mean_sentiment", "diffusion_rate",
            "sentiment_variance", "llm_calls",
        ])
        for step in state.step_history:
            writer.writerow([
                step.step,
                step.adoption_rate,
                step.mean_sentiment,
                step.diffusion_rate,
                step.sentiment_variance,
                step.llm_calls_this_step,
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=simulation_{simulation_id}.csv"
            },
        )
    else:
        data = {
            "simulation_id": str(state.simulation_id),
            "config": {
                "name": state.config.name,
                "max_steps": state.config.max_steps,
            },
            "status": state.status,
            "current_step": state.current_step,
            "total_agents": len(state.agents),
            "steps": [
                {
                    "step": s.step,
                    "adoption_rate": s.adoption_rate,
                    "mean_sentiment": s.mean_sentiment,
                    "diffusion_rate": s.diffusion_rate,
                    "total_adoption": s.total_adoption,
                }
                for s in state.step_history
            ],
        }
        content = json.dumps(data, indent=2, default=str)
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=simulation_{simulation_id}.json"
            },
        )
