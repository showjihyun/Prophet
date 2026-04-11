"""Application Service for Simulation lifecycle management.

SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#3.1

Orchestrates domain logic (engine/orchestrator) + persistence (repository
protocol) + real-time notifications (notification port). API controllers
are thin adapters — they parse HTTP input, call this service, and map
domain exceptions (``SimulationNotFoundError``) to HTTP status codes.

Contract discipline:
  * The service depends on :class:`SimulationRepository` (Protocol), not
    on the concrete :class:`SqlSimulationRepository`.
  * The service depends on :class:`NotificationPort` (Protocol), not on
    :class:`app.api.ws.ConnectionManager` — the layer arrow points
    ``api → services``, never the reverse.
  * Input payloads are typed against :class:`CreateSimulationInput`
    Protocol so the concrete Pydantic request model can change without
    the service noticing — as long as the structural contract holds.
  * Return values are strict (``StopOutcome`` enum, ``StepResult``) —
    no sentinel dicts.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import AbstractAsyncContextManager
from typing import Any, Callable
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, settings as default_settings
from app.engine.network.schema import CommunityConfig
from app.engine.simulation.orchestrator import (
    SimulationOrchestrator,
    SimulationState,
)
from app.engine.simulation.schema import (
    CampaignConfig,
    SimulationConfig,
    StepResult,
)
from app.repositories.protocols import SimulationRepository
from app.services.ports import (
    CreateSimulationInput,
    NotificationPort,
    SimulationNotFoundError,
    StopOutcome,
)

logger = logging.getLogger(__name__)


# ---- Default communities used when the request omits them ----
_DEFAULT_COMMUNITIES: list[CommunityConfig] = [
    CommunityConfig(id="A", name="early_adopters", size=100, agent_type="early_adopter"),
    CommunityConfig(id="B", name="general_consumers", size=500, agent_type="consumer"),
    CommunityConfig(id="C", name="skeptics", size=200, agent_type="skeptic"),
    CommunityConfig(id="D", name="experts", size=30, agent_type="expert"),
    CommunityConfig(id="E", name="influencers", size=170, agent_type="influencer"),
]


SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]
"""Factory that opens a fresh DB session as an async context manager."""


def _fire_and_forget(coro: Any, *, label: str = "bg") -> asyncio.Task:
    """Background task with error logging."""
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
    """Convert CommunityStepMetrics to a plain dict."""
    if isinstance(metric, dict):
        return metric
    result: dict = {}
    for attr in (
        "community_id", "adoption_count", "adoption_rate", "mean_belief",
        "sentiment_variance", "active_agents", "dominant_action",
        "new_propagation_count",
    ):
        val = getattr(metric, attr, None)
        if val is not None:
            result[attr] = str(val) if attr == "community_id" else val
    return result


class SimulationService:
    """Application service — orchestrates create/start/step/pause/resume/stop.

    SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#3.1

    Constructor injects every external dependency through a Protocol or
    factory so the service is trivially testable without a real DB,
    websocket, or settings file.

    :param orchestrator: Domain orchestrator (engine layer).
    :param repo: Repository conforming to :class:`SimulationRepository`.
    :param notifier: Outbound notification port (WebSocket in prod, fake
        in tests).
    :param session_factory: Opens fresh DB sessions for fire-and-forget
        background tasks that outlive the request session.
    :param settings: Application settings (for LLM tier → provider mapping).
    """

    def __init__(
        self,
        orchestrator: SimulationOrchestrator,
        repo: SimulationRepository,
        notifier: NotificationPort,
        *,
        session_factory: SessionFactory | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._orch = orchestrator
        self._repo = repo
        self._notifier = notifier
        self._settings = settings or default_settings
        if session_factory is None:
            # Lazy import breaks a potential circular between services and
            # infrastructure; we still declare the fallback at construction
            # time rather than at call time.
            from app.database import async_session as _async_session
            session_factory = _async_session
        self._session_factory: SessionFactory = session_factory

    # ------------------------------------------------------------------ #
    # State helpers
    # ------------------------------------------------------------------ #

    def get_state(self, sim_id: UUID) -> SimulationState:
        """Get in-memory state; raises ``ValueError`` if not found."""
        return self._orch.get_state(sim_id)

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #

    async def create(
        self, body: CreateSimulationInput, *, session: AsyncSession,
    ) -> SimulationState:
        """Build config + orchestrate create + persist creation.

        SPEC: docs/spec/06_API_SPEC.md#post-simulations

        Communities default to the five-template profile when the input
        payload supplies none.
        """
        sim_id = uuid4()

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

        state = self._orch.create_simulation(config)

        # ``save_creation`` is strict — it re-raises on failure. If that
        # happens, the in-memory state is a ghost (no DB backing) and we
        # must evict it before propagating so the orchestrator doesn't
        # accumulate unreachable simulations on repeated failures.
        edges = list(state.network.graph.edges(data=True)) if state.network else []
        try:
            await self._repo.save_creation(
                state.simulation_id, config, state.agents, edges, session=session,
            )
        except Exception:
            logger.exception(
                "save_creation failed for %s — evicting ghost state",
                state.simulation_id,
            )
            try:
                await self._orch.delete_simulation(state.simulation_id)
            except KeyError:
                pass  # already gone
            raise
        return state

    # ------------------------------------------------------------------ #
    # Start
    # ------------------------------------------------------------------ #

    async def start(self, sim_id: UUID, *, session: AsyncSession) -> dict:
        """Transition simulation to RUNNING and persist.

        SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstart
        """
        await self._orch.start(sim_id)
        await self._repo.save_status(sim_id, "running", session=session)
        _fire_and_forget(
            self._notifier.broadcast(str(sim_id), {
                "type": "status_change",
                "data": {"status": "running"},
            }),
            label="ws_start",
        )
        return {"status": "running", "simulation_id": str(sim_id)}

    # ------------------------------------------------------------------ #
    # Step
    # ------------------------------------------------------------------ #

    async def step(self, sim_id: UUID, *, session: AsyncSession) -> StepResult:
        """Execute one simulation step with full side-effects.

        SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstep

        Side-effects (in order):
          1. Orchestrator runs step (domain)
          2. Persist step + status (awaited inline on the request session)
          3. Persist LLM call records (awaited inline, shares request session)
          4. Persist expert opinions / agent memories (fire-and-forget,
             each opens its own session via ``session_factory``)
          5. Broadcast step_result + emergent events + agent updates
          6. If simulation completed, broadcast status_change

        Re-raises the underlying orchestrator exception after persisting
        the failed status so the route layer can map it to HTTP 500.
        """
        state = self.get_state(sim_id)

        try:
            result = await self._orch.run_step(sim_id)
        except Exception:
            # Orchestrator flipped state to FAILED. Persist + broadcast so
            # the frontend switches to the recover UI instead of getting 409.
            await self._repo.save_status(
                sim_id, state.status, state.current_step, session=session,
            )
            _fire_and_forget(self._notifier.broadcast(str(sim_id), {
                "type": "status_change",
                "data": {"status": state.status},
            }), label="ws_step_failed")
            raise

        # Persist step + agent states
        await self._repo.save_step(
            sim_id, result, agents=state.agents, session=session,
        )
        await self._repo.save_status(
            sim_id, state.status, state.current_step, session=session,
        )

        # ---- LLM call records (tier distribution) -------------------- #
        # Awaited inline (not fire-and-forget) because it shares the
        # request session — a concurrent task on the same session would
        # raise "This session is provisioning a new connection".
        if getattr(result, "llm_calls_this_step", 0) > 0:
            llm_records = self._build_llm_records(result)
            if llm_records:
                await self._repo.persist_llm_calls(
                    sim_id, llm_records, session=session,
                )

        # ---- Expert opinions (fire-and-forget with own session) ------ #
        expert_events = [
            e for e in result.emergent_events
            if "expert" in (e.event_type or "").lower() and e.community_id is not None
        ]
        if expert_events:
            opinions = [
                {
                    "agent_id": e.community_id,
                    "opinion_text": e.description,
                    "score": (e.severity * 2) - 1,
                    "confidence": e.severity,
                    "step": result.step,
                }
                for e in expert_events
            ]
            _fire_and_forget(
                self._persist_expert_opinions_bg(sim_id, result.step, opinions),
                label="persist_expert_opinions",
            )

        # ---- Agent memories (fire-and-forget with own session) ------- #
        agent_memories = self._collect_agent_memories(state.agents, result.step)
        if agent_memories:
            _fire_and_forget(
                self._persist_agent_memories_bg(sim_id, agent_memories),
                label="persist_agent_memories",
            )

        # ---- WebSocket broadcasts ------------------------------------ #
        self._broadcast_step_result(sim_id, result)
        self._broadcast_agent_updates(sim_id, state.agents, result.step)

        if state.status == "completed":
            _fire_and_forget(self._notifier.broadcast(str(sim_id), {
                "type": "status_change",
                "data": {"status": "completed"},
            }), label="ws_completed")

        return result

    # ------------------------------------------------------------------ #
    # Run-All
    # ------------------------------------------------------------------ #

    async def run_all(self, sim_id: UUID, *, session: AsyncSession) -> dict:
        """Run every remaining step to completion.

        SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idrun-all
        SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#1.2

        Persists each intermediate step inside a ``step_callback`` closure
        that shares the request session. After ``orchestrator.run_all``
        returns, the final status is persisted and a completion event is
        broadcast via the notification port.

        Orchestrator-level errors propagate upward; the route layer maps
        them to the appropriate HTTP status (429/409/500).
        """
        async def _persist_each_step(result: Any) -> None:
            """Persist each step as run_all progresses.

            The state snapshot must be re-read per step because
            ``orchestrator.run_step`` updates ``state.agents`` in place
            and earlier snapshots would be stale.
            """
            step_state = self.get_state(sim_id)
            await self._repo.save_step(
                sim_id, result, agents=step_state.agents, session=session,
            )

        report = await self._orch.run_all(
            sim_id, step_callback=_persist_each_step,
        )

        # Persist final status
        await self._repo.save_status(
            sim_id, report["status"], report["total_steps"], session=session,
        )

        # Broadcast completion via the notification port
        _fire_and_forget(self._notifier.broadcast(str(sim_id), {
            "type": "run_all_complete",
            "data": {
                "simulation_id": str(sim_id),
                "total_steps": report["total_steps"],
                "final_adoption_rate": report["final_adoption_rate"],
                "final_mean_sentiment": report["final_mean_sentiment"],
                "emergent_events_count": report["emergent_events_count"],
                "duration_ms": report["duration_ms"],
                "status": report["status"],
            },
        }), label="ws_run_all_complete")
        _fire_and_forget(self._notifier.broadcast(str(sim_id), {
            "type": "status_change",
            "data": {"status": report["status"]},
        }), label="ws_run_all_status")

        return report

    # ------------------------------------------------------------------ #
    # Pause / Resume
    # ------------------------------------------------------------------ #

    async def pause(self, sim_id: UUID, *, session: AsyncSession) -> dict:
        """Pause a running simulation."""
        await self._orch.pause(sim_id)
        state = self.get_state(sim_id)
        await self._repo.save_status(
            sim_id, "paused", state.current_step, session=session,
        )
        _fire_and_forget(self._notifier.broadcast(str(sim_id), {
            "type": "status_change", "data": {"status": "paused"},
        }), label="ws_pause")
        return {"status": "paused", "current_step": state.current_step}

    async def resume(self, sim_id: UUID, *, session: AsyncSession) -> dict:
        """Resume a paused simulation.

        ``session`` is accepted for API symmetry with start/step/pause/stop.
        ``orchestrator.resume`` is purely an in-memory state flip; the next
        ``step()`` will persist the new status. This keeps every lifecycle
        method on the service with the same shape for predictability.
        """
        # session is unused on the happy path but kept in the signature so
        # every lifecycle method looks identical to callers and so we can
        # start writing through it later without breaking route callsites.
        del session
        await self._orch.resume(sim_id)
        _fire_and_forget(self._notifier.broadcast(str(sim_id), {
            "type": "status_change", "data": {"status": "running"},
        }), label="ws_resume")
        return {"status": "running"}

    # ------------------------------------------------------------------ #
    # Stop
    # ------------------------------------------------------------------ #

    async def stop(
        self, sim_id: UUID, *, session: AsyncSession,
    ) -> StopOutcome:
        """Stop or reset a simulation.

        SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstop

        :returns: :attr:`StopOutcome.COMPLETED` for a normal stop, or
            :attr:`StopOutcome.RESET` when resetting from
            failed/completed (so it can be restarted).
        :raises SimulationNotFoundError: when the simulation exists in
            neither memory nor DB. The API layer maps this to HTTP 404.
        """
        try:
            state = self.get_state(sim_id)
        except (ValueError, KeyError):
            state = None

        if state is None:
            # DB-only (historical) simulation — update row status directly
            if not await self._repo.row_exists(sim_id, session=session):
                raise SimulationNotFoundError(sim_id)
            await self._repo.save_status(sim_id, "completed", session=session)
            return StopOutcome.COMPLETED

        # Reset from failed/completed → created via the domain method.
        # This replaces direct ``state.status = "created"`` mutation; the
        # orchestrator now owns the state transition and will raise
        # InvalidStateError if the caller tries to reset from the wrong
        # status (defence in depth — the outer branch already filters).
        if state.status in ("failed", "completed"):
            await self._orch.reset(sim_id)
            await self._repo.save_status(sim_id, "created", session=session)
            _fire_and_forget(self._notifier.broadcast(str(sim_id), {
                "type": "status_change",
                "data": {"status": "created"},
            }), label="ws_stop_reset")
            return StopOutcome.RESET

        # Normal stop
        state.status = "completed"
        await self._repo.save_status(sim_id, "completed", session=session)
        _fire_and_forget(self._notifier.broadcast(str(sim_id), {
            "type": "status_change",
            "data": {"status": "completed"},
        }), label="ws_stop")
        return StopOutcome.COMPLETED

    # ================================================================== #
    # Private helpers
    # ================================================================== #

    def _build_llm_records(self, result: Any) -> list[dict]:
        """Build synthetic LLM call records from tier distribution.

        Falls back to a single Tier-1 record if the distribution is empty
        but ``llm_calls_this_step`` reports activity.
        """
        cfg = self._settings
        tier_dist: dict = getattr(result, "llm_tier_distribution", {}) or {}
        records: list[dict] = []
        per_call_latency = (
            result.step_duration_ms / max(1, result.llm_calls_this_step)
        )
        for tier, count in tier_dist.items():
            provider = cfg.default_llm_provider if tier <= 2 else "ollama"
            model = cfg.slm_model if tier <= 2 else cfg.anthropic_default_model
            for _ in range(count):
                records.append({
                    "agent_id": None,
                    "step": result.step,
                    "provider": provider,
                    "model": model,
                    "prompt_hash": "",
                    "latency_ms": per_call_latency,
                    "tokens": None,
                    "cached": False,
                    "tier": int(tier),
                })
        if not records:
            records = [{
                "agent_id": None,
                "step": result.step,
                "provider": cfg.default_llm_provider,
                "model": cfg.slm_model,
                "prompt_hash": "",
                "tier": 1,
            }]
        return records

    def _collect_agent_memories(
        self, agents: list[Any], step: int, *, cap: int = 100,
    ) -> list[dict]:
        """Walk agent state and extract memory dicts (capped)."""
        memories: list[dict] = []
        for agent in agents:
            for mem in (getattr(agent, "memories", None) or []):
                if isinstance(mem, dict):
                    entry = dict(mem)
                    entry.setdefault("agent_id", agent.agent_id)
                    entry.setdefault("step", step)
                    memories.append(entry)
                elif hasattr(mem, "content"):
                    memories.append({
                        "agent_id": agent.agent_id,
                        "memory_type": getattr(mem, "memory_type", "episodic"),
                        "content": getattr(mem, "content", ""),
                        "emotion_weight": getattr(mem, "emotion_weight", 0.5),
                        "step": step,
                        "social_weight": getattr(mem, "social_weight", 0.0),
                    })
                if len(memories) >= cap:
                    return memories
        return memories

    async def _persist_expert_opinions_bg(
        self, sim_id: UUID, step: int, opinions: list[dict],
    ) -> None:
        """Open a fresh session and persist expert opinions."""
        async with self._session_factory() as bg_session:
            await self._repo.persist_expert_opinions(
                sim_id, step, opinions, session=bg_session,
            )

    async def _persist_agent_memories_bg(
        self, sim_id: UUID, memories: list[dict],
    ) -> None:
        """Open a fresh session and persist agent memories."""
        async with self._session_factory() as bg_session:
            await self._repo.persist_agent_memories(
                sim_id, memories, session=bg_session,
            )

    def _broadcast_step_result(self, sim_id: UUID, result: Any) -> None:
        """Fire-and-forget WS broadcast for step_result + emergent_events."""
        ws_data = {
            "type": "step_result",
            "data": {
                "simulation_id": str(sim_id),
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
                "action_distribution": dict(result.action_distribution),
                "propagation_pairs": result.propagation_pairs,
                "llm_calls_this_step": result.llm_calls_this_step,
                "step_duration_ms": result.step_duration_ms,
            },
        }
        _fire_and_forget(
            self._notifier.broadcast(str(sim_id), ws_data), label="ws_step",
        )

        for event in result.emergent_events:
            _fire_and_forget(self._notifier.broadcast(str(sim_id), {
                "type": "emergent_event",
                "data": {
                    "event_type": event.event_type,
                    "step": event.step,
                    "community_id": str(event.community_id) if event.community_id else None,
                    "severity": event.severity,
                    "description": event.description,
                },
            }), label="ws_emergent")

    def _broadcast_agent_updates(
        self, sim_id: UUID, agents: list[Any], step: int,
    ) -> None:
        """Fire-and-forget WS broadcast for per-agent state updates."""
        agent_state_map: dict[str, dict] = {}
        for agent in agents:
            aid = str(agent.agent_id)
            agent_state_map[aid] = {
                "agent_id": aid,
                "step": step,
                "belief": agent.belief,
                "action": agent.action.value if hasattr(agent.action, "value") else str(agent.action),
                "adopted": agent.adopted,
                "exposure_count": agent.exposure_count,
                "emotion": {
                    "interest": agent.emotion.interest,
                    "trust": agent.emotion.trust,
                    "skepticism": agent.emotion.skepticism,
                    "excitement": agent.emotion.excitement,
                },
            }
        _fire_and_forget(
            self._notifier.broadcast_agent_updates(
                str(sim_id), agent_state_map,
            ),
            label="ws_agents",
        )


__all__ = ["SimulationService"]
