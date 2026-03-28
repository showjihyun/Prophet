"""Simulation endpoints.
SPEC: docs/spec/06_API_SPEC.md#2-simulation-endpoints
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

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

router = APIRouter(prefix="/api/v1/simulations", tags=["simulations"])

# ---- In-memory store (Phase 6 placeholder until DB is wired) ----
_simulations: dict[str, dict[str, Any]] = {}
_monte_carlo_jobs: dict[str, dict[str, Any]] = {}


def _get_sim_or_404(simulation_id: str) -> dict[str, Any]:
    """Retrieve a simulation dict or raise 404."""
    sim = _simulations.get(simulation_id)
    if sim is None:
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
    return sim


def _require_status(sim: dict[str, Any], *allowed: SimulationStatus) -> None:
    """Raise 409 if simulation is not in one of the allowed statuses."""
    current = SimulationStatus(sim["status"])
    if current not in allowed:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                type="https://prophet.io/errors/simulation-running",
                title="Action Not Allowed",
                status=409,
                detail=f"Simulation is '{current.value}', expected one of {[s.value for s in allowed]}",
                instance=f"/api/v1/simulations/{sim['simulation_id']}",
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
    sim_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    sim = {
        "simulation_id": sim_id,
        "name": body.name,
        "description": body.description,
        "status": SimulationStatus.CONFIGURED.value,
        "current_step": 0,
        "max_steps": body.max_steps,
        "total_agents": 1000,  # default until orchestrator wires up
        "network_metrics": {"clustering_coefficient": 0.0, "avg_path_length": 0.0},
        "config": body.model_dump(),
        "created_at": now,
        "steps": [],
        "events": [],
    }

    # Try to delegate to real orchestrator
    try:
        result = orchestrator.create(body.model_dump())
        if isinstance(result, dict):
            sim.update({k: v for k, v in result.items() if k in sim})
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass  # use defaults above

    _simulations[sim_id] = sim

    return SimulationResponse(
        simulation_id=sim_id,
        status=SimulationStatus(sim["status"]),
        total_agents=sim["total_agents"],
        network_metrics=sim["network_metrics"],
        created_at=sim["created_at"],
    )


@router.get("/", response_model=PaginatedResponse)
async def list_simulations(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PaginatedResponse:
    """List all simulation runs.
    SPEC: docs/spec/06_API_SPEC.md#get-simulations
    """
    items = list(_simulations.values())
    if status is not None:
        items = [s for s in items if s["status"] == status]
    total = len(items)
    items = items[offset: offset + limit]
    return PaginatedResponse(items=items, total=total)


@router.get("/{simulation_id}", response_model=SimulationDetailResponse)
async def get_simulation(simulation_id: str) -> SimulationDetailResponse:
    """Get simulation details.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_id
    """
    sim = _get_sim_or_404(simulation_id)
    return SimulationDetailResponse(
        simulation_id=sim["simulation_id"],
        name=sim["name"],
        description=sim.get("description", ""),
        status=SimulationStatus(sim["status"]),
        current_step=sim["current_step"],
        max_steps=sim["max_steps"],
        total_agents=sim["total_agents"],
        network_metrics=sim["network_metrics"],
        config=sim.get("config", {}),
        created_at=sim["created_at"],
    )


@router.post("/{simulation_id}/start", response_model=StatusResponse)
async def start_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> StatusResponse:
    """Start the simulation.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstart
    """
    sim = _get_sim_or_404(simulation_id)
    _require_status(sim, SimulationStatus.CONFIGURED, SimulationStatus.PAUSED)
    now = datetime.now(timezone.utc)
    sim["status"] = SimulationStatus.RUNNING.value
    sim["started_at"] = now
    try:
        orchestrator.start(simulation_id)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass
    return StatusResponse(status=SimulationStatus.RUNNING, started_at=now)


@router.post("/{simulation_id}/step", response_model=StepResultResponse)
async def step_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> StepResultResponse:
    """Execute exactly one step.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstep
    """
    sim = _get_sim_or_404(simulation_id)
    _require_status(sim, SimulationStatus.RUNNING, SimulationStatus.PAUSED)

    try:
        result = orchestrator.step(simulation_id)
        if isinstance(result, dict):
            sim["current_step"] = result.get("step", sim["current_step"] + 1)
            sim["steps"].append(result)
            return StepResultResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    # Fallback: increment step with dummy data
    sim["current_step"] += 1
    step_data = StepResultResponse(
        step=sim["current_step"],
        adoption_rate=0.0,
        mean_sentiment=0.0,
        diffusion_rate=0,
        emergent_events=[],
    )
    sim["steps"].append(step_data.model_dump())
    return step_data


@router.post("/{simulation_id}/pause", response_model=StatusResponse)
async def pause_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> StatusResponse:
    """Pause after current step completes.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idpause
    """
    sim = _get_sim_or_404(simulation_id)
    _require_status(sim, SimulationStatus.RUNNING)
    sim["status"] = SimulationStatus.PAUSED.value
    try:
        await orchestrator.pause(simulation_id)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass
    return StatusResponse(
        status=SimulationStatus.PAUSED, current_step=sim["current_step"]
    )


@router.post("/{simulation_id}/resume", response_model=StatusResponse)
async def resume_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> StatusResponse:
    """Resume from paused state.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idresume
    """
    sim = _get_sim_or_404(simulation_id)
    _require_status(sim, SimulationStatus.PAUSED)
    sim["status"] = SimulationStatus.RUNNING.value
    try:
        await orchestrator.resume(simulation_id)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass
    return StatusResponse(status=SimulationStatus.RUNNING)


@router.post("/{simulation_id}/stop", response_model=StatusResponse)
async def stop_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> StatusResponse:
    """Stop and mark as completed.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstop
    """
    sim = _get_sim_or_404(simulation_id)
    _require_status(
        sim,
        SimulationStatus.RUNNING,
        SimulationStatus.PAUSED,
        SimulationStatus.CONFIGURED,
    )
    sim["status"] = SimulationStatus.COMPLETED.value
    try:
        orchestrator.stop(simulation_id)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass
    return StatusResponse(status=SimulationStatus.COMPLETED)


@router.get("/{simulation_id}/steps", response_model=StepHistoryResponse)
async def get_steps(
    simulation_id: str,
    from_step: int | None = Query(None, ge=0),
    to_step: int | None = Query(None, ge=0),
    metrics: str | None = Query(None),
) -> StepHistoryResponse:
    """Get step history.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idsteps
    """
    sim = _get_sim_or_404(simulation_id)
    steps = sim.get("steps", [])
    if from_step is not None:
        steps = [s for s in steps if s.get("step", 0) >= from_step]
    if to_step is not None:
        steps = [s for s in steps if s.get("step", 0) <= to_step]
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
    sim = _get_sim_or_404(simulation_id)
    _require_status(sim, SimulationStatus.RUNNING, SimulationStatus.PAUSED)

    event_id = str(uuid.uuid4())
    effective_step = sim["current_step"] + 1
    sim["events"].append({
        "event_id": event_id,
        "effective_step": effective_step,
        **body.model_dump(),
    })

    try:
        orchestrator.inject_event(simulation_id, body.model_dump())
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

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
    _get_sim_or_404(simulation_id)
    replay_id = str(uuid.uuid4())

    try:
        orchestrator.replay(simulation_id, step)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    return ReplayResponse(replay_id=replay_id, from_step=step)


@router.get(
    "/{simulation_id}/compare/{other_id}",
    response_model=ScenarioComparisonResponse,
)
async def compare_simulations(
    simulation_id: str,
    other_id: str,
) -> ScenarioComparisonResponse:
    """Compare two simulation runs.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idcompareother_simulation_id
    """
    _get_sim_or_404(simulation_id)
    _get_sim_or_404(other_id)
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
    _get_sim_or_404(simulation_id)
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    job = {
        "job_id": job_id,
        "status": "queued",
        "n_runs": body.n_runs,
        "started_at": now,
    }
    _monte_carlo_jobs[job_id] = job

    try:
        orchestrator.start_monte_carlo(simulation_id, body.model_dump())
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

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
) -> MonteCarloStatusResponse:
    """Get Monte Carlo job status and results.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idmonte-carlojob_id
    """
    _get_sim_or_404(simulation_id)
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
    sim = _get_sim_or_404(simulation_id)
    _require_status(sim, SimulationStatus.PAUSED)

    try:
        result = orchestrator.engine_control(simulation_id, body.model_dump())
        if isinstance(result, dict):
            return EngineControlResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    return EngineControlResponse()


@router.post("/recommend-engine", response_model=RecommendEngineResponse)
async def recommend_engine(
    body: RecommendEngineRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> RecommendEngineResponse:
    """Budget-based auto engine recommendation.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationsrecommend-engine
    """
    try:
        result = orchestrator.recommend_engine(body.model_dump())
        if isinstance(result, dict):
            return RecommendEngineResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

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
