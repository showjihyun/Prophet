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
from app.engine.agent.influence import PropagationEvent
from app.engine.diffusion.schema import (
    CampaignEvent,
    CommunitySentiment,
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
    thread_messages: list = field(default_factory=list)  # CapturedMessage list


class CommunityOrchestrator:
    """Manages agent execution within a single community.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#communityorchestrator
    """

    BATCH_SIZE = 32  # configurable via constructor or config injection

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
        session_factory=None,
        simulation_id: UUID | None = None,
    ):
        self.community_id = community_id
        self.community_config = community_config
        self.agents = agents
        self.subgraph = subgraph
        self.agent_node_map = agent_node_map
        self._bridge_node_ids = bridge_node_ids or set()
        self._gateway = gateway

        self._simulation_id = simulation_id
        self._agent_tick = AgentTick(
            llm_adapter=llm_adapter,
            gateway=gateway,
            session_factory=session_factory,
            simulation_id=simulation_id,
        )
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
        # Build a minimal SocialNetwork wrapper so ExposureModel can walk the subgraph
        from app.engine.network.schema import NetworkMetrics as _NetworkMetrics, SocialNetwork as _SocialNetwork
        _social_net = _SocialNetwork(
            graph=self.subgraph,
            communities=[self.community_config],
            influencer_node_ids=[],
            bridge_edge_ids=[],
            metrics=_NetworkMetrics(
                clustering_coefficient=0.0,
                avg_path_length=0.0,
                degree_distribution={},
                community_sizes={},
                bridge_count=0,
                is_valid=True,
            ),
        )
        _exposure_results = self._exposure_model.compute_exposure(
            agents=self.agents,
            graph=_social_net,
            active_events=[
                ce for ce in campaign_events
                if ce.start_step <= step <= ce.end_step
            ],
            step=step,
            agent_node_map=self.agent_node_map,
        )
        exposure_scores = {
            aid: er.exposure_score for aid, er in _exposure_results.items()
        }

        activation = EventDrivenActivation()
        active_agents = activation.get_active_agents(
            all_agents=self.agents,
            exposure_scores=exposure_scores,
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
        all_tick_results: list[AgentTickResult] = []  # for thread capture

        # Tier 3 agents are run via async_tick() which uses embedding-based memory
        # and real LLM cognition (GraphRAG path). Tier 1/2 use the fast sync tick().
        campaign_obj = campaign_events[0] if campaign_events else None
        # Round 8-6: thread all three campaign framing dimensions through to
        # the tick. Previously only ``controversy`` was forwarded; ``novelty``
        # and ``utility`` were silently ignored, which made the entire
        # campaign-framing slider dead input. See docs/USE_CASE_PILOTS.md
        # for the pilot that caught this.
        campaign_controversy = getattr(campaign_obj, "controversy", 0.0)
        campaign_novelty = getattr(campaign_obj, "novelty", 0.5)
        campaign_utility = getattr(campaign_obj, "utility", 0.5)

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
                        campaign_controversy=campaign_controversy,
                        campaign_novelty=campaign_novelty,
                        campaign_utility=campaign_utility,
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
                campaign_controversy=campaign_controversy,
                campaign_novelty=campaign_novelty,
                campaign_utility=campaign_utility,
            )

        def _process_result(result: AgentTickResult) -> None:
            """Apply a single AgentTickResult to the running accumulators."""
            nonlocal llm_calls
            all_tick_results.append(result)
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

        # Process agents in batches to yield to event loop between batches
        for i in range(0, len(self.agents), self.BATCH_SIZE):
            batch = self.agents[i:i + self.BATCH_SIZE]

            # Separate active agents by tier for parallel vs sequential processing
            tier3_tasks: list[tuple[AgentState, int]] = []
            sync_agents: list[tuple[AgentState, int]] = []

            for agent in batch:
                # Inactive agents keep their previous state (IGNORE action)
                if agent.agent_id not in active_agent_ids:
                    updated.append(agent)
                    action_counter[agent.action.value] += 1
                    continue

                tier = tier_map.get(agent.agent_id, 1)

                if tier == 3 and self._agent_tick._llm_adapter is not None:
                    # Tier 3: I/O-bound LLM calls — gather concurrently
                    tier3_tasks.append((agent, tier))
                else:
                    # Tier 1/2: fast CPU-bound — process sequentially
                    sync_agents.append((agent, tier))

            # Process Tier 1/2 agents sequentially (fast, CPU-bound)
            for agent, tier in sync_agents:
                result: AgentTickResult = await _run_agent_tick(agent, tier)
                _process_result(result)

            # Process Tier 3 agents concurrently (slow, I/O-bound LLM calls)
            # Sort results by agent_id for deterministic processing order
            if tier3_tasks:
                tier3_results = await asyncio.gather(
                    *[_run_agent_tick(agent, tier) for agent, tier in tier3_tasks]
                )
                tier3_sorted = sorted(
                    tier3_results, key=lambda r: r.updated_state.agent_id,
                )
                for result in tier3_sorted:
                    _process_result(result)

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

        # 7. Capture thread messages from agent actions
        # SPEC: docs/spec/22_CONVERSATION_THREAD_SPEC.md#CT-03
        # 7. Capture thread messages from agent actions
        # SPEC: docs/spec/22_CONVERSATION_THREAD_SPEC.md#CT-03
        from app.engine.simulation.thread_capture import collect_thread_messages
        campaign_msg = campaign_events[0].message if campaign_events else ""
        thread_msgs = collect_thread_messages(
            community_id=self.community_id,
            simulation_id=self._simulation_id or self.community_id,
            step=step,
            tick_results=all_tick_results,
            agents=agent_map,
            campaign_message=campaign_msg,
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
            thread_messages=thread_msgs,
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

        # Apply bridge trust factor to reduce probability.
        # Forward contextual_packet unchanged so text context survives cross-community hops.
        cross_events: list[PropagationEvent] = []
        for event in all_outbound:
            adjusted = PropagationEvent(
                source_agent_id=event.source_agent_id,
                target_agent_id=event.target_agent_id,
                content_id=event.content_id,
                probability=event.probability * self.BRIDGE_TRUST_FACTOR,
                packet=event.packet,
                step=event.step,
                action_type=event.action_type,
            )
            cross_events.append(adjusted)

        return cross_events


__all__ = [
    "CommunityOrchestrator",
    "CommunityTickResult",
    "BridgePropagator",
]
