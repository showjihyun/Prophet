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

from app.api.deps import (
    get_orchestrator,
    get_session,
    get_simulation_repo,
    get_simulation_service,
)
from app.api.ws import manager as ws_manager
from app.repositories.protocols import SimulationRepository
from app.services.simulation_service import SimulationService
from app.engine.simulation.exceptions import (
    InvalidStateError,
    InvalidStateTransitionError,
    SimulationCapacityError,
    StepNotFoundError,
)
from app.api.schemas import (
    CreateSimulationRequest,
    EngineControlRequest,
    EngineControlResponse,
    ErrorResponse,
    InjectEventRequest,
    InjectEventResponse,
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
from app.engine.simulation.schema import StepResult
from app.llm.engine_control import EngineController
from app.services.ports import SimulationNotFoundError, StopOutcome

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/simulations", tags=["simulations"])


def _fire_and_forget(coro, *, label: str = "ws_broadcast") -> asyncio.Task:
    """Create a background task with error logging.

    Prevents silent failures in fire-and-forget async tasks (H4).
    """
    task = asyncio.create_task(coro)

    def _log_exc(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            logger.error("Background task '%s' failed: %s", label, exc)

    task.add_done_callback(_log_exc)
    return task

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
    """Retrieve SimulationState from orchestrator or raise 404.

    Used by agents.py, communities.py, llm_dashboard.py, network.py
    for read-only GET endpoints that don't go through the service layer.
    Simulation-mutating POST routes should use ``_svc_state_or_404``
    instead so they depend only on ``SimulationService``.
    """
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


def _svc_state_or_404(service: SimulationService, simulation_id: str) -> Any:
    """Retrieve SimulationState via the service layer or raise 404.

    SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#3.1

    Clean Architecture version of ``_get_state_or_404``: the caller
    depends on ``SimulationService`` only, never on the raw
    ``SimulationOrchestrator``. Used by the 5 mutation routes
    (start/step/pause/resume/stop) after the Round 8-8 refactor.
    """
    sim_uuid = _sim_id_to_uuid(simulation_id)
    try:
        return service.get_state(sim_uuid)
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
    session: AsyncSession = Depends(get_session),
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationResponse:
    """Create a new simulation run.
    SPEC: docs/spec/06_API_SPEC.md#post-simulations
    """
    state = await service.create(body, session=session)

    # Network metrics are computed lazily via GET /network/metrics — avoid
    # running O(n^2) NetworkX algorithms on the create hot path.
    net_metrics = {"clustering_coefficient": 0.0, "avg_path_length": 0.0}

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
    repo: SimulationRepository = Depends(get_simulation_repo),
) -> PaginatedResponse:
    """List all simulation runs.
    SPEC: docs/spec/06_API_SPEC.md#get-simulations
    """
    # Build a dict of in-memory simulations (live, takes precedence).
    # ``list_states`` returns a snapshot — safe against concurrent mutation.
    mem_items: dict[str, dict] = {}
    for state in orchestrator.list_states(status=status):
        mem_items[str(state.simulation_id)] = {
            "simulation_id": str(state.simulation_id),
            "name": state.config.name,
            "status": state.status,
            "current_step": state.current_step,
            "total_agents": len(state.agents),
        }

    # Pull a windowed slice from DB with SQL-side filter/limit.
    # Fetch a bit extra to absorb in-memory overrides that collide by id.
    db_limit = limit + offset + len(mem_items)
    db_sims = await repo.list_all(
        status=status, limit=db_limit, offset=0, session=session,
    )
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
    # Total = DB count (SQL) + in-memory-only rows not present in DB.
    db_total = await repo.count(status=status, session=session)
    db_ids = {s["simulation_id"] for s in db_sims}
    mem_only = sum(1 for sid in mem_items if sid not in db_ids)
    total = db_total + mem_only
    items = items[offset: offset + limit]
    return PaginatedResponse(items=items, total=total)


@router.get("/{simulation_id}", response_model=SimulationDetailResponse)
async def get_simulation(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
    session: AsyncSession = Depends(get_session),
    repo: SimulationRepository = Depends(get_simulation_repo),
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
        pass  # simulation not in memory — fall through to DB lookup

    # Fallback: point-lookup from DB (read-only, completed/historical sims)
    db_sim = await repo.find_by_id(sim_uuid, session=session)
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
    session: AsyncSession = Depends(get_session),
    service: SimulationService = Depends(get_simulation_service),
) -> StatusResponse:
    """Start the simulation.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstart
    """
    state = _svc_state_or_404(service, simulation_id)
    _require_status(state, SimulationStatus.CONFIGURED, SimulationStatus.PAUSED)
    now = datetime.now(timezone.utc)
    await service.start(_sim_id_to_uuid(simulation_id), session=session)
    return StatusResponse(status=SimulationStatus.RUNNING, started_at=now)


@router.post("/{simulation_id}/step", response_model=StepResultResponse)
async def step_simulation(
    simulation_id: str,
    session: AsyncSession = Depends(get_session),
    service: SimulationService = Depends(get_simulation_service),
) -> StepResultResponse:
    """Execute exactly one step.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstep
    """
    state = _svc_state_or_404(service, simulation_id)
    _require_status(state, SimulationStatus.RUNNING, SimulationStatus.PAUSED)

    sim_uuid = _sim_id_to_uuid(simulation_id)
    try:
        result = await service.step(sim_uuid, session=session)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                type="https://prophet.io/errors/step-failed",
                title="Step Failed",
                status=500,
                detail=f"Simulation step crashed: {exc}",
                instance=f"/api/v1/simulations/{simulation_id}/step",
            ).model_dump(),
        ) from exc

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
        propagation_pairs=result.propagation_pairs,
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
    service: SimulationService = Depends(get_simulation_service),
) -> RunAllResponse:
    """Run all remaining steps to completion and return a report.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idrun-all
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    _require_status(state, SimulationStatus.CONFIGURED, SimulationStatus.RUNNING)
    sim_uuid = _sim_id_to_uuid(simulation_id)

    try:
        report = await service.run_all(sim_uuid, session=session)
    except SimulationCapacityError as exc:
        raise HTTPException(
            status_code=429,
            detail=ErrorResponse(
                type="https://prophet.io/errors/capacity-exceeded",
                title="Simulation Capacity Exceeded",
                status=429,
                detail=str(exc),
                instance=f"/api/v1/simulations/{simulation_id}/run-all",
            ).model_dump(),
        )
    except (InvalidStateError, InvalidStateTransitionError, ValueError) as exc:
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
    except Exception as exc:
        logger.error("run_all failed for %s: %s", simulation_id, exc)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                type="https://prophet.io/errors/internal",
                title="Simulation Execution Failed",
                status=500,
                detail=str(exc),
                instance=f"/api/v1/simulations/{simulation_id}/run-all",
            ).model_dump(),
        )

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
    session: AsyncSession = Depends(get_session),
    service: SimulationService = Depends(get_simulation_service),
) -> StatusResponse:
    """Pause after current step completes.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idpause
    """
    state = _svc_state_or_404(service, simulation_id)
    _require_status(state, SimulationStatus.RUNNING)
    await service.pause(_sim_id_to_uuid(simulation_id), session=session)
    return StatusResponse(
        status=SimulationStatus.PAUSED, current_step=state.current_step,
    )


@router.post("/{simulation_id}/resume", response_model=StatusResponse)
async def resume_simulation(
    simulation_id: str,
    session: AsyncSession = Depends(get_session),
    service: SimulationService = Depends(get_simulation_service),
) -> StatusResponse:
    """Resume from paused state.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idresume
    """
    state = _svc_state_or_404(service, simulation_id)
    _require_status(state, SimulationStatus.PAUSED)
    await service.resume(_sim_id_to_uuid(simulation_id), session=session)
    return StatusResponse(status=SimulationStatus.RUNNING)


@router.post("/{simulation_id}/stop", response_model=StatusResponse)
async def stop_simulation(
    simulation_id: str,
    session: AsyncSession = Depends(get_session),
    service: SimulationService = Depends(get_simulation_service),
) -> StatusResponse:
    """Stop and mark as completed.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstop
    """
    sim_uuid = _sim_id_to_uuid(simulation_id)

    # Validate status transition if sim is in memory — preserve 409 behavior
    # for unexpected states. DB-only sims skip this check.
    try:
        state = service.get_state(sim_uuid)
    except (ValueError, KeyError):
        state = None

    if state is not None:
        _require_status(
            state,
            SimulationStatus.RUNNING,
            SimulationStatus.PAUSED,
            SimulationStatus.CONFIGURED,
            SimulationStatus.FAILED,
            SimulationStatus.COMPLETED,
        )

    try:
        outcome = await service.stop(sim_uuid, session=session)
    except SimulationNotFoundError:
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

    if outcome is StopOutcome.RESET:
        return StatusResponse(status=SimulationStatus.CREATED)
    return StatusResponse(status=SimulationStatus.COMPLETED)


@router.get("/{simulation_id}/steps", response_model=StepHistoryResponse)
async def get_steps(
    simulation_id: str,
    from_step: int | None = Query(None, ge=0),
    to_step: int | None = Query(None, ge=0),
    metrics: str | None = Query(None),
    orchestrator: Any = Depends(get_orchestrator),
    session: AsyncSession = Depends(get_session),
    repo: SimulationRepository = Depends(get_simulation_repo),
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
                propagation_pairs=getattr(sr, 'propagation_pairs', []),
                llm_calls_this_step=sr.llm_calls_this_step,
                step_duration_ms=sr.step_duration_ms,
                emergent_events=[
                    {"type": e.event_type, "step": e.step, "community_id": str(e.community_id) if e.community_id else None}
                    for e in sr.emergent_events
                ] if sr.emergent_events else [],
            ))
    else:
        # Fallback: load from DB (completed/historical sims not in memory)
        db_steps = await repo.load_steps(sim_uuid, session=session)
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
        await orchestrator.inject_event(
            sim_uuid,
            event_type=body.event_type,
            payload={"content": body.content, "controversy": body.controversy},
            target_communities=body.target_communities or None,
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
    sim_uuid = _sim_id_to_uuid(simulation_id)
    try:
        result = await orchestrator.replay_step(sim_uuid, step)
    except (ValueError, StepNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Real failure — surface it as a 500 so the UI can tell the user
        # the replay did NOT happen. Previously this returned a fake
        # replay_id + the requested step, making the frontend believe the
        # branch succeeded when nothing had been created.
        import logging
        logging.getLogger(__name__).exception("replay_step failed for %s", simulation_id)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                type="https://prophet.io/errors/replay-failed",
                title="Replay Failed",
                status=500,
                detail=f"Simulation replay from step {step} failed: {e}",
                instance=f"/api/v1/simulations/{simulation_id}/replay/{step}",
            ).model_dump(),
        ) from e

    return ReplayResponse(
        replay_id=result["replay_id"],
        from_step=result["from_step"],
    )


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
    # Validate UUIDs first — invalid IDs should always 404.
    _sim_id_to_uuid(simulation_id)
    _sim_id_to_uuid(other_id)
    # Historical sims (DB-only after restart) have no in-memory step_history.
    # Return an empty comparison rather than 404.
    try:
        state_a = _get_state_or_404(orchestrator, simulation_id)
        state_b = _get_state_or_404(orchestrator, other_id)
    except HTTPException as e:
        if e.status_code != 404:
            raise
        return ScenarioComparisonResponse(
            simulation_a=simulation_id,
            simulation_b=other_id,
            comparison={},
        )

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

        # Per-step metric diffs (align by step index)
        max_steps = max(len(state_a.step_history), len(state_b.step_history))
        metric_diffs: dict[str, list[float]] = {
            "adoption_rate": [],
            "mean_sentiment": [],
            "diffusion_rate": [],
        }
        for i in range(max_steps):
            a = state_a.step_history[i] if i < len(state_a.step_history) else None
            b = state_b.step_history[i] if i < len(state_b.step_history) else None
            metric_diffs["adoption_rate"].append(
                (a.adoption_rate if a else 0.0) - (b.adoption_rate if b else 0.0)
            )
            metric_diffs["mean_sentiment"].append(
                (a.mean_sentiment if a else 0.0) - (b.mean_sentiment if b else 0.0)
            )
            metric_diffs["diffusion_rate"].append(
                (a.diffusion_rate if a else 0) - (b.diffusion_rate if b else 0)
            )
        comparison["metric_diffs"] = metric_diffs

    return ScenarioComparisonResponse(
        simulation_a=simulation_id,
        simulation_b=other_id,
        comparison=comparison,
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
        tier1_model=body.slm_model,
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
    # Use EngineController for consistent tier calculation
    ratio = min(1.0, body.budget_usd / (body.agent_count * body.max_steps * 0.001))
    ratio = round(max(0.0, min(1.0, ratio)), 2)

    controller = EngineController()
    dist = controller.compute_tier_distribution(
        total_agents=body.agent_count,
        slm_llm_ratio=ratio,
        budget_usd=body.budget_usd,
    )

    estimated_total_cost = round(dist.estimated_cost_per_step * body.max_steps, 2)
    estimated_time_ms = dist.estimated_latency_ms * body.max_steps
    if estimated_time_ms < 60_000:
        estimated_total_time = f"~{estimated_time_ms / 1000:.0f}s"
    else:
        estimated_total_time = f"~{estimated_time_ms / 60_000:.0f}min"

    mode = "Speed" if ratio < 0.3 else "Quality" if ratio > 0.7 else "Balanced"

    from app.api.schemas import TierDistribution as ApiTierDistribution
    return RecommendEngineResponse(
        recommended_ratio=ratio,
        recommended_slm_model=dist.tier1_model,
        tier_distribution=ApiTierDistribution(
            tier1_count=dist.tier1_count,
            tier2_count=dist.tier2_count,
            tier3_count=dist.tier3_count,
            estimated_cost_per_step=dist.estimated_cost_per_step,
            estimated_latency_ms=dist.estimated_latency_ms,
        ),
        estimated_total_cost=estimated_total_cost,
        estimated_total_time=estimated_total_time,
        mode=mode,
    )


# ---- Group Chat & Interview (G6, G8) ----

_group_chat_managers: dict[str, GroupChatManager] = {}
_interviewer: AgentInterviewer | None = None


def _get_interviewer() -> AgentInterviewer:
    """Lazy-init interviewer with LLM gateway from orchestrator."""
    global _interviewer
    if _interviewer is None:
        try:
            orch = get_orchestrator()
            _interviewer = AgentInterviewer(
                gateway=getattr(orch, '_gateway', None),
                llm_adapter=getattr(orch, '_llm_adapter', None),
            )
        except Exception:
            _interviewer = AgentInterviewer()
    return _interviewer


def _get_group_chat_manager(simulation_id: str) -> GroupChatManager:
    if simulation_id not in _group_chat_managers:
        try:
            orch = get_orchestrator()
            _group_chat_managers[simulation_id] = GroupChatManager(
                gateway=getattr(orch, '_gateway', None),
                llm_adapter=getattr(orch, '_llm_adapter', None),
            )
        except Exception:
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
    interviewer = _get_interviewer()
    # Use async LLM interview when gateway is available, fallback to rule-based
    try:
        result = await interviewer.interview_async(agent_state, question)
    except Exception:
        result = interviewer.interview(agent_state, question)

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
    session: AsyncSession = Depends(get_session),
    repo: SimulationRepository = Depends(get_simulation_repo),
) -> StreamingResponse:
    """Export simulation results as JSON or CSV download.
    SPEC: docs/spec/06_API_SPEC.md#simulation-endpoints
    """
    sim_uuid = _sim_id_to_uuid(simulation_id)

    # Try in-memory first, fall back to DB for historical sims.
    step_rows: list[dict[str, Any]] = []
    sim_name = simulation_id
    sim_status = "unknown"
    sim_step = 0
    sim_max_steps = 0
    total_agents = 0
    try:
        state = orchestrator.get_state(sim_uuid)
        sim_name = state.config.name
        sim_status = state.status
        sim_step = state.current_step
        sim_max_steps = state.config.max_steps
        total_agents = len(state.agents)
        for s in state.step_history:
            step_rows.append({
                "step": s.step,
                "adoption_rate": s.adoption_rate,
                "mean_sentiment": s.mean_sentiment,
                "diffusion_rate": s.diffusion_rate,
                "sentiment_variance": s.sentiment_variance,
                "total_adoption": s.total_adoption,
                "llm_calls_this_step": s.llm_calls_this_step,
            })
    except (ValueError, KeyError):
        # Historical sim — load from DB
        db_sim = await repo.find_by_id(sim_uuid, session=session)
        if db_sim:
            sim_name = db_sim.get("name", simulation_id)
            sim_status = db_sim.get("status", "completed")
            sim_step = db_sim.get("current_step", 0)
            sim_max_steps = db_sim.get("max_steps", 0)
        db_steps = await repo.load_steps(sim_uuid, session=session)
        for sr in db_steps:
            step_rows.append({
                "step": sr.get("step", 0),
                "adoption_rate": sr.get("adoption_rate", 0.0),
                "mean_sentiment": sr.get("mean_sentiment", 0.0),
                "diffusion_rate": sr.get("diffusion_rate", 0.0),
                "sentiment_variance": sr.get("sentiment_variance", 0.0),
                "total_adoption": sr.get("total_adoption", 0),
                "llm_calls_this_step": sr.get("llm_calls_this_step", 0),
            })

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "step", "adoption_rate", "mean_sentiment", "diffusion_rate",
            "sentiment_variance", "llm_calls",
        ])
        for row in step_rows:
            writer.writerow([
                row["step"], row["adoption_rate"], row["mean_sentiment"],
                row["diffusion_rate"], row["sentiment_variance"],
                row["llm_calls_this_step"],
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
            "simulation_id": simulation_id,
            "config": {"name": sim_name, "max_steps": sim_max_steps},
            "status": sim_status,
            "current_step": sim_step,
            "total_agents": total_agents,
            "steps": [
                {
                    "step": r["step"],
                    "adoption_rate": r["adoption_rate"],
                    "mean_sentiment": r["mean_sentiment"],
                    "diffusion_rate": r["diffusion_rate"],
                    "total_adoption": r["total_adoption"],
                }
                for r in step_rows
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
