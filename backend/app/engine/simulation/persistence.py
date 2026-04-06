"""DB persistence layer for simulation state.
SPEC: docs/spec/08_DB_SPEC.md

Writes simulation lifecycle events to PostgreSQL without blocking
the in-memory orchestrator flow. Failures are logged but do not
crash the simulation — in-memory state remains the runtime source
of truth, DB is the durable audit trail.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import Simulation, SimStep, SimulationEvent
from app.models.agent import Agent
from app.models.community import Community
from app.models.campaign import Campaign
from app.models.network import NetworkEdge
from app.models.propagation import EmergentEvent as EmergentEventORM, ExpertOpinion, LLMCall, MonteCarloRun, PropagationEvent
from app.models.agent import AgentState as AgentStateORM
from app.models.memory import AgentMemory

if TYPE_CHECKING:
    from app.engine.simulation.schema import SimulationConfig, StepResult

logger = logging.getLogger(__name__)


class SimulationPersistence:
    """Async persistence layer for simulation data.

    SPEC: docs/spec/08_DB_SPEC.md

    Each method accepts an AsyncSession and performs writes.
    All methods are fire-and-forget safe — exceptions are caught and logged.
    """

    async def persist_creation(
        self,
        session: AsyncSession,
        sim_id: uuid.UUID,
        config: SimulationConfig,
        agents: list[Any],
        network_edges: list[tuple[Any, Any, dict]],
    ) -> None:
        """Persist a newly created simulation to DB."""
        try:
            # 1. Simulation row
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

            # 3. Community rows
            community_ids_seen: set[str] = set()
            for agent in agents:
                cid = str(agent.community_id)
                if cid not in community_ids_seen:
                    community_ids_seen.add(cid)
                    comm_row = Community(
                        community_id=uuid.UUID(cid) if len(cid) > 8 else uuid.uuid4(),
                        simulation_id=sim_id,
                        name=cid[:8],
                        community_key=cid[:10],
                        agent_type="consumer",
                        size=sum(1 for a in agents if str(a.community_id) == cid),
                    )
                    session.add(comm_row)

            # 4. Agent rows (batch)
            for agent in agents:
                agent_row = Agent(
                    agent_id=agent.agent_id,
                    simulation_id=sim_id,
                    community_id=agent.community_id,
                    agent_type=agent.agent_type.value if hasattr(agent.agent_type, 'value') else str(agent.agent_type),
                    openness=agent.personality.openness,
                    skepticism=agent.personality.skepticism,
                    trend_following=agent.personality.trend_following,
                    brand_loyalty=agent.personality.brand_loyalty,
                    social_influence=agent.personality.social_influence,
                    emotion_interest=agent.emotion.interest,
                    emotion_trust=agent.emotion.trust,
                    emotion_skepticism=agent.emotion.skepticism,
                    emotion_excitement=agent.emotion.excitement,
                    influence_score=agent.influence_score,
                )
                session.add(agent_row)

            # 5. Network edge rows (batch, limit to avoid huge inserts)
            edge_batch = network_edges[:5000]  # cap at 5000 edges
            for src, tgt, data in edge_batch:
                edge_row = NetworkEdge(
                    edge_id=uuid.uuid4(),
                    simulation_id=sim_id,
                    source_node_id=int(src) if isinstance(src, (int, float)) else hash(str(src)) % 2147483647,
                    target_node_id=int(tgt) if isinstance(tgt, (int, float)) else hash(str(tgt)) % 2147483647,
                    weight=data.get("weight", 1.0),
                    is_bridge=data.get("is_bridge", False),
                )
                session.add(edge_row)

            await session.commit()
            logger.info("Persisted simulation %s: %d agents, %d edges", sim_id, len(agents), len(network_edges))
        except Exception:
            await session.rollback()
            logger.exception("Failed to persist simulation creation %s", sim_id)

    async def persist_status(
        self,
        session: AsyncSession,
        sim_id: uuid.UUID,
        status: str,
        current_step: int | None = None,
    ) -> None:
        """Persist a status change."""
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
        """Persist a step result, agent state snapshots, and propagation events.

        SPEC: docs/spec/08_DB_SPEC.md

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

            # C-1: Persist agent state snapshots
            if agents:
                for agent in agents:
                    try:
                        state_row = AgentStateORM(
                            state_id=uuid.uuid4(),
                            simulation_id=sim_id,
                            agent_id=agent.agent_id,
                            step=result.step,
                            openness=agent.personality.openness,
                            skepticism=agent.personality.skepticism,
                            trend_following=agent.personality.trend_following,
                            brand_loyalty=agent.personality.brand_loyalty,
                            social_influence=agent.personality.social_influence,
                            emotion_interest=agent.emotion.interest,
                            emotion_trust=agent.emotion.trust,
                            emotion_skepticism=agent.emotion.skepticism,
                            emotion_excitement=agent.emotion.excitement,
                            community_id=agent.community_id,
                            belief=agent.belief,
                            action=agent.action.value if hasattr(agent.action, 'value') else str(agent.action),
                            adopted=agent.adopted,
                            exposure_count=agent.exposure_count,
                            llm_tier_used=agent.llm_tier_used,
                        )
                        session.add(state_row)
                    except Exception:
                        pass  # skip individual agent on error, continue batch

            # C-2: Persist propagation events
            if propagation_pairs:
                for src_id, tgt_id, action, prob in propagation_pairs:
                    try:
                        prop_row = PropagationEvent(
                            propagation_id=uuid.uuid4(),
                            simulation_id=sim_id,
                            step=result.step,
                            source_agent_id=src_id,
                            target_agent_id=tgt_id,
                            action_type=action,
                            probability=prob,
                        )
                        session.add(prop_row)
                    except Exception:
                        pass  # skip individual event on error

            await session.commit()
            logger.debug("Persisted step %d for simulation %s", result.step, sim_id)
        except Exception:
            await session.rollback()
            logger.exception("Failed to persist step %d for %s", result.step, sim_id)

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
                    embedding=None,
                )
                session.add(row)
            await session.commit()
            logger.debug("Persisted %d agent memories for simulation %s", len(batch), sim_id)
        except Exception:
            await session.rollback()
            logger.exception("Failed to persist agent memories for %s", sim_id)

    async def load_simulations(self, session: AsyncSession) -> list[dict]:
        """Load all simulations from DB for listing."""
        try:
            result = await session.execute(
                select(Simulation).order_by(Simulation.created_at.desc())
            )
            rows = result.scalars().all()
            return [
                {
                    "simulation_id": str(r.simulation_id),
                    "name": r.name,
                    "description": r.description or "",
                    "status": r.status,
                    "current_step": r.current_step,
                    "max_steps": r.max_steps,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        except Exception:
            logger.exception("Failed to load simulations from DB")
            return []

    async def load_steps(self, session: AsyncSession, sim_id: uuid.UUID) -> list[dict]:
        """Load step history from DB."""
        try:
            result = await session.execute(
                select(SimStep)
                .where(SimStep.simulation_id == sim_id)
                .order_by(SimStep.step)
            )
            rows = result.scalars().all()
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
                }
                for r in rows
            ]
        except Exception:
            logger.exception("Failed to load steps for %s", sim_id)
            return []


def _config_to_dict(config: SimulationConfig) -> dict:
    """Convert SimulationConfig to a JSON-serializable dict."""
    try:
        return {
            "name": config.name,
            "description": config.description,
            "max_steps": config.max_steps,
            "random_seed": config.random_seed,
            "slm_llm_ratio": config.slm_llm_ratio,
            "communities": [c if isinstance(c, str) else str(c) for c in config.communities],
        }
    except Exception:
        return {"name": getattr(config, "name", "unknown")}


def _community_metric_to_dict(metric: Any) -> dict:
    """Convert a CommunityStepMetrics to dict."""
    if isinstance(metric, dict):
        return metric
    try:
        return asdict(metric)
    except Exception:
        return {}
