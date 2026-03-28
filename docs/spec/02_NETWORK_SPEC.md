# 02 — Network Generator SPEC
Version: 0.1.1 | Status: DRAFT

---

## 1. Overview

The social network models the influence relationships between agents. A realistic network must replicate three properties of real-world SNS:

| Property | Model | Parameter |
|----------|-------|-----------|
| Community clustering | Watts-Strogatz small-world | High clustering coefficient |
| Power-law influencers | Barabási-Albert preferential attachment | Scale-free degree distribution |
| Short path length | Small-world rewiring | avg path ≈ 4–6 |

The generator produces a **Hybrid Network** by merging community-local graphs with an influencer layer, then adding cross-community bridges.

---

## 2. Default Community Configuration

```python
DEFAULT_COMMUNITIES = [
    CommunityConfig(id="A", name="early_adopters",   size=100, agent_type="early_adopter"),
    CommunityConfig(id="B", name="general_consumers", size=500, agent_type="consumer"),
    CommunityConfig(id="C", name="skeptics",          size=200, agent_type="skeptic"),
    CommunityConfig(id="D", name="experts",           size=30,  agent_type="expert"),
    CommunityConfig(id="E", name="influencers",       size=170, agent_type="influencer"),
]
# Total: 1000 agents
```

---

## 3. Interface Contracts

### NetworkGenerator

```python
class NetworkGenerator:
    def generate(
        self,
        communities: list[CommunityConfig],
        config: NetworkConfig,
    ) -> SocialNetwork:
        """
        Full network generation pipeline:
            1. generate_community_graphs()
            2. generate_influencer_layer()
            3. merge_networks()
            4. add_cross_community_edges()
            5. compute_edge_weights()
            6. validate_network_metrics()

        Raises:
            NetworkValidationError: if generated graph violates metric thresholds
        """

@dataclass
class NetworkConfig:
    # Watts-Strogatz parameters
    ws_k_neighbors: int = 6          # each node connects to K nearest neighbors
    ws_rewire_prob: float = 0.1      # rewiring probability

    # Barabási-Albert parameters
    ba_m_edges: int = 3              # edges added per new node

    # Cross-community edges
    cross_community_prob: float = 0.02  # P_cross

    # Edge weight
    trust_similarity_weight: float = 0.6
    interaction_freq_weight: float = 0.4

    # Validation thresholds
    min_clustering_coefficient: float = 0.2
    max_clustering_coefficient: float = 0.6
    min_avg_path_length: float = 3.0
    max_avg_path_length: float = 7.0
```

---

### Step 1: Community Graph Generation (Watts-Strogatz)

```python
class CommunityGraphBuilder:
    def build(
        self,
        community: CommunityConfig,
        config: NetworkConfig,
    ) -> nx.Graph:
        """
        G = nx.watts_strogatz_graph(
            n = community.size,
            k = config.ws_k_neighbors,
            p = config.ws_rewire_prob
        )
        Nodes relabeled to [start_index, start_index + size).

        Returns nx.Graph with node attributes:
            - community_id: str
            - agent_type: str
        """
```

### Step 2: Influencer Layer (Barabási-Albert)

```python
class InfluencerLayerBuilder:
    def build(
        self,
        total_agents: int,
        config: NetworkConfig,
    ) -> nx.Graph:
        """
        G = nx.barabasi_albert_graph(
            n = total_agents,
            m = config.ba_m_edges
        )
        Produces scale-free degree distribution (power-law).
        Top 1% degree nodes tagged as 'hub' for influencer identification.
        """
```

### Step 3: Merge Networks

```python
class NetworkMerger:
    def merge(
        self,
        community_graphs: list[nx.Graph],
        influencer_graph: nx.Graph,
    ) -> nx.Graph:
        """
        compose(community_graphs) + compose(influencer_graph)
        Edge deduplication: keep max weight on duplicate edges.
        Node attributes from community_graphs take priority.
        """
```

### Step 4: Cross-Community Edges

```python
class CrossCommunityBridge:
    def add_bridges(
        self,
        G: nx.Graph,
        communities: list[CommunityConfig],
        p_cross: float = 0.02,
        seed: int | None = None,
    ) -> nx.Graph:
        """
        For each pair of communities (A, B):
            sample random node_i from A, node_j from B
            with probability p_cross, add edge (i, j)

        Bridge edges get reduced initial trust weight (0.3 default).
        Represents realistic inter-community connections.
        """
```

### Step 5: Edge Weight Computation

