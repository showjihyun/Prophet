"""Step Runner — executes a single simulation step.
SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface (run_step detail)
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from app.engine.agent.perception import EnvironmentEvent, NeighborAction
from app.engine.agent.schema import AgentAction, AgentState
from app.engine.agent.tick import AgentTick, AgentTickResult, GraphContext
from app.engine.agent.tier_selector import TierConfig, TierSelector
from app.engine.diffusion.cascade_detector import (
    CascadeDetector,
    StepResult as CascadeStepResult,
)
from app.engine.diffusion.exposure_model import ExposureModel
from app.engine.diffusion.schema import CampaignEvent, CascadeConfig, EmergentEvent, NegativeEvent, RecSysConfig
from app.engine.diffusion.negative_cascade import NegativeCascadeModel
from app.engine.diffusion.sentiment_model import SentimentModel
from app.engine.network.evolution import NetworkEvolver
from app.engine.network.schema import CommunityConfig, SocialNetwork

from app.engine.simulation.community_orchestrator import (
    BridgePropagator,
    CommunityOrchestrator,
    CommunityTickResult,
)
from app.engine.simulation.schema import (
    CampaignConfig,
    CommunityStepMetrics,
    SimulationConfig,
    StepResult,
)
from app.llm.gateway import LLMGateway

if TYPE_CHECKING:
    from app.engine.simulation.orchestrator import SimulationState

logger = logging.getLogger(__name__)


def _build_campaign_events(
    config: SimulationConfig,
    step: int,
    agents: list[AgentState],
) -> list[CampaignEvent]:
    """Build CampaignEvent list from SimulationConfig.campaign for the current step.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
    """
    campaign = config.campaign
    end_step = campaign.end_step if campaign.end_step is not None else config.max_steps

    if step < campaign.start_step or step > end_step:
        return []

    # Collect all community UUIDs from agents
    all_community_ids = list({a.community_id for a in agents})

    if "all" in campaign.target_communities:
        target_ids = all_community_ids
    else:
        target_ids = [cid for cid in all_community_ids if str(cid) in campaign.target_communities]
        if not target_ids:
            target_ids = all_community_ids  # fallback if no match

    campaign_id = UUID(int=hash(campaign.name) % (2**128))

    return [
        CampaignEvent(
            campaign_id=campaign_id,
            name=campaign.name,
            message=campaign.message,
            channels=campaign.channels,
            novelty=campaign.novelty,
            controversy=campaign.controversy,
            utility=campaign.utility,
            budget=campaign.budget,
            target_communities=target_ids,
            start_step=campaign.start_step,
            end_step=end_step,
        )
    ]


def _build_environment_events(
    campaign_events: list[CampaignEvent],
    step: int,
) -> list[EnvironmentEvent]:
    """Convert CampaignEvents into EnvironmentEvents for agent perception.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
    """
    env_events: list[EnvironmentEvent] = []
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
    return env_events


def _build_graph_context(
    network: SocialNetwork,
    agents: list[AgentState],
) -> GraphContext:
    """Build GraphContext from SocialNetwork for AgentTick.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
    """
    G = network.graph
    edges: dict[tuple[UUID, UUID], float] = {}
    trust_matrix: dict[tuple[UUID, UUID], float] = {}
    neighbor_ids: dict[UUID, list[UUID]] = {}

    # Build agent_id -> node_id mapping
    node_to_agent: dict[int, UUID] = {}
    agent_to_node: dict[UUID, int] = {}
    for node, data in G.nodes(data=True):
        aid = data.get("agent_id")
        if aid is not None:
            node_to_agent[node] = aid
            agent_to_node[aid] = node

    for u, v, data in G.edges(data=True):
        u_aid = node_to_agent.get(u)
        v_aid = node_to_agent.get(v)
        if u_aid is not None and v_aid is not None:
            w = data.get("weight", 0.5)
            edges[(u_aid, v_aid)] = w
            edges[(v_aid, u_aid)] = w
            trust_matrix[(u_aid, v_aid)] = w
            trust_matrix[(v_aid, u_aid)] = w

    for agent in agents:
        node = agent_to_node.get(agent.agent_id)
        if node is not None and G.has_node(node):
            nids = []
            for n in G.neighbors(node):
                naid = node_to_agent.get(n)
                if naid is not None:
                    nids.append(naid)
            neighbor_ids[agent.agent_id] = nids
        else:
            neighbor_ids[agent.agent_id] = []

    # Community beliefs
    community_beliefs: dict[UUID, float] = {}
    community_agents: dict[UUID, list[float]] = {}
    for agent in agents:
        community_agents.setdefault(agent.community_id, []).append(agent.belief)
    for cid, beliefs in community_agents.items():
        community_beliefs[cid] = sum(beliefs) / len(beliefs) if beliefs else 0.0

    return GraphContext(
        edges=edges,
        trust_matrix=trust_matrix,
        neighbor_ids=neighbor_ids,
        community_beliefs=community_beliefs,
    )


class StepRunner:
    """Executes a single simulation step with all sub-steps.

    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface

    Sub-steps:
        1. Get active campaign events
        2. ExposureModel.compute_exposure()
        3. For each agent: AgentTick.tick() with tier assignment
        4. Collect propagation events
        5. SentimentModel.update per community
        6. CascadeDetector.detect()
        7. MetricCollector.record()
        8. NetworkEvolver.evolve_step() if enabled
        9. Increment current_step, return StepResult
    """

    def __init__(self, llm_adapter=None, gateway=None) -> None:
        """SPEC: docs/spec/04_SIMULATION_SPEC.md"""
        from app.config import settings
        self._agent_tick = AgentTick(llm_adapter=llm_adapter, gateway=gateway)
        self._tier_selector = TierSelector()
        self._exposure_model = ExposureModel()
        self._sentiment_model = SentimentModel()
        cascade_config = CascadeConfig(
            viral_cascade_threshold=settings.cascade_viral_threshold,
            slow_adoption_steps=settings.cascade_slow_adoption_steps,
        )
        self._cascade_detector = CascadeDetector(config=cascade_config)
        self._network_evolver = NetworkEvolver()
        self._gateway = LLMGateway()
        self._negative_cascade = NegativeCascadeModel()
        from app.engine.platform.registry import PlatformRegistry
        self._platform_registry = PlatformRegistry()

    def _build_community_orchestrators(
        self,
        state: SimulationState,
    ) -> list[CommunityOrchestrator]:
        """Split agents into community groups and create per-community orchestrators.
        SPEC: docs/spec/04_SIMULATION_SPEC.md#communityorchestrator
        """
        network = state.network
        G = network.graph

        # Build agent_id -> node_id mapping from the full graph
        agent_to_node: dict[UUID, int] = {}
        for node, data in G.nodes(data=True):
            aid = data.get("agent_id")
            if aid is not None:
                agent_to_node[aid] = node

        # Collect bridge node IDs from bridge edges
        bridge_node_set: set[int] = set()
        for u, v in network.bridge_edge_ids:
            bridge_node_set.add(u)
            bridge_node_set.add(v)

        # Group agents by community_id
        community_agents: dict[UUID, list[AgentState]] = {}
        for agent in state.agents:
            community_agents.setdefault(agent.community_id, []).append(agent)

        orchestrators: list[CommunityOrchestrator] = []
        for comm_id, agents in community_agents.items():
            # Extract subgraph for this community
            node_ids = [
                agent_to_node[a.agent_id]
                for a in agents
                if a.agent_id in agent_to_node
            ]
            subgraph = G.subgraph(node_ids).copy()

            # Agent-node map for this community only
            comm_agent_node_map = {
                a.agent_id: agent_to_node[a.agent_id]
                for a in agents
                if a.agent_id in agent_to_node
            }

            # Bridge nodes that belong to this community
            comm_bridge_nodes = bridge_node_set & set(node_ids)

            # Find matching CommunityConfig (fallback to a default)
            comm_config = CommunityConfig(
                id=str(comm_id), name=str(comm_id), size=len(agents), agent_type="consumer",
            )
            for cc in state.config.communities:
                if cc.id == str(comm_id):
                    comm_config = cc
                    break

            orchestrators.append(CommunityOrchestrator(
                community_id=comm_id,
                community_config=comm_config,
                agents=agents,
                subgraph=subgraph,
                agent_node_map=comm_agent_node_map,
                bridge_node_ids=comm_bridge_nodes,
                llm_adapter=self._agent_tick._llm_adapter,
                gateway=self._gateway,
            ))

        return orchestrators

    async def execute_step(
        self,
        state: SimulationState,
        step_num: int,
    ) -> StepResult:
        """Execute one full simulation step using 3-phase community approach.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface

        Phases:
            1. Intra-Community: each community runs its agents in parallel
            2. Cross-Community Bridge: BridgePropagator reduces trust on cross edges
            3. Global Aggregation: merge results, cascade detection, metrics, evolution
        """
        start_time = time.perf_counter()

        config = state.config
        agents = state.agents
        network = state.network
        seed = (config.random_seed or 0) + step_num

        # Step 1: Campaign events
        campaign_events = _build_campaign_events(config, step_num, agents)
        env_events = _build_environment_events(campaign_events, step_num)

        # Add any injected events; process NegativeEvents via NegativeCascadeModel
        if state.injected_events:
            negative_deltas: dict[UUID, float] = {}
            remaining: list = []
            for ev in state.injected_events:
                if isinstance(ev, NegativeEvent):
                    pairs = self._negative_cascade.process_negative_event(
                        ev, agents, network
                    )
                    for aid, delta in pairs:
                        negative_deltas[aid] = negative_deltas.get(aid, 0.0) + delta
                else:
                    remaining.append(ev)
            state.injected_events.clear()
            # Apply belief deltas from negative cascade before agent ticks
            if negative_deltas:
                from dataclasses import replace as _replace
                updated_with_deltas: list[AgentState] = []
                for a in agents:
                    d = negative_deltas.get(a.agent_id, 0.0)
                    if d != 0.0:
                        new_belief = max(-1.0, min(1.0, a.belief + d))
                        updated_with_deltas.append(_replace(a, belief=new_belief))
                    else:
                        updated_with_deltas.append(a)
                state.agents = updated_with_deltas
                agents = state.agents
            env_events.extend(remaining)

        # Tier config for communities
        tier_config = TierConfig(
            max_tier3_ratio=config.llm_tier3_ratio,
            max_tier2_ratio=config.llm_tier3_ratio,
        )

        # Resolve platform RecSys config: prefer explicit config, then platform plugin
        recsys_config = config.recsys_config
        if recsys_config is None:
            platform_name = getattr(config, "platform", "default")
            try:
                plugin = self._platform_registry.get_platform(platform_name)
                recsys_config = plugin.get_feed_config()
            except (ValueError, AttributeError):
                recsys_config = None  # ExposureModel will use its own default

        # ── Phase 1: Intra-Community (parallel) ──
        community_orchs = self._build_community_orchestrators(state)
        community_results: list[CommunityTickResult] = await asyncio.gather(*[
            co.tick(
                step=step_num,
                campaign_events=campaign_events,
                env_events=env_events,
                tier_config=tier_config,
                seed=seed,
                recsys_config=recsys_config,
            )
            for co in community_orchs
        ])

        # ── Phase 2: Cross-Community Bridge ──
        bridge_propagator = BridgePropagator()
        cross_events = bridge_propagator.propagate(
            community_results,
            network.bridge_edge_ids,
            network.graph,
        )

        # ── Phase 3: Global Aggregation ──
        # Merge all updated agents from community results
        updated_agents: list[AgentState] = []
        all_propagation_events = []
        total_llm_calls = 0
        action_dist: dict[str, int] = {}

        for cr in community_results:
            for ua in cr.updated_agents:
                updated_agent = replace(ua, step=step_num + 1)
                if env_events and ua.action != AgentAction.IGNORE:
                    updated_agent = replace(
                        updated_agent,
                        exposure_count=updated_agent.exposure_count + 1,
                    )
                updated_agents.append(updated_agent)

            all_propagation_events.extend(cr.propagation_events)
            total_llm_calls += cr.llm_calls

            for action_name, count in cr.action_distribution.items():
                action_dist[action_name] = action_dist.get(action_name, 0) + count

        # Include cross-community events in propagation
        all_propagation_events.extend(cross_events)

        state.agents = updated_agents

        # Sentiment per community (already computed per-community, reuse)
        community_sentiments: dict[UUID, object] = {}
        for cr in community_results:
            if cr.community_sentiment is not None:
                community_sentiments[cr.community_id] = cr.community_sentiment

        # Fill in any missing communities via SentimentModel
        community_ids = list({a.community_id for a in updated_agents})
        for cid in community_ids:
            if cid not in community_sentiments:
                cs = self._sentiment_model.update_community_sentiment(
                    cid, updated_agents, []
                )
                community_sentiments[cid] = cs

        # Cascade detection
        total_agents = len(updated_agents)
        adopted_count = sum(1 for a in updated_agents if a.adopted)
        adoption_rate = adopted_count / total_agents if total_agents > 0 else 0.0

        cascade_step = CascadeStepResult(
            step=step_num,
            total_agents=total_agents,
            adopted_count=adopted_count,
            adoption_rate=adoption_rate,
            community_sentiments={
                cid: cs.mean_belief for cid, cs in community_sentiments.items()
            },
            community_variances={
                cid: cs.sentiment_variance for cid, cs in community_sentiments.items()
            },
            community_adoption_rates={
                cid: cs.adoption_rate for cid, cs in community_sentiments.items()
            },
            internal_links={cid: 10 for cid in community_ids},
            external_links={cid: 1 for cid in community_ids},
            adopted_agent_ids=[a.agent_id for a in updated_agents if a.adopted],
        )

        cascade_history = []
        for prev_sr in state.step_history:
            cascade_history.append(CascadeStepResult(
                step=prev_sr.step,
                total_agents=total_agents,
                adopted_count=prev_sr.total_adoption,
                adoption_rate=prev_sr.adoption_rate,
                community_sentiments={},
                community_variances={},
                community_adoption_rates={},
                internal_links={},
                external_links={},
                adopted_agent_ids=[],
            ))

        emergent_events = self._cascade_detector.detect(cascade_step, cascade_history)

        # Network evolution — build agent_id → node_id map for the full graph
        if config.enable_dynamic_edges:
            G_evolve = state.network.graph
            agent_to_node_evolve: dict = {}
            for node, data in G_evolve.nodes(data=True):
                aid = data.get("agent_id")
                if aid is not None:
                    agent_to_node_evolve[aid] = node
            state.network = self._network_evolver.evolve_step(
                state.network,
                updated_agents,
                step_num,
                node_map=agent_to_node_evolve,
            )

        # Tier distribution (approximate from community results)
        tier_dist: dict[int, int] = {}

        # Compute mean sentiment and variance across all agents
        all_beliefs = [a.belief for a in updated_agents]
        mean_sentiment = sum(all_beliefs) / len(all_beliefs) if all_beliefs else 0.0
        if len(all_beliefs) > 1:
            sentiment_var = sum(
                (b - mean_sentiment) ** 2 for b in all_beliefs
            ) / len(all_beliefs)
        else:
            sentiment_var = 0.0

        # Diffusion rate
        adoption_history = [sr.total_adoption for sr in state.step_history]
        adoption_history.append(adopted_count)
        if len(adoption_history) >= 2:
            diffusion_rate = float(adoption_history[-1] - adoption_history[-2])
            diffusion_rate = max(0.0, diffusion_rate)
        else:
            diffusion_rate = float(adopted_count)

        # Community metrics
        community_metrics: dict[str, CommunityStepMetrics] = {}
        for cid in community_ids:
            cs = community_sentiments[cid]
            comm_agents = [a for a in updated_agents if a.community_id == cid]
            comm_adopted = sum(1 for a in comm_agents if a.adopted)
            comm_rate = comm_adopted / len(comm_agents) if comm_agents else 0.0

            comm_actions = Counter(a.action for a in comm_agents)
            dominant = comm_actions.most_common(1)[0][0] if comm_actions else AgentAction.IGNORE

            comm_agent_ids = {a.agent_id for a in comm_agents}
            new_prop = sum(
                1 for pe in all_propagation_events
                if pe.source_agent_id in comm_agent_ids
            )

            community_metrics[str(cid)] = CommunityStepMetrics(
                community_id=cid,
                adoption_count=comm_adopted,
                adoption_rate=comm_rate,
                mean_belief=cs.mean_belief,
                dominant_action=dominant,
                new_propagation_count=new_prop,
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return StepResult(
            simulation_id=state.simulation_id,
            step=step_num,
            total_adoption=adopted_count,
            adoption_rate=adoption_rate,
            diffusion_rate=diffusion_rate,
            mean_sentiment=mean_sentiment,
            sentiment_variance=sentiment_var,
            community_metrics=community_metrics,
            emergent_events=emergent_events,
            action_distribution=action_dist,
            propagation_pairs=self._build_propagation_pairs(all_propagation_events),
            llm_calls_this_step=total_llm_calls,
            llm_tier_distribution=tier_dist,
            step_duration_ms=elapsed_ms,
        )


    @staticmethod
    def _build_propagation_pairs(
        events: list,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        """Convert PropagationEvents to lightweight dicts for frontend animation (GAP-7).

        SPEC: docs/spec/04_SIMULATION_SPEC.md#stepresult
        Returns top *limit* pairs sorted by probability descending.
        """
        sorted_events = sorted(events, key=lambda e: e.probability, reverse=True)[:limit]
        return [
            {
                "source": str(e.source_agent_id),
                "target": str(e.target_agent_id),
                "action": str(e.action_type),
                "probability": float(e.probability),
            }
            for e in sorted_events
        ]


__all__ = ["StepRunner"]
