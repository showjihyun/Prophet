"""Dynamic network evolution.
SPEC: docs/spec/02_NETWORK_SPEC.md#dynamic-network-evolution
"""
import logging
from typing import Any

from app.engine.network.schema import EvolutionConfig, SocialNetwork

logger = logging.getLogger(__name__)


class NetworkEvolver:
    """Evolves network edge weights based on agent actions each step.
    SPEC: docs/spec/02_NETWORK_SPEC.md#dynamic-network-evolution
    """

    def __init__(self, config: EvolutionConfig | None = None) -> None:
        self.config = config or EvolutionConfig()

    def evolve_step(
        self,
        network: SocialNetwork,
        actions: list[Any],
        step: int,
        node_map: dict | None = None,
    ) -> SocialNetwork:
        """Evolve the network based on agent actions for one simulation step.
        SPEC: docs/spec/02_NETWORK_SPEC.md#dynamic-network-evolution

        Empty action list returns unchanged network.
        """
        if not actions:
            return network

        # Shallow copy the graph structure (NetworkX .copy() creates new edge dicts)
        new_graph = network.graph.copy()

        for result in actions:
            agent_id = result.agent_id
            action = result.action

            # Get action name as string for comparison
            action_name = action.value if hasattr(action, "value") else str(action)

            # Map UUID agent_id to integer node_id if node_map provided
            graph_node = node_map.get(agent_id, agent_id) if node_map else agent_id

            neighbors = list(new_graph.neighbors(graph_node)) if new_graph.has_node(graph_node) else []

            if action_name == "share":
                for neighbor in neighbors:
                    self.update_edge_weight(
                        new_graph, (graph_node, neighbor), self.config.share_weight_boost
                    )
            elif action_name == "ignore":
                for neighbor in neighbors:
                    self.update_edge_weight(
                        new_graph, (graph_node, neighbor), -self.config.ignore_weight_decay
                    )
            elif action_name == "adopt":
                for neighbor in neighbors:
                    self.update_edge_weight(
                        new_graph, (graph_node, neighbor), self.config.adopt_trust_boost
                    )

        # Prune edges below min_weight
        if self.config.enable_dynamic_edges:
            edges_to_remove = [
                (u, v)
                for u, v, d in new_graph.edges(data=True)
                if d.get("weight", 1.0) < self.config.min_edge_weight
            ]
            new_graph.remove_edges_from(edges_to_remove)

        # Cap total edges to prevent unbounded growth
        # SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md — scalability A-
        max_edges = 100_000  # domain default
        if new_graph.number_of_edges() > max_edges:
            # Remove weakest edges until under cap
            sorted_edges = sorted(
                new_graph.edges(data=True),
                key=lambda e: e[2].get("weight", 0.5),
            )
            excess = new_graph.number_of_edges() - max_edges
            new_graph.remove_edges_from(
                [(u, v) for u, v, _ in sorted_edges[:excess]]
            )

        # Return updated network with new graph
        return SocialNetwork(
            graph=new_graph,
            communities=network.communities,
            influencer_node_ids=network.influencer_node_ids,
            bridge_edge_ids=network.bridge_edge_ids,
            metrics=network.metrics,
        )

    def update_edge_weight(
        self, graph: Any, edge: tuple, delta: float
    ) -> None:
        """Update edge weight by delta, clamped to [0, 1].
        SPEC: docs/spec/02_NETWORK_SPEC.md#error-specification

        Missing edges are silently skipped.
        """
        # Handle dict-like or nx.Graph
        if isinstance(graph, dict):
            logger.debug("Skipping edge weight update on dict graph for edge %s", edge)
            return

        u, v = edge
        if not graph.has_edge(u, v):
            logger.debug("Skipping update for non-existent edge (%s, %s)", u, v)
            return

        current = graph[u][v].get("weight", 0.5)
        new_weight = max(0.0, min(1.0, current + delta))
        graph[u][v]["weight"] = new_weight