```python
class EdgeWeightComputer:
    def compute(
        self,
        G: nx.Graph,
        agents: dict[int, AgentPersonality],
        config: NetworkConfig,
    ) -> nx.Graph:
        """
        For each edge (i, j):
            trust_ij = cosine_similarity(personality_i, personality_j)
                       + interaction_history_ij  (default 0 on init)
            interaction_freq_ij = (activity_i + activity_j) / 2

            W_ij = trust_weight * trust_ij + freq_weight * interaction_freq_ij

        Edge attribute 'weight' is set. Range: [0.0, 1.0].
        """
```

---

## 4. Dynamic Network Evolution

The network is not static. Each step may update edge weights:

```python
class NetworkEvolver:
    def evolve_step(
        self,
        G: nx.Graph,
        step_results: list[AgentTickResult],
        config: EvolutionConfig,
    ) -> nx.Graph:
        """
        Updates based on agent actions:
            SHARE   → edge weight += 0.02 (interaction reinforcement)
            IGNORE  → edge weight -= 0.01 (slow decay)
            ADOPT   → trust to recommending neighbor += 0.05

        New edges may form if two agents both share the same content (co-exposure bonding).
        Edges may be removed if weight drops below min_weight threshold.
        """

@dataclass
class EvolutionConfig:
    enable_dynamic_edges: bool = True
    share_weight_boost: float = 0.02
    ignore_weight_decay: float = 0.01
    adopt_trust_boost: float = 0.05
    min_edge_weight: float = 0.01    # edges below this are pruned
    co_exposure_bond_threshold: float = 3  # steps of co-exposure before edge forms
```

---

## 5. Influence Score

```python
class InfluenceScorer:
    def compute_influence_score(
        self,
        G: nx.Graph,
        agent_id: int,
        activity_level: float,
        credibility: float,
    ) -> float:
        """
        degree = G.degree(agent_id)
        followers = len([n for n in G.neighbors(agent_id) if n in influencer_set])

        I_i = normalize(followers * credibility * activity_level)

        Normalized to [0.0, 1.0] across all agents.
        """
```

---

## 6. SocialNetwork Output Object

```python
@dataclass
class SocialNetwork:
    graph: nx.Graph                          # NetworkX graph with weights
    communities: list[CommunityConfig]
    influencer_node_ids: list[int]           # top-degree nodes
    bridge_edge_ids: list[tuple[int, int]]   # cross-community edges
    metrics: NetworkMetrics

@dataclass
class NetworkMetrics:
    clustering_coefficient: float
    avg_path_length: float
    degree_distribution: dict[int, int]   # degree → count
    community_sizes: dict[str, int]
    bridge_count: int
    is_valid: bool
    validation_errors: list[str]
```

---

## 7. Error Specification

| Situation | Exception Type | Recovery | Logging |
|-----------|---------------|----------|---------|
| `total_agents < 2` | `ValueError` | Reject generation | ERROR |
| Community `size <= 0` in config | `ValueError` | Reject generation | ERROR |
| Community `size` sum ≠ `total_agents` | `ValueError` | Reject generation (no silent resize) | ERROR |
| Watts-Strogatz `k >= n` (neighbors ≥ nodes) | `NetworkValidationError` | Reduce `k` to `n-1`, retry with different seed (max 3 retries) | WARN |
| Barabási-Albert `m > existing_nodes` | `NetworkValidationError` | Clamp `m` to `existing_nodes`, retry | WARN |
| Graph not connected after merge | — (auto-repair) | Add minimum bridge edges until weakly connected | WARN |
| Invalid `rewiring_prob` (not in [0, 1]) | `ValueError` | Reject generation | ERROR |
| Seed collision (same seed reused) | — (allowed) | Deterministic duplicate — no error | — |
| Edge weight update on non-existent edge | `KeyError` | Skip update, edge treated as 0.0 weight | DEBUG |
| Network evolution with empty action list | — (no-op) | Return unchanged network | — |

---

## 8. Acceptance Criteria (Harness Tests)

| ID | Test | Expected |
|----|------|----------|
| NET-01 | Generate 1000-agent default network | `metrics.is_valid == True` |
| NET-02 | Degree distribution follows power law | Top 1% nodes have degree > 10× median |
| NET-03 | Clustering coefficient in valid range | `0.2 ≤ clustering_coefficient ≤ 0.6` |
| NET-04 | Average path length in valid range | `3.0 ≤ avg_path_length ≤ 7.0` |
| NET-05 | Cross-community edges exist | `bridge_count > 0` |
| NET-06 | All agent nodes present | `len(G.nodes) == total_agents` |
| NET-07 | Edge weights all in [0, 1] | No edge weight outside range |
| NET-08 | Dynamic evolution changes edge weights | Weights change after step with SHARE action |
| NET-09 | Network generation completes within 5s | Benchmark for 1000 agents |
| NET-10 | Reproducible with seed | Same seed → identical network |
