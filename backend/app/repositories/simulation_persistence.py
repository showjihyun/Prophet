"""DB persistence layer for simulation state.

SPEC: docs/spec/08_DB_SPEC.md
SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#2.4

Writes simulation lifecycle events to PostgreSQL without blocking
the in-memory orchestrator flow. Failures are logged but do not
crash the simulation — in-memory state remains the runtime source
of truth, DB is the durable audit trail.

**Round 6 move**: previously lived at
``app/engine/simulation/persistence.py`` which violated CA-01 (the
engine layer must not depend on SQLAlchemy). Moved under
``repositories/`` so the file sits on the correct side of the
dependency arrow — ``SqlSimulationRepository`` wraps it behind the
``SimulationRepository`` Protocol.
"""
from __future__ import annotations

import logging
import uuid
import dataclasses
from dataclasses import asdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import Simulation, SimStep, SimulationEvent
from app.models.agent import Agent
from app.models.community import Community
from app.models.campaign import Campaign
from app.models.network import NetworkEdge
from app.models.propagation import EmergentEvent as EmergentEventORM, ExpertOpinion, LLMCall, PropagationEvent
from app.models.agent import AgentState as AgentStateORM
from app.models.memory import AgentMemory

if TYPE_CHECKING:
    from app.engine.simulation.schema import SimulationConfig, StepResult

logger = logging.getLogger(__name__)


