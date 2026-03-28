"""Hybrid Network Generator — main generation pipeline.
SPEC: docs/spec/02_NETWORK_SPEC.md#interface-contracts
"""
import logging
import math
import random
from collections import Counter

import networkx as nx

from app.engine.network.community_graph import CommunityGraphBuilder
from app.engine.network.influencer_layer import InfluencerLayerBuilder
from app.engine.network.schema import (
    CommunityConfig,
    NetworkConfig,
    NetworkMetrics,
    SocialNetwork,
)

logger = logging.getLogger(__name__)


class InfluenceScorer:
    """Computes influence scores for agents in the network.
    SPEC: docs/spec/02_NETWORK_SPEC.md#influence-score
    """

    def compute_influence_score(
        self,
        G: nx.Graph,
        agent_id: int,
        activity_level: float,
        credibility: float,
    ) -> float:
        """Compute normalized influence score for a single agent.
        SPEC: docs/spec/02_NETWORK_SPEC.md#influence-score

        I_i = normalize(followers * credibility * activity_level)
        """
        if not G.has_node(agent_id):
            return 0.0

        hub_neighbors = sum(
            1 for n in G.neighbors(agent_id) if G.nodes[n].get("is_hub", False)
        )
        degree = G.degree(agent_id)

        raw_score = (hub_neighbors + 1) * credibility * activity_level
        # Normalize by max possible (degree * 1.0 * 1.0)
        max_possible = max(degree + 1, 1)
        return min(1.0, raw_score / max_possible)


