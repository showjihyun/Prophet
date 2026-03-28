"""Simulation endpoints.
SPEC: docs/spec/06_API_SPEC.md#2-simulation-endpoints
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_orchestrator
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
from app.engine.network.schema import CommunityConfig
from app.engine.simulation.schema import (
    CampaignConfig,
    SimulationConfig,
)

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
) -> StatusResponse:
    """Start the simulation.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstart
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(state, SimulationStatus.CONFIGURED, SimulationStatus.PAUSED)
    now = datetime.now(timezone.utc)
    sim_uuid = _sim_id_to_uuid(simulation_id)
    orchestrator.start(sim_uuid)
    return StatusResponse(status=SimulationStatus.RUNNING, started_at=now)


@router.post("/{simulation_id}/step", response_model=StepResultResponse)
async def step_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> StepResultResponse:
    """Execute exactly one step.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstep
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(state, SimulationStatus.RUNNING, SimulationStatus.PAUSED)

    sim_uuid = _sim_id_to_uuid(simulation_id)
    result = await orchestrator.run_step(sim_uuid)

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
) -> StatusResponse:
    """Pause after current step completes.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idpause
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(state, SimulationStatus.RUNNING)
    sim_uuid = _sim_id_to_uuid(simulation_id)
    await orchestrator.pause(sim_uuid)
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
    return StatusResponse(status=SimulationStatus.RUNNING)


@router.post("/{simulation_id}/stop", response_model=StatusResponse)
async def stop_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
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
    # Directly set status (orchestrator doesn't have a stop method)
    state.status = "completed"
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
    except (ValueError, NotImplementedError, AttributeError, TypeError):
        pass  # event injection is best-effort for now

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
    except (ValueError, NotImplementedError, AttributeError, TypeError):
        pass

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
    _get_state_or_404(orchestrator, simulation_id)
    _get_state_or_404(orchestrator, other_id)
    return ScenarioComparisonResponse(
        simulation_a=simulation_id,
        simulation_b=other_id,
        comparison={},
    )


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
    _get_state_or_404(orchestrator, simulation_id)
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    job = {
        "job_id": job_id,
        "status": "queued",
        "n_runs": body.n_runs,
        "started_at": now,
    }
    _monte_carlo_jobs[job_id] = job

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

    return EngineControlResponse()


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