def _safe_uuid(value: str) -> uuid.UUID:
    """Parse *value* as UUID, falling back to a fresh random UUID on failure."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return uuid.uuid4()


def _node_id_to_int(node_id: Any) -> int:
    """Map a NetworkX node id to a stable 32-bit signed integer.

    The ``network_edges`` table stores endpoints as ``INTEGER`` columns.
    NetworkGenerator always produces integer node ids, but older
    NetworkX graphs or custom networks may use strings. We must map
    any node id to an int **deterministically** — using Python's
    built-in ``hash()`` would randomize the mapping across processes
    (PYTHONHASHSEED), breaking simulation replay.

    :returns: ``int(node_id)`` if already numeric, otherwise a
        deterministic 31-bit digest of its string form (SHA-1 truncated,
        masked to fit a signed INTEGER column).
    """
    if isinstance(node_id, (int, float)):
        return int(node_id)
    import hashlib as _hashlib
    digest = _hashlib.sha1(str(node_id).encode()).digest()
    # Take first 4 bytes as unsigned int, then mask to 31 bits so the
    # value fits a signed PostgreSQL INTEGER (max 2,147,483,647).
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


class SimulationPersistence:
    """Async persistence layer for simulation data.

    SPEC: docs/spec/08_DB_SPEC.md
    SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#1.4

    Each method accepts an AsyncSession and performs writes.
    Fire-and-forget safe with retry logic — transient failures are retried
    up to _RETRY_COUNT times. Permanent failures are logged and recorded in
    a bounded failure queue for admin inspection.
    """

    _RETRY_COUNT: int = 3
    _RETRY_DELAY_BASE: float = 0.3

    def __init__(self) -> None:
        from collections import deque
        self._failed_queue: deque[dict[str, Any]] = deque(maxlen=1000)

    @property
    def failed_queue(self) -> list[dict[str, Any]]:
        """Return a snapshot of the persistence failure queue."""
        return list(self._failed_queue)

    def _record_failure(self, operation: str, sim_id: Any, detail: str) -> None:
        """Record a permanent persistence failure."""
        self._failed_queue.append({
            "operation": operation,
            "simulation_id": str(sim_id),
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def persist_creation(
        self,
        session: AsyncSession,
        sim_id: uuid.UUID,
        config: SimulationConfig,
        agents: list[Any],
        network_edges: list[tuple[Any, Any, dict]],
    ) -> None:
        """Persist a newly created simulation to DB — **strict with retry**.

        Unlike the other ``persist_*`` methods in this class, which are
        fire-and-forget (log + swallow), ``persist_creation`` is a REQUIRED
        step in the simulation lifecycle. If it fails, the caller must know
        so downstream code does not create FK references to a non-existent
        row (e.g. ``scenarios.simulation_id``) or leave a ghost simulation
        running in memory with no DB backing.

        Retry policy (same pattern as :meth:`persist_step`):
          * Attempts the full transaction up to ``_RETRY_COUNT`` times.
          * Back-off sleep between attempts (``_RETRY_DELAY_BASE * attempt``).
          * After all attempts fail, the failure is recorded on
            :attr:`failed_queue` and the last exception is **re-raised**
            so the caller can abort cleanly.

        IMPORTANT: We mix ORM ``session.add`` with bulk Core
        ``session.execute(insert)``. The bulk Core path bypasses the ORM
        unit-of-work and triggers an autoflush of pending ORM objects, but
        autoflush ordering does NOT always honour FK dependencies — Campaign
        can flush before Simulation and produce a
        ``campaigns_simulation_id_fkey`` violation. To avoid this, we
        explicitly flush the Simulation row first so its INSERT lands before
        anything that references it.

        Raises:
            The last DB exception after all retries are exhausted. The
            session is rolled back before the exception propagates.
        """
        import asyncio as _aio

        last_exc: Exception | None = None
        for attempt in range(1, self._RETRY_COUNT + 1):
            try:
                # 1. Simulation row — flush IMMEDIATELY so child FKs resolve.
                sim_row = Simulation(
                    simulation_id=sim_id,
                    name=config.name,
                    description=config.description,
                    status="configured",
                    current_step=0,
                    max_steps=config.max_steps,
                    config=_config_to_dict(config),
                    random_seed=config.random_seed,
                )
                session.add(sim_row)
                await session.flush()

                # 2. Campaign row
                if config.campaign:
                    campaign_row = Campaign(
                        campaign_id=uuid.uuid4(),
                        simulation_id=sim_id,
                        name=config.campaign.name,
                        budget=config.campaign.budget,
                        channels=config.campaign.channels,
                        message=config.campaign.message,
                        controversy=config.campaign.controversy,
                        novelty=config.campaign.novelty,
                        utility=config.campaign.utility,
                    )
                    session.add(campaign_row)
                    await session.flush()

                # 3. Community rows — single-pass size count (was O(n²))
                community_sizes: dict[str, int] = {}
                for agent in agents:
                    cid = str(agent.community_id)
                    community_sizes[cid] = community_sizes.get(cid, 0) + 1

                community_values = [
                    {
                        "community_id": _safe_uuid(cid),
                        "simulation_id": sim_id,
                        "name": cid[:8],
                        "community_key": cid[:10],
                        "agent_type": "consumer",
                        "size": size,
                    }
                    for cid, size in community_sizes.items()
                ]
                if community_values:
                    await session.execute(insert(Community), community_values)

                # 4. Agent rows — bulk insert
                agent_values = [
                    {
                        "agent_id": agent.agent_id,
                        "simulation_id": sim_id,
                        "community_id": agent.community_id,
                        "agent_type": (
                            agent.agent_type.value
                            if hasattr(agent.agent_type, "value")
                            else str(agent.agent_type)
                        ),
                        "openness": agent.personality.openness,
                        "skepticism": agent.personality.skepticism,
                        "trend_following": agent.personality.trend_following,
                        "brand_loyalty": agent.personality.brand_loyalty,
                        "social_influence": agent.personality.social_influence,
                        "emotion_interest": agent.emotion.interest,
                        "emotion_trust": agent.emotion.trust,
                        "emotion_skepticism": agent.emotion.skepticism,
                        "emotion_excitement": agent.emotion.excitement,
                        "influence_score": agent.influence_score,
                    }
                    for agent in agents
                ]
                if agent_values:
                    await session.execute(insert(Agent), agent_values)

                # 5. Network edge rows — batch insert (no cap)
                # SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#5.3c
                _EDGE_BATCH_SIZE = 1000
                for i in range(0, len(network_edges), _EDGE_BATCH_SIZE):
                    edge_chunk = network_edges[i:i + _EDGE_BATCH_SIZE]
                    edge_values = [
                        {
                            "edge_id": uuid.uuid4(),
                            "simulation_id": sim_id,
                            "source_node_id": _node_id_to_int(src),
                            "target_node_id": _node_id_to_int(tgt),
                            "weight": data.get("weight", 1.0),
                            "is_bridge": data.get("is_bridge", False),
                        }
                        for src, tgt, data in edge_chunk
                    ]
                    if edge_values:
                        await session.execute(insert(NetworkEdge), edge_values)

                await session.commit()
                if attempt == 1:
                    logger.info(
                        "Persisted simulation %s: %d agents, %d edges",
                        sim_id, len(agents), len(network_edges),
                    )
                else:
                    logger.info(
                        "persist_creation retry %d succeeded for sim %s",
                        attempt, sim_id,
                    )
                return
            except Exception as exc:
                last_exc = exc
                await session.rollback()
                logger.warning(
                    "persist_creation attempt %d/%d failed for sim %s: %s",
                    attempt, self._RETRY_COUNT, sim_id, exc,
                )
                if attempt < self._RETRY_COUNT:
                    await _aio.sleep(self._RETRY_DELAY_BASE * attempt)

        # All retries exhausted — record + re-raise (strict contract).
        self._record_failure("persist_creation", sim_id, str(last_exc))
        logger.error(
            "persist_creation PERMANENTLY FAILED for sim=%s after %d attempts: %s",
            sim_id, self._RETRY_COUNT, last_exc,
        )
        assert last_exc is not None  # loop ran at least once
        raise last_exc

    async def persist_status(
        self,
        session: AsyncSession,
        sim_id: uuid.UUID,
        status: str,
        current_step: int | None = None,
    ) -> None:
        """Persist a status change — **best-effort, swallows failures**.

        Unlike :meth:`persist_creation`, this is deliberately tolerant of
        transient DB errors: a single failed status write should not abort
        an in-progress simulation step. Failures are logged and the row
        stays out-of-sync until the next successful write (typically the
        next ``persist_step`` or status change).
        """
        try:
            values: dict[str, Any] = {"status": status}
            if current_step is not None:
                values["current_step"] = current_step
            if status == "running":
                values["started_at"] = datetime.now(timezone.utc)
            elif status in ("completed", "failed"):
                values["completed_at"] = datetime.now(timezone.utc)

            await session.execute(
                update(Simulation).where(Simulation.simulation_id == sim_id).values(**values)
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Failed to persist status for %s", sim_id)

    async def persist_step(
        self,
        session: AsyncSession,
        sim_id: uuid.UUID,
        result: StepResult,
        agents: list[Any] | None = None,
        propagation_pairs: list[tuple[Any, Any, str, float]] | None = None,
    ) -> None:
        """Persist a step result — **best-effort with retry + failed_queue**.

        SPEC: docs/spec/08_DB_SPEC.md

        Retries up to ``_RETRY_COUNT`` times with exponential back-off.
        If all attempts fail, the failure is recorded on
        :attr:`failed_queue` for operational recovery and the method
        returns normally — the simulation keeps running even if a single
        step could not be persisted. Use :meth:`persist_creation` when
        strict all-or-nothing semantics are required.

        Args:
            agents: list of AgentState dataclass instances (from orchestrator).
                    Each agent snapshot is written to the ``agent_states`` table.
            propagation_pairs: list of (source_agent_id, target_agent_id,
                    action_type, probability) tuples from this step's diffusion.
        """
        try:
            step_row = SimStep(
                step_id=uuid.uuid4(),
                simulation_id=sim_id,
                step=result.step,
                total_adoption=result.total_adoption,
                adoption_rate=result.adoption_rate,
                diffusion_rate=result.diffusion_rate,
                mean_sentiment=result.mean_sentiment,
                sentiment_variance=result.sentiment_variance,
                action_distribution={k: v for k, v in result.action_distribution.items()},
                community_metrics={k: _community_metric_to_dict(v) for k, v in result.community_metrics.items()},
                llm_calls_count=result.llm_calls_this_step,
                step_duration_ms=result.step_duration_ms,
            )
            session.add(step_row)

            # Persist emergent events
            for event in result.emergent_events:
                ev_row = EmergentEventORM(
                    event_id=uuid.uuid4(),
                    simulation_id=sim_id,
                    step=result.step,
                    event_type=event.event_type,
                    community_id=str(event.community_id) if event.community_id else None,
                    severity=event.severity,
                    description=event.description,
                )
                session.add(ev_row)

            # C-1: Persist agent state snapshots — bulk insert
            if agents:
                state_values: list[dict] = []
                for agent in agents:
                    try:
                        state_values.append({
                            "state_id": uuid.uuid4(),
                            "simulation_id": sim_id,
                            "agent_id": agent.agent_id,
                            "step": result.step,
                            "openness": agent.personality.openness,
                            "skepticism": agent.personality.skepticism,
                            "trend_following": agent.personality.trend_following,
                            "brand_loyalty": agent.personality.brand_loyalty,
                            "social_influence": agent.personality.social_influence,
                            "emotion_interest": agent.emotion.interest,
                            "emotion_trust": agent.emotion.trust,
                            "emotion_skepticism": agent.emotion.skepticism,
                            "emotion_excitement": agent.emotion.excitement,
                            "community_id": agent.community_id,
                            "belief": agent.belief,
                            "action": (
                                agent.action.value
                                if hasattr(agent.action, "value")
                                else str(agent.action)
                            ),
                            "adopted": agent.adopted,
                            "exposure_count": agent.exposure_count,
                            "llm_tier_used": agent.llm_tier_used,
                        })
                    except (AttributeError, TypeError, ValueError) as exc:
                        logger.warning(
                            "Skipping malformed agent %s at step %d: %s",
                            getattr(agent, "agent_id", "unknown"), result.step, exc,
                        )
                if state_values:
                    await session.execute(insert(AgentStateORM), state_values)

            # C-2: Persist propagation events — bulk insert
            if propagation_pairs:
                prop_values = [
                    {
                        "propagation_id": uuid.uuid4(),
                        "simulation_id": sim_id,
                        "step": result.step,
                        "source_agent_id": src_id,
                        "target_agent_id": tgt_id,
                        "action_type": action,
                        "probability": prob,
                    }
                    for src_id, tgt_id, action, prob in propagation_pairs
                ]
                if prop_values:
                    await session.execute(insert(PropagationEvent), prop_values)

            await session.commit()
            logger.debug("Persisted step %d for simulation %s", result.step, sim_id)
            return
        except Exception:
            await session.rollback()
            logger.warning("persist_step attempt 1 failed for step %d sim %s", result.step, sim_id)

        # Retry up to _RETRY_COUNT - 1 more times
        import asyncio as _aio
        for attempt in range(2, self._RETRY_COUNT + 1):
            try:
                await _aio.sleep(self._RETRY_DELAY_BASE * attempt)
                step_row = SimStep(
                    step_id=uuid.uuid4(),
                    simulation_id=sim_id,
                    step=result.step,
                    total_adoption=result.total_adoption,
                    adoption_rate=result.adoption_rate,
                    diffusion_rate=result.diffusion_rate,
                    mean_sentiment=result.mean_sentiment,
                    sentiment_variance=result.sentiment_variance,
                    action_distribution={k: v for k, v in result.action_distribution.items()},
                    community_metrics={k: _community_metric_to_dict(v) for k, v in result.community_metrics.items()},
                    llm_calls_count=result.llm_calls_this_step,
                    step_duration_ms=result.step_duration_ms,
                )
                session.add(step_row)
                # Re-persist emergent events that were lost on rollback.
                for event in result.emergent_events:
                    session.add(EmergentEventORM(
                        event_id=uuid.uuid4(),
                        simulation_id=sim_id,
                        step=result.step,
                        event_type=event.event_type,
                        community_id=str(event.community_id) if event.community_id else None,
                        severity=event.severity,
                        description=event.description,
                    ))
                # Re-persist agent states (were also lost on rollback).
                if agents:
                    retry_states: list[dict] = []
                    for agent in agents:
                        try:
                            retry_states.append({
                                "state_id": uuid.uuid4(),
                                "simulation_id": sim_id,
                                "agent_id": agent.agent_id,
                                "step": result.step,
                                "openness": agent.personality.openness,
                                "skepticism": agent.personality.skepticism,
                                "trend_following": agent.personality.trend_following,
                                "brand_loyalty": agent.personality.brand_loyalty,
                                "social_influence": agent.personality.social_influence,
                                "emotion_interest": agent.emotion.interest,
                                "emotion_trust": agent.emotion.trust,
                                "emotion_skepticism": agent.emotion.skepticism,
                                "emotion_excitement": agent.emotion.excitement,
                                "community_id": agent.community_id,
                                "belief": agent.belief,
                                "action": (
                                    agent.action.value
                                    if hasattr(agent.action, "value")
                                    else str(agent.action)
                                ),
                                "adopted": agent.adopted,
                                "exposure_count": agent.exposure_count,
                                "llm_tier_used": agent.llm_tier_used,
                            })
                        except (AttributeError, TypeError, ValueError):
                            pass  # skip malformed — already warned on first attempt
                    if retry_states:
                        await session.execute(insert(AgentStateORM), retry_states)
                # Re-persist propagation events.
                if propagation_pairs:
                    retry_props = [
                        {
                            "propagation_id": uuid.uuid4(),
                            "simulation_id": sim_id,
                            "step": result.step,
                            "source_agent_id": src_id,
                            "target_agent_id": tgt_id,
                            "action_type": action,
                            "probability": prob,
                        }
                        for src_id, tgt_id, action, prob in propagation_pairs
                    ]
                    if retry_props:
                        await session.execute(insert(PropagationEvent), retry_props)
                await session.commit()
                logger.info("persist_step retry %d succeeded for step %d sim %s", attempt, result.step, sim_id)
                return
            except Exception:
                await session.rollback()
                logger.warning("persist_step attempt %d failed for step %d sim %s", attempt, result.step, sim_id)

        # All retries exhausted
        self._record_failure("persist_step", sim_id, f"step={result.step}")
        logger.error("persist_step PERMANENTLY FAILED for sim=%s step=%d after %d attempts", sim_id, result.step, self._RETRY_COUNT)

    async def persist_event(
        self,
        session: AsyncSession,
        sim_id: uuid.UUID,
        event_type: str,
        step: int,
        payload: dict | None = None,
    ) -> uuid.UUID:
        """Persist a simulation event (inject, replay, etc.)."""
        event_id = uuid.uuid4()
        try:
            row = SimulationEvent(
                event_id=event_id,
                simulation_id=sim_id,
                step=step,
                event_type=event_type,
                payload=payload,
            )
            session.add(row)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Failed to persist event for %s", sim_id)
        return event_id

    async def persist_llm_calls(
        self,
        session: AsyncSession,
        sim_id: uuid.UUID,
        call_records: list[dict],
    ) -> None:
        """Persist a batch of LLM call records to the llm_calls table.

        SPEC: docs/spec/08_DB_SPEC.md

        Each record dict should contain:
            agent_id (UUID | None), step (int), provider (str),
            latency_ms (float | None), tokens (int | None),
            cached (bool), tier (int)
        """
        if not call_records:
            return
        try:
            for rec in call_records:
                row = LLMCall(
                    call_id=uuid.uuid4(),
                    simulation_id=sim_id,
                    agent_id=rec.get("agent_id"),
                    step=rec.get("step", 0),
                    provider=rec.get("provider", "unknown"),
                    model=rec.get("model", "unknown"),
                    prompt_hash=rec.get("prompt_hash", ""),
                    prompt_tokens=rec.get("tokens"),
                    completion_tokens=None,
                    latency_ms=rec.get("latency_ms"),
                    cached=rec.get("cached", False),
                    tier=rec.get("tier", 1),
                )
                session.add(row)
            await session.commit()
            logger.debug(
                "Persisted %d LLM call records for simulation %s",
                len(call_records),
                sim_id,
            )
        except Exception:
            await session.rollback()
            logger.exception("Failed to persist LLM calls for %s", sim_id)

    async def persist_expert_opinions(
        self,
        session: AsyncSession,
        sim_id: uuid.UUID,
        step: int,
        opinions: list[dict],
    ) -> None:
        """Persist expert opinion records for a step.

        SPEC: docs/spec/08_DB_SPEC.md#expert_opinions

        Each opinion dict: {agent_id, opinion_text, score, confidence, step}
        Fire-and-forget — exceptions are logged but do not raise.
        """
        if not opinions:
            return
        try:
            for op in opinions:
                agent_id = op.get("agent_id")
                if agent_id is None:
                    continue
                # Clamp score and confidence to valid DB ranges
                score = max(-1.0, min(1.0, float(op.get("score", 0.0))))
                confidence = max(0.0, min(1.0, float(op.get("confidence", 0.5))))
                row = ExpertOpinion(
                    opinion_id=uuid.uuid4(),
                    simulation_id=sim_id,
                    expert_agent_id=agent_id if isinstance(agent_id, uuid.UUID) else uuid.UUID(str(agent_id)),
                    step=op.get("step", step),
                    score=score,
                    reasoning=op.get("opinion_text"),
                    confidence=confidence,
                    affects_communities=[],
                )
                session.add(row)
            await session.commit()
            logger.debug("Persisted %d expert opinions for simulation %s step %d", len(opinions), sim_id, step)
        except Exception:
            await session.rollback()
            logger.exception("Failed to persist expert opinions for %s step %d", sim_id, step)

    async def persist_agent_memories(
        self,
        session: AsyncSession,
        sim_id: uuid.UUID,
        memories: list[dict],
    ) -> None:
        """Persist agent memory records for a step.

        SPEC: docs/spec/08_DB_SPEC.md#agent_memories

        Each memory dict: {agent_id, memory_type, content, emotion_weight, step, social_weight}
        Batched — cap at 100 per call to avoid huge inserts.
        Fire-and-forget — exceptions are logged but do not raise.
        """
        if not memories:
            return
        batch = memories[:100]
        try:
            for mem in batch:
                agent_id = mem.get("agent_id")
                if agent_id is None:
                    continue
                content = mem.get("content", "")
                if not content:
                    continue
                row = AgentMemory(
                    memory_id=uuid.uuid4(),
                    simulation_id=sim_id,
                    agent_id=agent_id if isinstance(agent_id, uuid.UUID) else uuid.UUID(str(agent_id)),
                    memory_type=mem.get("memory_type", "episodic"),
                    content=str(content),
                    emotion_weight=float(mem.get("emotion_weight", 0.5)),
                    step=int(mem.get("step", 0)),
                    social_weight=float(mem.get("social_weight", 0.0)),
                    embedding=mem.get("embedding"),
                )
                session.add(row)
            await session.commit()
            logger.debug("Persisted %d agent memories for simulation %s", len(batch), sim_id)
        except Exception:
            await session.rollback()
            logger.exception("Failed to persist agent memories for %s", sim_id)

    async def persist_thread_messages(
        self,
        session: AsyncSession,
        messages: list,
    ) -> None:
        """Persist thread messages captured during a simulation step.

        SPEC: docs/spec/22_CONVERSATION_THREAD_SPEC.md#CT-05

        Fire-and-forget — exceptions are logged but do not raise.
        """
        if not messages:
            return
        try:
            from app.models.thread import ThreadMessageRow
            for msg in messages[:200]:  # cap per step
                row = ThreadMessageRow(
                    message_id=msg.message_id,
                    simulation_id=msg.simulation_id,
                    community_id=msg.community_id,
                    agent_id=msg.agent_id,
                    step=msg.step,
                    action=msg.action,
                    content=msg.content,
                    belief=msg.belief,
                    emotion_valence=msg.emotion_valence,
                    reply_to_id=msg.reply_to_id,
                )
                session.add(row)
            await session.commit()
            logger.debug("Persisted %d thread messages", len(messages[:200]))
        except Exception:
            await session.rollback()
            logger.exception("Failed to persist thread messages")

    @staticmethod
    def _row_to_dict(r: Simulation) -> dict:
        return {
            "simulation_id": str(r.simulation_id),
            "name": r.name,
            "description": r.description or "",
            "status": r.status,
            "current_step": r.current_step,
            "max_steps": r.max_steps,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }

    async def simulation_row_exists(
        self, session: AsyncSession, sim_id: uuid.UUID
    ) -> bool:
        """Return True iff the `simulations` row for `sim_id` is in the DB.

        Used by callers that need to update a foreign key referencing
        this row (e.g. `run_scenario` linking `scenarios.simulation_id`).
        A False result means the earlier `persist_creation` call silently
        failed and no FK update should be attempted.
        """
        try:
            result = await session.execute(
                select(Simulation.simulation_id).where(
                    Simulation.simulation_id == sim_id
                )
            )
            return result.scalar_one_or_none() is not None
        except Exception:
            logger.exception("Failed to check simulation existence %s", sim_id)
            return False

    async def load_simulation(
        self, session: AsyncSession, sim_id: uuid.UUID
    ) -> dict | None:
        """Point-lookup for a single simulation by id.

        Avoids the full-table scan of `load_simulations` on hot paths like
        GET /simulations/{id}.
        """
        try:
            result = await session.execute(
                select(Simulation).where(Simulation.simulation_id == sim_id)
            )
            row = result.scalar_one_or_none()
            return self._row_to_dict(row) if row is not None else None
        except Exception:
            logger.exception("Failed to load simulation %s from DB", sim_id)
            return None

    async def load_simulations(
        self,
        session: AsyncSession,
        *,
        status: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict]:
        """Load simulations from DB for listing, with SQL-side filter/pagination."""
        try:
            stmt = select(Simulation).order_by(Simulation.created_at.desc())
            if status is not None:
                stmt = stmt.where(Simulation.status == status)
            if limit is not None:
                stmt = stmt.limit(limit).offset(offset)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [self._row_to_dict(r) for r in rows]
        except Exception:
            logger.exception("Failed to load simulations from DB")
            return []

    async def count_simulations(
        self, session: AsyncSession, *, status: str | None = None
    ) -> int:
        """Count rows in simulations table (optionally filtered by status)."""
        try:
            from sqlalchemy import func
            stmt = select(func.count()).select_from(Simulation)
            if status is not None:
                stmt = stmt.where(Simulation.status == status)
            result = await session.execute(stmt)
            return int(result.scalar_one() or 0)
        except Exception:
            logger.exception("Failed to count simulations")
            return 0

    async def load_steps(
        self, session: AsyncSession, sim_id: uuid.UUID, limit: int = 2000,
    ) -> list[dict]:
        """Load step history from DB (capped at `limit` rows to prevent unbounded queries).

        FIX (2026-04-13): also fetches `EmergentEvent` rows for the
        simulation and groups them by step into each step dict's
        `emergent_events` list. Previously this method dropped events on
        the floor, so historical sims (loaded from DB after restart)
        showed an empty timeline.
        """
        try:
            result = await session.execute(
                select(SimStep)
                .where(SimStep.simulation_id == sim_id)
                .order_by(SimStep.step)
                .limit(limit)
            )
            rows = result.scalars().all()

            # Fetch emergent events for the steps we actually loaded.
            # Bounded by the same step range to avoid unbounded memory on
            # long-running simulations with many detector firings.
            max_step = rows[-1].step if rows else 0
            ev_result = await session.execute(
                select(EmergentEventORM)
                .where(EmergentEventORM.simulation_id == sim_id)
                .where(EmergentEventORM.step <= max_step)
                .order_by(EmergentEventORM.step)
                .limit(limit * 5)  # generous cap; ~5 events/step worst case
            )
            events_by_step: dict[int, list[dict]] = {}
            for ev in ev_result.scalars().all():
                events_by_step.setdefault(ev.step, []).append({
                    "event_type": ev.event_type,
                    "step": ev.step,
                    "community_id": str(ev.community_id) if ev.community_id else None,
                    "severity": ev.severity,
                    "description": ev.description,
                })

            return [
                {
                    "step": r.step,
                    "total_adoption": r.total_adoption,
                    "adoption_rate": r.adoption_rate,
                    "diffusion_rate": r.diffusion_rate,
                    "mean_sentiment": r.mean_sentiment,
                    "sentiment_variance": r.sentiment_variance,
                    "action_distribution": r.action_distribution or {},
                    "community_metrics": r.community_metrics or {},
                    "llm_calls_this_step": r.llm_calls_count,
                    "step_duration_ms": r.step_duration_ms or 0,
                    "emergent_events": events_by_step.get(r.step, []),
                }
                for r in rows
            ]
        except Exception:
            logger.exception("Failed to load steps for %s", sim_id)
            return []


    async def restore_simulation_state(
        self,
        session: AsyncSession,
        sim_id: uuid.UUID,
    ) -> dict | None:
        """Reconstruct a SimulationState-compatible dict from DB for crash recovery.

        SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#1.3 — Data Integrity A-

        Returns a dict with keys matching SimulationState fields, or None if
        the simulation doesn't exist in DB. The caller (orchestrator) is
        responsible for converting this into a live SimulationState with
        network regeneration.

        Fields returned:
            simulation_id, config (raw dict), status, current_step,
            agents (list of dicts), step_history (list of dicts)
        """
        try:
            # 1. Load simulation row
            sim_result = await session.execute(
                select(Simulation).where(Simulation.simulation_id == sim_id)
            )
            sim_row = sim_result.scalar_one_or_none()
            if sim_row is None:
                return None

            # 2. Load latest agent states
            agent_result = await session.execute(
                select(AgentStateORM)
                .where(AgentStateORM.simulation_id == sim_id)
                .where(AgentStateORM.step == sim_row.current_step)
            )
            agent_rows = agent_result.scalars().all()

            agents = [
                {
                    "agent_id": str(r.agent_id),
                    "belief": r.belief,
                    "action": r.action,
                    "adopted": r.adopted,
                    "exposure_count": r.exposure_count,
                    "community_id": str(r.community_id),
                    "openness": r.openness,
                    "skepticism": r.skepticism,
                    "trend_following": r.trend_following,
                    "brand_loyalty": r.brand_loyalty,
                    "social_influence": r.social_influence,
                    "emotion_interest": r.emotion_interest,
                    "emotion_trust": r.emotion_trust,
                    "emotion_skepticism": r.emotion_skepticism,
                    "emotion_excitement": r.emotion_excitement,
                    "llm_tier_used": r.llm_tier_used,
                }
                for r in agent_rows
            ]

            # 3. Load step history
            steps = await self.load_steps(session, sim_id)

            return {
                "simulation_id": str(sim_id),
                "config": sim_row.config or {},
                "status": sim_row.status,
                "current_step": sim_row.current_step or 0,
                "agents": agents,
                "step_history": steps,
            }
        except Exception:
            logger.exception("Failed to restore simulation state for %s", sim_id)
            return None


def _config_to_dict(config: SimulationConfig) -> dict:
    """Convert SimulationConfig to a JSON-serializable dict."""
    try:
        return {
            "name": config.name,
            "description": config.description,
            "max_steps": config.max_steps,
            "random_seed": config.random_seed,
            "slm_llm_ratio": config.slm_llm_ratio,
            "communities": [
                c if isinstance(c, dict)
                else dataclasses.asdict(c) if dataclasses.is_dataclass(c)
                else str(c)
                for c in config.communities
            ],
        }
    except Exception as exc:
        logger.error("Failed to serialize SimulationConfig: %s", exc)
        return {"name": getattr(config, "name", "unknown")}


def _community_metric_to_dict(metric: Any) -> dict:
    """Convert a CommunityStepMetrics to dict."""
    if isinstance(metric, dict):
        return metric
    try:
        return asdict(metric)
    except Exception as exc:
        logger.error(
            "Failed to convert community metric to dict (type=%s): %s",
            type(metric).__name__, exc,
        )
        return {}
