"""Community graph builder using Watts-Strogatz small-world model.
SPEC: docs/spec/02_NETWORK_SPEC.md#step-1-community-graph-generation-watts-strogatz
"""
import logging

import networkx as nx

from app.engine.network.schema import CommunityConfig, NetworkConfig

logger = logging.getLogger(__name__)


class CommunityGraphBuilder:
    """Builds a Watts-Strogatz small-world graph for a single community.
    SPEC: docs/spec/02_NETWORK_SPEC.md#step-1-community-graph-generation-watts-strogatz
    """

    def build(
        self,
        community: CommunityConfig,
        config: NetworkConfig,
        start_index: int = 0,
        seed: int | None = None,
    ) -> nx.Graph:
        """Build a Watts-Strogatz graph for the given community.
        SPEC: docs/spec/02_NETWORK_SPEC.md#step-1-community-graph-generation-watts-strogatz

        Nodes are relabeled to [start_index, start_index + size).
        Node attributes: community_id, agent_type.

        Handles k >= n error: reduce k to min(n-1, k), must be even,
        retry up to 3 times.
        """
        n = community.size
        k = config.ws_k_neighbors
        p = config.ws_rewire_prob

        max_retries = 3
        for attempt in range(max_retries):
            effective_k = min(k, n - 1)
            # k must be even for Watts-Strogatz
            if effective_k % 2 != 0:
                effective_k = max(effective_k - 1, 2)
            # Minimum k is 2
            effective_k = max(effective_k, 2)

            if effective_k != k:
                logger.warning(
                    "Community '%s' (size=%d): reduced k from %d to %d (attempt %d)",
                    community.id, n, k, effective_k, attempt + 1,
                )

            # For very small n where even k=2 is problematic, just use a complete graph
            if n <= 2:
                G = nx.complete_graph(n)
                break

            try:
                current_seed = seed + attempt if seed is not None else None
                G = nx.watts_strogatz_graph(n, effective_k, p, seed=current_seed)
                break
            except nx.NetworkXError:
                if attempt == max_retries - 1:
                    # Last resort: complete graph
                    logger.warning(
                        "Community '%s': falling back to complete graph after %d retries",
                        community.id, max_retries,
                    )
                    G = nx.complete_graph(n)
                continue

        # Relabel nodes to [start_index, start_index + size)
        mapping = {old: old + start_index for old in G.nodes()}
        G = nx.relabel_nodes(G, mapping)

        # Set node attributes
        for node in G.nodes():
            G.nodes[node]["community_id"] = community.id
            G.nodes[node]["agent_type"] = community.agent_type

        return G
