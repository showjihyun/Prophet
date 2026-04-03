"""Community-level orchestrator and bridge propagator.
SPEC: docs/spec/04_SIMULATION_SPEC.md#communityorchestrator
"""
from __future__ import annotations

import asyncio
import time
from collections import Counter
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import networkx as nx

from app.engine.agent.schema import AgentAction, AgentState
from app.engine.agent.tick import AgentTick, AgentTickResult, GraphContext
from app.engine.agent.tier_selector import TierConfig, TierSelector
from app.engine.agent.perception import EnvironmentEvent, NeighborAction
from app.engine.diffusion.schema import (
    CampaignEvent,
    CommunitySentiment,
    PropagationEvent,
    RecSysConfig,
)
from app.engine.diffusion.exposure_model import ExposureModel
from app.engine.diffusion.sentiment_model import SentimentModel
from app.engine.network.schema import CommunityConfig
from app.engine.simulation.event_activation import EventDrivenActivation


@dataclass
class CommunityTickResult:
    """Result of a single community's tick.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#communityorchestrator
    """
    community_id: UUID
    updated_agents: list[AgentState] = field(default_factory=list)
    propagation_events: list[PropagationEvent] = field(default_factory=list)
    outbound_events: list[PropagationEvent] = field(default_factory=list)
    community_sentiment: CommunitySentiment | None = None
    action_distribution: dict[str, int] = field(default_factory=dict)
    llm_calls: int = 0
    tick_duration_ms: float = 0.0


