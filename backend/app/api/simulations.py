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
    for attr in ("community_id", "adoption_rate", "mean_belief", "sentiment_variance",
                 "active_agents", "dominant_action"):
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
    )

    state = orchestrator.create_simulation(config)

    # Persist to DB (fire-and-forget, does not block response)
    edges = list(state.network.graph.edges(data=True)) if state.network else []
    await persist.persist_creation(session, state.simulation_id, config, state.agents, edges)

    return SimulationResponse(
        simulation_id=str(state.simulation_id),
        status=SimulationStatus(state.status),
        total_agents=len(state.agents),
        network_metrics={
            "clustering_coefficient": 0.0,
            "avg_path_length": 0.0,
        },
        created_at=datetime.now(timezone.utc),
    )


@router.get("/", response_model=PaginatedResponse)
async def list_simulations(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    orchestrator: Any = Depends(get_orchestrator),
) -> PaginatedResponse:
    """List all simulation runs.
    SPEC: docs/spec/06_API_SPEC.md#get-simulations
    """
    all_sims = orchestrator._simulations.values()
    items = []
    for state in all_sims:
        item = {
            "simulation_id": str(state.simulation_id),
            "name": state.config.name,
            "status": state.status,
            "current_step": state.current_step,
            "total_agents": len(state.agents),
        }
        if status is not None and item["status"] != status:
            continue
        items.append(item)

    total = len(items)
    items = items[offset: offset + limit]
    return PaginatedResponse(items=items, total=total)


@router.get("/{simulation_id}", response_model=SimulationDetailResponse)
async def get_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> SimulationDetailResponse:
    """Get simulation details.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_id
    """
    state = _get_state_or_404(orchestrator, simulation_id)
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

    # Persist step result + status update
    await persist.persist_step(session, sim_uuid, result)
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

    # Broadcast status change if simulation completed
    if state.status == "completed":
        asyncio.create_task(ws_manager.broadcast(str(sim_uuid), {
            "type": "status_change",
            "data": {"status": "completed"},
        }))

    return StepResultResponse(
        step=result.step,
        adoption_rate=result.adoption_rate,
        mean_sentiment=result.mean_sentiment,
        diffusion_rate=result.diffusion_rate,
        emergent_events=[],
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
) -> StepHistoryResponse:
    """Get step history.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idsteps
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    steps = []
    for sr in state.step_history:
        if from_step is not None and sr.step < from_step:
            continue
        if to_step is not None and sr.step > to_step:
            continue
        steps.append(StepResultResponse(
            step=sr.step,
            adoption_rate=sr.adoption_rate,
            mean_sentiment=sr.mean_sentiment,
            diffusion_rate=sr.diffusion_rate,
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
    except (ValueError, NotImplementedError, AttributeError, TypeError) as e:
        import logging
        logging.getLogger(__name__).warning(f"inject_event fallback: {e}")

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


async def _run_monte_carlo(job_id: str, config: Any, n_runs: int) -> None:
    """Background task to actually run Monte Carlo.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector
    """
    try:
        _monte_carlo_jobs[job_id]["status"] = "running"
        runner = MonteCarloRunner()
        result = await runner.run(config, n_runs=n_runs)
        _monte_carlo_jobs[job_id].update({
            "status": "completed",
            "viral_probability": result.viral_probability,
            "expected_reach": result.expected_reach,
            "p5_reach": result.p5_reach,
            "p50_reach": result.p50_reach,
            "p95_reach": result.p95_reach,
            "community_adoption": result.community_adoption,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        _monte_carlo_jobs[job_id].update({
            "status": "failed",
            "error_message": str(e),
        })


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
        "status": "queued",
        "n_runs": body.n_runs,
        "started_at": now,
    }
    _monte_carlo_jobs[job_id] = job

    # Fire background task using the simulation's config
    asyncio.create_task(_run_monte_carlo(job_id, state.config, body.n_runs))

    return MonteCarloStatusResponse(
        job_id=job_id,
        status="queued",
        n_runs=body.n_runs,
        started_at=now,
    )


@router.get(
    "/{simulation_id}/monte-carlo/{job_id}",
    response_model=MonteCarloStatusResponse,
)
async def get_monte_carlo_status(
    simulation_id: str,
    job_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> MonteCarloStatusResponse:
    """Get Monte Carlo job status and results.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idmonte-carlojob_id
    """
    _get_state_or_404(orchestrator, simulation_id)
    job = _monte_carlo_jobs.get(job_id)
    if job is None:
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
    return MonteCarloStatusResponse(**job)


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
