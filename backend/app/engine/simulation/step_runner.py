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
from app.engine.diffusion.schema import CampaignEvent, EmergentEvent, RecSysConfig
from app.engine.diffusion.sentiment_model import SentimentModel
from app.engine.network.evolution import NetworkEvolver
from app.engine.network.schema import SocialNetwork

from app.engine.simulation.schema import (
    CampaignConfig,
    CommunityStepMetrics,
    SimulationConfig,
    StepResult,
)

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
        target_ids = all_community_ids  # Simplified: target all for now

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

    def __init__(self, llm_adapter=None) -> None:
        """SPEC: docs/spec/04_SIMULATION_SPEC.md"""
        self._agent_tick = AgentTick(llm_adapter=llm_adapter)
        self._tier_selector = TierSelector()
        self._exposure_model = ExposureModel()
        self._sentiment_model = SentimentModel()
        self._cascade_detector = CascadeDetector()
        self._network_evolver = NetworkEvolver()

    async def execute_step(
        self,
        state: SimulationState,
        step_num: int,
    ) -> StepResult:
        """Execute one full simulation step.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
        """
        start_time = time.perf_counter()

        config = state.config
        agents = state.agents
        network = state.network
        seed = (config.random_seed or 0) + step_num

        # Step 1: Campaign events
        campaign_events = _build_campaign_events(config, step_num, agents)
        env_events = _build_environment_events(campaign_events, step_num)

        # Add any injected events
        if state.injected_events:
            env_events.extend(state.injected_events)
            state.injected_events.clear()

        # Step 2: Exposure (skip if no agents — shouldn't happen)
        # ExposureModel needs agents, but we can skip if no campaign
        # For simplicity, we pass exposure info via environment events

        # Step 3: Tier assignment
        tier_config = TierConfig(
            max_tier3_ratio=config.llm_tier3_ratio,
            max_tier2_ratio=config.llm_tier3_ratio,  # Use same ratio for tier2
        )
        tier_assignments = self._tier_selector.assign_tiers(agents, tier_config, seed)

        # Step 4: Build graph context
        graph_context = _build_graph_context(network, agents)

        # Step 5: Execute agent ticks
        # Build neighbor actions from previous step
        neighbor_actions_map: dict[UUID, list[NeighborAction]] = {}
        for agent in agents:
            nids = graph_context.neighbor_ids.get(agent.agent_id, [])
            na_list = []
            for nid in nids:
                # Find neighbor's last action
                for other in agents:
                    if other.agent_id == nid and other.action != AgentAction.IGNORE:
                        na_list.append(
                            NeighborAction(
                                agent_id=nid,
                                action=other.action,
                                content_id=uuid4(),
                                step=step_num,
                            )
                        )
                        break
            neighbor_actions_map[agent.agent_id] = na_list

        # Run all agent ticks
        tick_results: list[AgentTickResult] = []
        all_propagation_events = []

        for agent in agents:
            tier = tier_assignments.get(agent.agent_id, 1)
            neighbor_actions = neighbor_actions_map.get(agent.agent_id, [])

            result = self._agent_tick.tick(
                agent=agent,
                environment_events=env_events,
                neighbor_actions=neighbor_actions,
                cognition_tier=tier,
                seed=seed,
                graph_context=graph_context,
            )
            tick_results.append(result)
            all_propagation_events.extend(result.propagation_events)

        # Step 6: Update agent states
        updated_agents: list[AgentState] = []
        for tr in tick_results:
            updated = replace(tr.updated_state, step=step_num + 1)
            # Increment exposure_count if the agent saw campaign content
            if env_events and tr.action != AgentAction.IGNORE:
                updated = replace(updated, exposure_count=updated.exposure_count + 1)
            updated_agents.append(updated)
        state.agents = updated_agents

        # Step 7: Sentiment per community
        community_ids = list({a.community_id for a in updated_agents})
        community_sentiments = {}
        for cid in community_ids:
            cs = self._sentiment_model.update_community_sentiment(
                cid, updated_agents, []
            )
            community_sentiments[cid] = cs

        # Step 8: Cascade detection
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

        # Step 9: Network evolution
        if config.enable_dynamic_edges:
            # Build simple action results for evolver
            action_results = []
            for tr in tick_results:
                action_results.append(tr.updated_state)
            state.network = self._network_evolver.evolve(network, action_results, step_num)

        # Step 10: Build StepResult
        action_dist: dict[str, int] = {}
        tier_dist: dict[int, int] = {}
        llm_calls = 0
        for tr in tick_results:
            action_name = tr.action.value
            action_dist[action_name] = action_dist.get(action_name, 0) + 1
            if tr.llm_tier_used is not None:
                tier_dist[tr.llm_tier_used] = tier_dist.get(tr.llm_tier_used, 0) + 1
                if tr.llm_tier_used >= 2:
                    llm_calls += 1

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

            # Dominant action
            comm_actions = Counter(a.action for a in comm_agents)
            dominant = comm_actions.most_common(1)[0][0] if comm_actions else AgentAction.IGNORE

            # Propagation count for this community
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
            llm_calls_this_step=llm_calls,
            llm_tier_distribution=tier_dist,
            step_duration_ms=elapsed_ms,
        )


__all__ = ["StepRunner"]