class CommunityOrchestrator:
    """Manages agent execution within a single community.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#communityorchestrator
    """

    BATCH_SIZE = 32

    def __init__(
        self,
        community_id: UUID,
        community_config: CommunityConfig,
        agents: list[AgentState],
        subgraph: nx.Graph,
        agent_node_map: dict[UUID, int],
        bridge_node_ids: set[int] | None = None,
        llm_adapter: object | None = None,
        gateway: 'LLMGateway | None' = None,
    ):
        self.community_id = community_id
        self.community_config = community_config
        self.agents = agents
        self.subgraph = subgraph
        self.agent_node_map = agent_node_map
        self._bridge_node_ids = bridge_node_ids or set()
        self._gateway = gateway

        self._agent_tick = AgentTick(llm_adapter=llm_adapter)
        self._tier_selector = TierSelector()
        self._exposure_model = ExposureModel()
        self._sentiment_model = SentimentModel()

    async def tick(
        self,
        step: int,
        campaign_events: list[CampaignEvent],
        env_events: list[EnvironmentEvent] | None = None,
        tier_config: TierConfig | None = None,
        seed: int = 0,
        recsys_config: RecSysConfig | None = None,
    ) -> CommunityTickResult:
        """Execute one step for this community's agents.
        SPEC: docs/spec/04_SIMULATION_SPEC.md#communityorchestrator
        """
        start = time.perf_counter()

        if not self.agents:
            return CommunityTickResult(community_id=self.community_id)

        # 1. Build graph context for this community's subgraph
        agent_map: dict[UUID, AgentState] = {a.agent_id: a for a in self.agents}
        node_to_agent: dict[int, UUID] = {}
        for aid, nid in self.agent_node_map.items():
            if aid in agent_map and self.subgraph.has_node(nid):
                node_to_agent[nid] = aid

        neighbor_ids: dict[UUID, list[UUID]] = {}
        edge_weights: dict[tuple[UUID, UUID], float] = {}
        trust_matrix: dict[tuple[UUID, UUID], float] = {}

        for aid, nid in self.agent_node_map.items():
            if aid not in agent_map:
                continue
            neighbors: list[UUID] = []
            if self.subgraph.has_node(nid):
                for nbr in self.subgraph.neighbors(nid):
                    nbr_aid = node_to_agent.get(nbr)
                    if nbr_aid:
                        neighbors.append(nbr_aid)
                        w = self.subgraph[nid][nbr].get("weight", 0.5)
                        edge_weights[(aid, nbr_aid)] = w
                        edge_weights[(nbr_aid, aid)] = w
                        trust_matrix[(aid, nbr_aid)] = w
                        trust_matrix[(nbr_aid, aid)] = w
            neighbor_ids[aid] = neighbors

        # Community beliefs (local only)
        beliefs = [a.belief for a in self.agents]
        community_beliefs: dict[UUID, float] = {
            self.community_id: sum(beliefs) / len(beliefs) if beliefs else 0.0,
        }

        graph_context = GraphContext(
            edges=edge_weights,
            trust_matrix=trust_matrix,
            neighbor_ids=neighbor_ids,
            community_beliefs=community_beliefs,
        )

        # 2. Tier assignment (community-local)
        t_config = tier_config or TierConfig()
        tier_map = self._tier_selector.assign_tiers(self.agents, t_config, seed)

        # 3. Build environment events from campaign events
        if env_events is None:
            env_events = []
            for ce in campaign_events:
                env_events.append(
                    EnvironmentEvent(
                        event_type="campaign_ad",
                        content_id=ce.campaign_id,
                        message=ce.message,
                        source_agent_id=None,
                        channel=ce.channels[0] if ce.channels else "social_feed",
                        timestamp=step,
                    )
                )

        # 3.5. Event-driven activation: only tick active agents
        activation = EventDrivenActivation()
        active_agents = activation.get_active_agents(
            all_agents=self.agents,
            exposure_scores={},  # will be populated from exposure model
            base_activation_rate=0.10,
            seed=seed,
        )
        active_agent_ids = {a.agent_id for a in active_agents}

        # 4. Build neighbor actions from previous step
        neighbor_actions_map: dict[UUID, list[NeighborAction]] = {}
        for agent in self.agents:
            na_list: list[NeighborAction] = []
            for nid in neighbor_ids.get(agent.agent_id, []):
                other = agent_map.get(nid)
                if other and other.action != AgentAction.IGNORE:
                    na_list.append(NeighborAction(
                        agent_id=other.agent_id,
                        action=other.action,
                        content_id=uuid4(),
                        step=step,
                    ))
            neighbor_actions_map[agent.agent_id] = na_list

        # 5. Tick each agent
        updated: list[AgentState] = []
        all_propagation: list[PropagationEvent] = []
        outbound: list[PropagationEvent] = []
        llm_calls = 0
        action_counter: Counter[str] = Counter()

        # Tier 3 agents are run via async_tick() which uses embedding-based memory
        # and real LLM cognition (GraphRAG path). Tier 1/2 use the fast sync tick().
        campaign_obj = campaign_events[0] if campaign_events else None

        async def _run_agent_tick(agent: AgentState, tier: int) -> AgentTickResult:
            """Dispatch to async_tick for Tier 3 (embeddings + LLM) or sync tick for Tier 1/2."""
            if tier == 3 and self._agent_tick._llm_adapter is not None:
                try:
                    return await self._agent_tick.async_tick(
                        agent=agent,
                        environment_events=env_events,
                        neighbor_actions=neighbor_actions_map.get(agent.agent_id, []),
                        cognition_tier=tier,
                        seed=seed,
                        graph_context=graph_context,
                        campaign=campaign_obj,
                    )
                except Exception:
                    # Graceful fallback to sync tick on any async failure
                    pass
            # Fast path: Tier 1/2, or Tier 3 fallback when LLM is unavailable
            return self._agent_tick.tick(
                agent=agent,
                environment_events=env_events,
                neighbor_actions=neighbor_actions_map.get(agent.agent_id, []),
                cognition_tier=tier,
                seed=seed,
                graph_context=graph_context,
            )

        # Process agents in batches to yield to event loop between batches
        for i in range(0, len(self.agents), self.BATCH_SIZE):
            batch = self.agents[i:i + self.BATCH_SIZE]
            for agent in batch:
                # Inactive agents keep their previous state (IGNORE action)
                if agent.agent_id not in active_agent_ids:
                    updated.append(agent)
                    action_counter[agent.action.value] += 1
                    continue

                tier = tier_map.get(agent.agent_id, 1)

                result: AgentTickResult = await _run_agent_tick(agent, tier)

                new_agent = result.updated_state
                updated.append(new_agent)
                action_counter[result.action.value] += 1

                if result.llm_call_log or result.llm_tier_used == 3:
                    llm_calls += 1

                # Separate intra-community vs outbound propagation
                for pe in result.propagation_events:
                    target_node = self.agent_node_map.get(pe.target_agent_id)
                    if target_node is not None and target_node in self._bridge_node_ids:
                        outbound.append(pe)
                    elif pe.target_agent_id in agent_map:
                        all_propagation.append(pe)
                    else:
                        outbound.append(pe)  # target not in this community
            # Yield to event loop between batches (allows other communities to progress)
            await asyncio.sleep(0)

        # 5.5. Flush gateway step cache after all agent ticks
        if self._gateway:
            await self._gateway.flush_step_cache()

        # 6. Community sentiment
        sentiment = self._sentiment_model.update_community_sentiment(
            community_id=self.community_id,
            agent_states=updated,
            expert_opinions=[],
        )

        elapsed = (time.perf_counter() - start) * 1000

        return CommunityTickResult(
            community_id=self.community_id,
            updated_agents=updated,
            propagation_events=all_propagation,
            outbound_events=outbound,
            community_sentiment=sentiment,
            action_distribution=dict(action_counter),
            llm_calls=llm_calls,
            tick_duration_ms=elapsed,
        )


class BridgePropagator:
    """Handles cross-community propagation via bridge edges.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#bridgepropagator
    """

    BRIDGE_TRUST_FACTOR = 0.6

    def propagate(
        self,
        community_results: list[CommunityTickResult],
        bridge_edges: list[tuple[int, int]],
        full_graph: nx.Graph,
    ) -> list[PropagationEvent]:
        """Apply cross-community propagation with reduced trust.
        SPEC: docs/spec/04_SIMULATION_SPEC.md#bridgepropagator
        """
        if not community_results:
            return []

        all_outbound: list[PropagationEvent] = []
        for cr in community_results:
            all_outbound.extend(cr.outbound_events)

        if not all_outbound:
            return []

        # Apply bridge trust factor to reduce probability
        cross_events: list[PropagationEvent] = []
        for event in all_outbound:
            adjusted = PropagationEvent(
                source_agent_id=event.source_agent_id,
                target_agent_id=event.target_agent_id,
                action_type=event.action_type,
                probability=event.probability * self.BRIDGE_TRUST_FACTOR,
                step=event.step,
                message_id=event.message_id,
            )
            cross_events.append(adjusted)

        return cross_events


__all__ = [
    "CommunityOrchestrator",
    "CommunityTickResult",
    "BridgePropagator",
]
