"""Network data types.
SPEC: docs/spec/02_NETWORK_SPEC.md
"""
from dataclasses import dataclass, field

import networkx as nx


@dataclass
class CommunityConfig:
    """Configuration for a single community.
    SPEC: docs/spec/02_NETWORK_SPEC.md#default-community-configuration
    """
    id: str
    name: str
    size: int
    agent_type: str
    personality_profile: dict[str, float] = field(default_factory=dict)


@dataclass
class NetworkConfig:
    """Configuration for network generation.
    SPEC: docs/spec/02_NETWORK_SPEC.md#interface-contracts
    """
    communities: list[CommunityConfig] = field(default_factory=list)

    # Watts-Strogatz parameters
    ws_k_neighbors: int = 6
    ws_rewire_prob: float = 0.1

    # Barabasi-Albert parameters
    ba_m_edges: int = 3

    # Cross-community edges
    cross_community_prob: float = 0.02

    # Edge weight
    trust_similarity_weight: float = 0.6
    interaction_freq_weight: float = 0.4

    # Validation thresholds
    min_clustering_coefficient: float = 0.2
    max_clustering_coefficient: float = 0.6
    min_avg_path_length: float = 3.0
    max_avg_path_length: float = 7.0

    # Alias: rewiring_prob maps to ws_rewire_prob
    rewiring_prob: float | None = None

    # Bridge ratio override (None = use cross_community_prob)
    bridge_ratio: float | None = None

    def __post_init__(self) -> None:
        if self.rewiring_prob is not None:
            self.ws_rewire_prob = self.rewiring_prob

    @property
    def effective_cross_community_prob(self) -> float:
        if self.bridge_ratio is not None:
            return self.bridge_ratio
        return self.cross_community_prob


@dataclass
class NetworkMetrics:
    """Metrics computed from a generated network.
    SPEC: docs/spec/02_NETWORK_SPEC.md#socialnetwork-output-object
    """
    clustering_coefficient: float
    avg_path_length: float
    degree_distribution: dict[int, int]
    community_sizes: dict[str, int]
    bridge_count: int
    is_valid: bool
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class SocialNetwork:
    """Output of network generation.
    SPEC: docs/spec/02_NETWORK_SPEC.md#socialnetwork-output-object
    """
    graph: nx.Graph
    communities: list[CommunityConfig]
    influencer_node_ids: list[int]
    bridge_edge_ids: list[tuple[int, int]]
    metrics: NetworkMetrics


@dataclass
class EvolutionConfig:
    """Configuration for dynamic network evolution.
    SPEC: docs/spec/02_NETWORK_SPEC.md#dynamic-network-evolution
    """
    enable_dynamic_edges: bool = True
    share_weight_boost: float = 0.02
    ignore_weight_decay: float = 0.01
    adopt_trust_boost: float = 0.05
    min_edge_weight: float = 0.01
    co_exposure_bond_threshold: float = 3
