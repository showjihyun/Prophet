"""Influencer layer builder using Barabasi-Albert preferential attachment.
SPEC: docs/spec/02_NETWORK_SPEC.md#step-2-influencer-layer-barabasi-albert
"""
import logging
import math

import networkx as nx

from app.engine.network.schema import NetworkConfig

logger = logging.getLogger(__name__)


class InfluencerLayerBuilder:
    """Builds a Barabasi-Albert scale-free graph for the influencer layer.
    SPEC: docs/spec/02_NETWORK_SPEC.md#step-2-influencer-layer-barabasi-albert
    """

    def build(
        self,
        total_agents: int,
        config: NetworkConfig,
        seed: int | None = None,
    ) -> nx.Graph:
        """Build a Barabasi-Albert graph over all agents.
        SPEC: docs/spec/02_NETWORK_SPEC.md#step-2-influencer-layer-barabasi-albert

        Tags top 1% degree nodes as 'hub'.
        Handles m > existing_nodes: clamp m.
        """
        m = config.ba_m_edges

        # Clamp m if it exceeds total_agents - 1
        if m >= total_agents:
            logger.warning(
                "BA m=%d >= total_agents=%d, clamping to %d",
                m, total_agents, total_agents - 1,
            )
            m = max(1, total_agents - 1)

        G = nx.barabasi_albert_graph(total_agents, m, seed=seed)

        # Tag top 1% degree nodes as 'hub'
        degrees = sorted(G.degree(), key=lambda x: x[1], reverse=True)
        top_1pct_count = max(1, math.ceil(len(degrees) * 0.01))
        hub_nodes = {node for node, _ in degrees[:top_1pct_count]}

        for node in G.nodes():
            G.nodes[node]["is_hub"] = node in hub_nodes

        return G
