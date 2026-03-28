"""Metric Collector — in-memory metric storage and retrieval.
SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from app.engine.agent.schema import AgentAction
from app.engine.agent.tick import AgentTickResult
from app.engine.diffusion.schema import EmergentEvent

from app.engine.simulation.schema import (
    CommunityStepMetrics,
    StepResult,
)

logger = logging.getLogger(__name__)


class MetricCollector:
    """In-memory metric collection for Phase 6.

    SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector

    Stores StepResults in memory. DB persistence deferred to later phase.
    """

    def __init__(self) -> None:
        """SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector"""
        self._history: dict[UUID, list[StepResult]] = {}

    def record(
        self,
        simulation_id: UUID,
        step: int,
        agent_results: list[AgentTickResult],
        emergent_events: list[EmergentEvent],
        step_duration_ms: float,
    ) -> StepResult:
        """Record metrics from a simulation step.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector

        Computes aggregate metrics from agent_results and stores the StepResult.
        """
        total = len(agent_results)
        adopted_count = sum(1 for r in agent_results if r.updated_state.adopted)
        adoption_rate = adopted_count / total if total > 0 else 0.0

        # Action distribution
        action_dist: dict[str, int] = {}
        for r in agent_results:
            action_name = r.action.value
            action_dist[action_name] = action_dist.get(action_name, 0) + 1

        # LLM tier distribution
        tier_dist: dict[int, int] = {}
        llm_calls = 0
        for r in agent_results:
            if r.llm_tier_used is not None:
                tier_dist[r.llm_tier_used] = tier_dist.get(r.llm_tier_used, 0) + 1
                if r.llm_tier_used >= 2:
                    llm_calls += 1

        # Sentiment
        beliefs = [r.updated_state.belief for r in agent_results]
        mean_sentiment = sum(beliefs) / len(beliefs) if beliefs else 0.0
        if len(beliefs) > 1:
            sentiment_var = sum(
                (b - mean_sentiment) ** 2 for b in beliefs
            ) / len(beliefs)
        else:
            sentiment_var = 0.0

        # Diffusion rate
        prev_results = self._history.get(simulation_id, [])
        if prev_results:
            prev_adoption = prev_results[-1].total_adoption
            diffusion_rate = max(0.0, float(adopted_count - prev_adoption))
        else:
            diffusion_rate = float(adopted_count)

        # Community metrics
        community_agents: dict[UUID, list[AgentTickResult]] = {}
        for r in agent_results:
            cid = r.updated_state.community_id
            community_agents.setdefault(cid, []).append(r)

        community_metrics: dict[str, CommunityStepMetrics] = {}
        for cid, results in community_agents.items():
            comm_adopted = sum(1 for r in results if r.updated_state.adopted)
            comm_rate = comm_adopted / len(results) if results else 0.0
            comm_beliefs = [r.updated_state.belief for r in results]
            mean_belief = sum(comm_beliefs) / len(comm_beliefs) if comm_beliefs else 0.0

            # Dominant action
            comm_actions = Counter(r.action for r in results)
            dominant = comm_actions.most_common(1)[0][0] if comm_actions else AgentAction.IGNORE

            # New propagation count
            new_prop = sum(len(r.propagation_events) for r in results)

            community_metrics[str(cid)] = CommunityStepMetrics(
                community_id=cid,
                adoption_count=comm_adopted,
                adoption_rate=comm_rate,
                mean_belief=mean_belief,
                dominant_action=dominant,
                new_propagation_count=new_prop,
            )

        result = StepResult(
            simulation_id=simulation_id,
            step=step,
            timestamp=datetime.now(timezone.utc),
            total_adoption=adopted_count,
            adoption_rate=adoption_rate,
            diffusion_rate=diffusion_rate,
            mean_sentiment=mean_sentiment,
            sentiment_variance=sentiment_var,
            community_metrics=community_metrics,
            emergent_events=emergent_events,
            action_distribution=action_dist,
            llm_calls_this_step=llm_calls,
            llm_tier_distribution=tier_dist,
            step_duration_ms=step_duration_ms,
        )

        self._history.setdefault(simulation_id, []).append(result)
        return result

    def get_metric_history(
        self,
        simulation_id: UUID,
        metric: str,
        from_step: int = 0,
        to_step: int | None = None,
    ) -> list[tuple[int, float]]:
        """Returns [(step, value)] for the requested metric.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector
        """
        results = self._history.get(simulation_id, [])
        out: list[tuple[int, float]] = []

        for sr in results:
            if sr.step < from_step:
                continue
            if to_step is not None and sr.step > to_step:
                continue

            value = getattr(sr, metric, None)
            if value is not None and isinstance(value, (int, float)):
                out.append((sr.step, float(value)))

        return out

    def get_all_results(self, simulation_id: UUID) -> list[StepResult]:
        """Return all recorded StepResults for a simulation."""
        return self._history.get(simulation_id, [])


__all__ = ["MetricCollector"]