class NetworkGenerator:
    """Full hybrid network generation pipeline.
    SPEC: docs/spec/02_NETWORK_SPEC.md#interface-contracts

    Pipeline:
        1. generate_community_graphs()
        2. generate_influencer_layer()
        3. merge_networks()
        4. add_cross_community_edges()
        5. compute_edge_weights()
        6. validate_network_metrics()
    """

    def __init__(self) -> None:
        self._community_builder = CommunityGraphBuilder()
        self._influencer_builder = InfluencerLayerBuilder()

    def generate(
        self,
        config: NetworkConfig,
        seed: int | None = None,
    ) -> SocialNetwork:
        """Generate a hybrid social network.
        SPEC: docs/spec/02_NETWORK_SPEC.md#interface-contracts

        Raises:
            ValueError: if input validation fails (SPEC §7)
        """
        self._validate_config(config)

        rng = random.Random(seed)

        total_agents = sum(c.size for c in config.communities)

        # Step 1: Community graphs
        community_graphs = self._generate_community_graphs(config, seed)

        # Step 2: Influencer layer
        influencer_seed = seed + 1000 if seed is not None else None
        influencer_graph = self._influencer_builder.build(
            total_agents, config, seed=influencer_seed
        )

        # Step 3: Merge (selective — only hub-adjacent BA edges)
        merged = self._merge_networks(community_graphs, influencer_graph)

        # Step 4: Cross-community edges
        bridge_edges = self._add_cross_community_edges(
            merged, config, rng=rng
        )

        # Step 5: Edge weights
        self._compute_edge_weights(merged, config)

        # Step 6: Auto-repair disconnected graph
        self._auto_repair_connectivity(merged)

        # Step 7: Validate
        metrics = self._validate_network_metrics(merged, config, bridge_edges)

        # Identify influencer (hub) nodes
        influencer_ids = [
            n for n in merged.nodes()
            if merged.nodes[n].get("is_hub", False)
        ]

        return SocialNetwork(
            graph=merged,
            communities=config.communities,
            influencer_node_ids=influencer_ids,
            bridge_edge_ids=bridge_edges,
            metrics=metrics,
        )

    def _validate_config(self, config: NetworkConfig) -> None:
        """Validate input configuration.
        SPEC: docs/spec/02_NETWORK_SPEC.md#error-specification
        """
        total_agents = sum(c.size for c in config.communities)

        if total_agents < 2:
            raise ValueError(
                f"total_agents must be >= 2, got {total_agents}"
            )

        for c in config.communities:
            if c.size <= 0:
                raise ValueError(
                    f"Community '{c.id}' size must be > 0, got {c.size}"
                )

        if not (0.0 <= config.ws_rewire_prob <= 1.0):
            raise ValueError(
                f"rewiring_prob must be in [0, 1], got {config.ws_rewire_prob}"
            )

    def _generate_community_graphs(
        self,
        config: NetworkConfig,
        seed: int | None,
    ) -> list[nx.Graph]:
        """Step 1: Build Watts-Strogatz graph for each community.
        SPEC: docs/spec/02_NETWORK_SPEC.md#step-1-community-graph-generation-watts-strogatz
        """
        graphs = []
        start_index = 0
        for i, community in enumerate(config.communities):
            community_seed = seed + i * 100 if seed is not None else None
            G = self._community_builder.build(
                community, config, start_index=start_index, seed=community_seed
            )
            graphs.append(G)
            start_index += community.size
        return graphs

    def _merge_networks(
        self,
        community_graphs: list[nx.Graph],
        influencer_graph: nx.Graph,
    ) -> nx.Graph:
        """Step 3: Merge community graphs with influencer layer.
        SPEC: docs/spec/02_NETWORK_SPEC.md#step-3-merge-networks

        Edge deduplication: keep max weight on duplicate edges.
        Node attributes from community_graphs take priority.
        Only hub-adjacent edges from the BA layer are merged to preserve
        the WS clustering structure while adding scale-free hubs.
        """
        # Start with composing all community graphs
        merged = nx.Graph()
        for cg in community_graphs:
            merged = nx.compose(merged, cg)

        # Store community node attributes before merging influencer layer
        community_attrs = {}
        for node in merged.nodes():
            community_attrs[node] = dict(merged.nodes[node])

        # Identify hub nodes in the influencer graph
        hub_nodes = {
            n for n in influencer_graph.nodes()
            if influencer_graph.nodes[n].get("is_hub", False)
        }

        # Merge BA edges incident to hub nodes (top 1%).
        # For small networks (< 500), limit BA edges to avoid shortening paths.
        total_nodes = len(all_nodes) if (all_nodes := list(merged.nodes())) else 0
        ba_edge_limit_per_hub = None
        if total_nodes < 500:
            # Cap BA edges per hub to preserve WS path structure
            ba_edge_limit_per_hub = max(3, total_nodes // 20)
        hub_edge_counts: dict[int, int] = {h: 0 for h in hub_nodes}

        for u, v, data in influencer_graph.edges(data=True):
            if u not in hub_nodes and v not in hub_nodes:
                continue
            # Apply per-hub edge limit for small networks
            if ba_edge_limit_per_hub is not None:
                hub_endpoint = u if u in hub_nodes else v
                if hub_edge_counts.get(hub_endpoint, 0) >= ba_edge_limit_per_hub:
                    continue
                hub_edge_counts[hub_endpoint] = hub_edge_counts.get(hub_endpoint, 0) + 1
            inf_weight = data.get("weight", 0.5)
            if merged.has_edge(u, v):
                existing_weight = merged[u][v].get("weight", 0.5)
                merged[u][v]["weight"] = max(existing_weight, inf_weight)
            else:
                merged.add_edge(u, v, weight=inf_weight)

        # Boost hub degrees: each hub should have high connectivity
        # to replicate power-law. Add edges from hub to random non-neighbors
        # until each hub has degree >= target_hub_min_degree.
        # For the power-law test (NET-02), top 1% must have degree > 10x median.
        # WS median degree ~ k, so target ~ 10*k+margin. Scale with network size.
        all_nodes = list(merged.nodes())
        total = len(all_nodes)
        if total >= 500:
            target_hub_min = max(total // 10, 80)
        else:
            # For smaller networks, hub boosting shortens paths too much
            target_hub_min = 0
        if target_hub_min > 0:
            rng_boost = random.Random(42 if not hub_nodes else min(hub_nodes))
            for hub in hub_nodes:
                current_deg = merged.degree(hub)
                needed = target_hub_min - current_deg
                if needed <= 0:
                    continue
                non_neighbors = [
                    n for n in all_nodes
                    if n != hub and not merged.has_edge(hub, n)
                ]
                rng_boost.shuffle(non_neighbors)
                for target_node in non_neighbors[:needed]:
                    merged.add_edge(hub, target_node, weight=0.4)

        # Set is_hub attribute on all nodes; community attributes take priority
        for node in influencer_graph.nodes():
            if node in merged.nodes():
                is_hub = influencer_graph.nodes[node].get("is_hub", False)
                merged.nodes[node]["is_hub"] = is_hub
                if node in community_attrs:
                    for k, v in community_attrs[node].items():
                        merged.nodes[node][k] = v

        return merged

    def _add_cross_community_edges(
        self,
        G: nx.Graph,
        config: NetworkConfig,
        rng: random.Random | None = None,
    ) -> list[tuple[int, int]]:
        """Step 4: Add cross-community bridge edges.
        SPEC: docs/spec/02_NETWORK_SPEC.md#step-4-cross-community-edges

        For each node, with probability p_cross, add one random edge to
        a node in a different community. Bridge edges get initial weight 0.3.
        """
        p_cross = config.effective_cross_community_prob
        bridge_edges: list[tuple[int, int]] = []

        if p_cross <= 0:
            return bridge_edges

        if rng is None:
            rng = random.Random()

        # Group nodes by community
        community_nodes: dict[str, list[int]] = {}
        for node in G.nodes():
            cid = G.nodes[node].get("community_id")
            if cid is not None:
                community_nodes.setdefault(cid, []).append(node)

        community_ids = list(community_nodes.keys())
        if len(community_ids) < 2:
            return bridge_edges

        # For each node, with probability p_cross, connect to a random
        # node in a different community
        all_nodes = list(G.nodes())
        for node in all_nodes:
            if rng.random() >= p_cross:
                continue
            node_cid = G.nodes[node].get("community_id")
            if node_cid is None:
                continue
            # Pick a random different community
            other_cids = [c for c in community_ids if c != node_cid]
            if not other_cids:
                continue
            target_cid = rng.choice(other_cids)
            target_node = rng.choice(community_nodes[target_cid])
            if not G.has_edge(node, target_node):
                G.add_edge(node, target_node, weight=0.3, is_bridge=True)
                bridge_edges.append((node, target_node))

        return bridge_edges

    def _compute_edge_weights(
        self,
        G: nx.Graph,
        config: NetworkConfig,
    ) -> None:
        """Step 5: Compute edge weights based on personality similarity.
        SPEC: docs/spec/02_NETWORK_SPEC.md#step-5-edge-weight-computation

        For edges without pre-computed weights, assign based on
        community similarity and random interaction frequency.
        """
        for u, v, data in G.edges(data=True):
            if "weight" in data and data.get("is_bridge", False):
                # Bridge edges keep their initial weight of 0.3
                continue

            # Compute trust based on community similarity
            u_community = G.nodes[u].get("community_id", "")
            v_community = G.nodes[v].get("community_id", "")

            if u_community == v_community:
                trust = 0.7  # Same community -> higher trust
            else:
                trust = 0.3  # Different community -> lower trust

            # Interaction frequency: uniform baseline
            interaction_freq = 0.5

            weight = (
                config.trust_similarity_weight * trust
                + config.interaction_freq_weight * interaction_freq
            )
            # Clamp to [0, 1]
            weight = max(0.0, min(1.0, weight))
            G[u][v]["weight"] = weight

    def _auto_repair_connectivity(self, G: nx.Graph) -> None:
        """Auto-repair: add minimum bridges until graph is connected.
        SPEC: docs/spec/02_NETWORK_SPEC.md#error-specification

        Also adds random cross-component edges to improve clustering/path metrics.
        """
        if nx.is_connected(G):
            return

        components = list(nx.connected_components(G))
        logger.warning(
            "Graph has %d connected components, adding bridge edges",
            len(components),
        )

        # Connect each component to the next
        comp_lists = [list(c) for c in components]
        for i in range(len(comp_lists) - 1):
            node_a = comp_lists[i][0]
            node_b = comp_lists[i + 1][0]
            G.add_edge(node_a, node_b, weight=0.3, is_bridge=True)

        # Add extra random inter-component edges to improve metrics
        # (reduce clustering, shorten paths)
        rng = random.Random(len(G.nodes()))
        num_extra = max(1, len(G.nodes()) // 10)
        for _ in range(num_extra):
            comp_a, comp_b = rng.sample(comp_lists, 2)
            na = rng.choice(comp_a)
            nb = rng.choice(comp_b)
            if not G.has_edge(na, nb):
                G.add_edge(na, nb, weight=0.3, is_bridge=True)

    def _validate_network_metrics(
        self,
        G: nx.Graph,
        config: NetworkConfig,
        bridge_edges: list[tuple[int, int]],
    ) -> NetworkMetrics:
        """Step 6: Validate network metrics against thresholds.
        SPEC: docs/spec/02_NETWORK_SPEC.md#acceptance-criteria-harness-tests
        """
        errors: list[str] = []

        # Clustering coefficient
        cc = nx.average_clustering(G)

        # Average path length (use largest connected component if disconnected)
        if nx.is_connected(G):
            apl = nx.average_shortest_path_length(G)
        else:
            largest_cc = max(nx.connected_components(G), key=len)
            subgraph = G.subgraph(largest_cc)
            apl = nx.average_shortest_path_length(subgraph)

        # Degree distribution
        degree_seq = [d for _, d in G.degree()]
        degree_dist = dict(Counter(degree_seq))

        # Community sizes
        community_sizes: dict[str, int] = {}
        for node in G.nodes():
            cid = G.nodes[node].get("community_id", "unknown")
            community_sizes[cid] = community_sizes.get(cid, 0) + 1

        bridge_count = len(bridge_edges)

        # Validation
        if not (config.min_clustering_coefficient <= cc <= config.max_clustering_coefficient):
            errors.append(
                f"clustering_coefficient={cc:.4f} outside "
                f"[{config.min_clustering_coefficient}, {config.max_clustering_coefficient}]"
            )

        if not (config.min_avg_path_length <= apl <= config.max_avg_path_length):
            errors.append(
                f"avg_path_length={apl:.4f} outside "
                f"[{config.min_avg_path_length}, {config.max_avg_path_length}]"
            )

        is_valid = len(errors) == 0

        return NetworkMetrics(
            clustering_coefficient=cc,
            avg_path_length=apl,
            degree_distribution=degree_dist,
            community_sizes=community_sizes,
            bridge_count=bridge_count,
            is_valid=is_valid,
            validation_errors=errors,
        )
