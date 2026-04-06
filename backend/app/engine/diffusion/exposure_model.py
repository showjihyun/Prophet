"""RecSys-inspired Exposure Model.
SPEC: docs/spec/03_DIFFUSION_SPEC.md#exposuremodel-recsys-inspired-oasis-차용
"""
import logging
from uuid import UUID

from app.engine.agent.schema import AgentState
from app.engine.network.schema import SocialNetwork
from app.engine.diffusion.schema import (
    CampaignEvent,
    ExposureResult,
    FeedItem,
    RecSysConfig,
)

logger = logging.getLogger(__name__)


class ExposureModel:
    """RecSys-inspired exposure model that simulates algorithmic feed curation.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#exposuremodel-recsys-inspired-oasis-차용

    Two-phase exposure:
        Phase 1 — Candidate Generation: all content available this step.
        Phase 2 — RecSys Feed Ranking: weighted scoring, top-K selection.

    Error behavior:
        - Empty agent list → raise ValueError
        - RecSysConfig weight sum != 1.0 (±0.01) → ValueError (at config level)
        - No active campaign → all exposure scores 0.0
    """

    def __init__(self, recsys_config: RecSysConfig | None = None) -> None:
        self._config = recsys_config or RecSysConfig()

    def compute_exposure(
        self,
        agents: list[AgentState],
        graph: SocialNetwork,
        active_events: list[CampaignEvent],
        step: int,
        recsys_config: RecSysConfig | None = None,
        agent_node_map: dict[UUID, int] | None = None,
    ) -> dict[UUID, ExposureResult]:
        """Compute exposure for all agents.

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#exposuremodel-recsys-inspired-oasis-차용

        Returns dict of agent_id -> ExposureResult.

        Args:
            agent_node_map: Optional pre-built map of agent_id -> node id for O(1)
                lookups (PERF-01). When provided, avoids O(N) linear node scans.
        """
        if not agents:
            raise ValueError("ExposureModel.compute_exposure: agents list must not be empty")

        config = recsys_config or self._config

        # No active campaign → all scores 0.0
        if not active_events:
            logger.debug("No active campaigns at step %d, all exposure scores = 0.0", step)
            return {
                agent.agent_id: ExposureResult(
                    agent_id=agent.agent_id,
                    exposure_score=0.0,
                    exposed_events=[],
                    social_feed=[],
                    suppressed_count=0,
                    is_directly_exposed=False,
                    feed_diversity_score=0.0,
                )
                for agent in agents
            }

        results: dict[UUID, ExposureResult] = {}

        for agent in agents:
            # Phase 1: Candidate Generation
            candidates = self._generate_candidates(
                agent, graph, active_events, step, agent_node_map=agent_node_map
            )

            # Phase 2: RecSys Feed Ranking
            ranked = self._rank_feed(candidates, agent, graph, config, agent_node_map=agent_node_map)

            # Top-K selection
            top_k = ranked[: config.feed_capacity]
            suppressed_count = max(0, len(ranked) - config.feed_capacity)

            # Compute exposure score
            if top_k:
                exposure_score = min(
                    1.0,
                    sum(item.feed_rank_score for item in top_k) / len(top_k),
                )
            else:
                exposure_score = 0.0

            # Determine direct exposure (agent's community is a target)
            is_directly_exposed = any(
                agent.community_id in event.target_communities
                for event in active_events
            )

            # Exposed events: campaigns present in the feed
            exposed_campaign_ids = {
                item.campaign_id for item in top_k if item.campaign_id is not None
            }
            exposed_events = [
                e for e in active_events if e.campaign_id in exposed_campaign_ids
            ]

            # Feed diversity score
            feed_diversity_score = self._compute_diversity(top_k)

            results[agent.agent_id] = ExposureResult(
                agent_id=agent.agent_id,
                exposure_score=exposure_score,
                exposed_events=exposed_events,
                social_feed=top_k,
                suppressed_count=suppressed_count,
                is_directly_exposed=is_directly_exposed,
                feed_diversity_score=feed_diversity_score,
            )

        return results

    def _generate_candidates(
        self,
        agent: AgentState,
        graph: SocialNetwork,
        active_events: list[CampaignEvent],
        step: int,
        agent_node_map: dict[UUID, int] | None = None,
    ) -> list[FeedItem]:
        """Phase 1: Generate all candidate feed items for an agent.

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#exposuremodel-recsys-inspired-oasis-차용

        Args:
            agent_node_map: Optional pre-built map for O(1) node lookups (PERF-02).
        """
        candidates: list[FeedItem] = []

        # Campaign content as feed items
        for event in active_events:
            if event.start_step <= step <= event.end_step:
                candidates.append(
                    FeedItem(
                        source_agent_id=None,
                        campaign_id=event.campaign_id,
                        feed_rank_score=0.0,  # Will be scored in Phase 2
                        ad_boost_score=event.budget,
                    )
                )

        # Neighbor-shared content (simplified: each neighbor is a source)
        nx_graph = graph.graph
        # PERF-02: use pre-built map for O(1) lookup; fall back to O(N) scan
        if agent_node_map is not None:
            agent_node = agent_node_map.get(agent.agent_id)
        else:
            agent_node = self._find_agent_node(agent, nx_graph)

        if agent_node is not None and nx_graph.has_node(agent_node):
            # PERF-16: build reverse map once from agent_node_map to avoid O(N) per neighbor
            if agent_node_map is not None:
                node_to_agent = {v: k for k, v in agent_node_map.items()}
            else:
                node_to_agent = None

            for neighbor in nx_graph.neighbors(agent_node):
                if node_to_agent is not None:
                    source_id = node_to_agent.get(neighbor)
                else:
                    source_id = self._get_node_agent_id(neighbor, nx_graph)
                candidates.append(
                    FeedItem(
                        source_agent_id=source_id,
                        campaign_id=None,
                        feed_rank_score=0.0,
                    )
                )

        return candidates

    def _rank_feed(
        self,
        candidates: list[FeedItem],
        agent: AgentState,
        graph: SocialNetwork,
        config: RecSysConfig,
        agent_node_map: dict[UUID, int] | None = None,
    ) -> list[FeedItem]:
        """Phase 2: Rank feed items using RecSys weights.

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#exposuremodel-recsys-inspired-oasis-차용

        feed_rank_score = w1*recency + w2*social_affinity + w3*interest_match
                        + w4*engagement_signal + w5*ad_boost

        Args:
            agent_node_map: Optional pre-built map for O(1) node lookups (PERF-03).
        """
        scored: list[FeedItem] = []
        seen_sources: dict[UUID | None, int] = {}

        # PERF-03: resolve agent node once outside the per-item loop
        nx_graph = graph.graph
        if agent_node_map is not None:
            agent_node = agent_node_map.get(agent.agent_id)
        else:
            agent_node = self._find_agent_node(agent, nx_graph)

        for item in candidates:
            # Recency: newer items score higher (simplified: all same step = 1.0)
            recency = 1.0

            # Social affinity: trust to content source
            social_affinity = 0.0
            if item.source_agent_id is not None:
                # PERF-03: use pre-built map for O(1) lookup; fall back to O(N) scan
                if agent_node_map is not None:
                    source_node = agent_node_map.get(item.source_agent_id)
                else:
                    source_node = self._find_agent_id_node(item.source_agent_id, nx_graph)
                if (
                    agent_node is not None
                    and source_node is not None
                    and nx_graph.has_edge(agent_node, source_node)
                ):
                    edge_data = nx_graph[agent_node][source_node]
                    social_affinity = edge_data.get("weight", 0.5)

            # Interest match: personality alignment (openness + trend_following)
            interest_match = (
                agent.personality.openness * 0.5
                + agent.personality.trend_following * 0.5
            )

            # Engagement signal: simplified as campaign novelty or 0.5 default
            engagement_signal = 0.5
            if item.campaign_id is not None:
                # Campaign items may have higher engagement
                engagement_signal = 0.7

            # Ad boost: normalized budget
            ad_boost = min(1.0, item.ad_boost_score) if item.ad_boost_score > 0 else 0.0

            # Diversity penalty: penalize repeated same-source content
            source_key = item.source_agent_id or item.campaign_id
            count = seen_sources.get(source_key, 0)
            diversity_adj = count * config.diversity_penalty
            seen_sources[source_key] = count + 1

            # Final score
            score = (
                config.w_recency * recency
                + config.w_social_affinity * social_affinity
                + config.w_interest_match * interest_match
                + config.w_engagement_signal * engagement_signal
                + config.w_ad_boost * ad_boost
                - diversity_adj
            )

            scored.append(
                FeedItem(
                    source_agent_id=item.source_agent_id,
                    campaign_id=item.campaign_id,
                    feed_rank_score=max(0.0, score),
                    recency_score=recency,
                    social_affinity_score=social_affinity,
                    interest_match_score=interest_match,
                    engagement_signal_score=engagement_signal,
                    ad_boost_score=ad_boost,
                )
            )

        # Sort by feed_rank_score descending
        scored.sort(key=lambda x: x.feed_rank_score, reverse=True)
        return scored

    def _compute_diversity(self, feed: list[FeedItem]) -> float:
        """Compute feed diversity score (0-1, higher = more diverse).

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#exposuremodel-recsys-inspired-oasis-차용
        """
        if not feed:
            return 0.0

        unique_sources: set[UUID | None] = set()
        for item in feed:
            unique_sources.add(item.source_agent_id or item.campaign_id)

        return min(1.0, len(unique_sources) / max(1, len(feed)))

    @staticmethod
    def _find_agent_node(agent: AgentState, nx_graph) -> int | None:  # noqa: ANN001
        """Find the networkx node ID for an agent."""
        for node, data in nx_graph.nodes(data=True):
            if data.get("agent_id") == agent.agent_id:
                return node
        return None

    @staticmethod
    def _find_agent_id_node(agent_id: UUID, nx_graph) -> int | None:  # noqa: ANN001
        """Find the networkx node ID for an agent_id."""
        for node, data in nx_graph.nodes(data=True):
            if data.get("agent_id") == agent_id:
                return node
        return None

    @staticmethod
    def _get_node_agent_id(node: int, nx_graph) -> UUID | None:  # noqa: ANN001
        """Get agent_id from a node."""
        return nx_graph.nodes[node].get("agent_id")


__all__ = ["ExposureModel"]
