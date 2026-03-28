"""
Auto-generated from SPEC: docs/spec/02_NETWORK_SPEC.md#acceptance-criteria
SPEC Version: 0.1.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest
import time


@pytest.mark.phase3
@pytest.mark.acceptance
class TestNetworkAcceptance:
    """SPEC: 02_NETWORK_SPEC.md — Acceptance Criteria NET-01 to NET-10"""

    def _default_config(self):
        """Helper: build default 1000-agent network config from SPEC section 2."""
        from app.engine.network.schema import NetworkConfig, CommunityConfig
        return NetworkConfig(communities=[
            CommunityConfig(id="A", name="early_adopters", size=100, agent_type="early_adopter"),
            CommunityConfig(id="B", name="general_consumers", size=500, agent_type="consumer"),
            CommunityConfig(id="C", name="skeptics", size=200, agent_type="skeptic"),
            CommunityConfig(id="D", name="experts", size=30, agent_type="expert"),
            CommunityConfig(id="E", name="influencers", size=170, agent_type="influencer"),
        ])

    def test_net01_default_network_valid(self):
        """NET-01: Generate 1000-agent default network -> metrics.is_valid == True."""
        from app.engine.network.generator import NetworkGenerator
        gen = NetworkGenerator()
        config = self._default_config()
        result = gen.generate(config, seed=42)
        assert result.metrics.is_valid is True

    def test_net02_degree_distribution_power_law(self):
        """NET-02: Top 1% nodes have degree > 10x median degree."""
        from app.engine.network.generator import NetworkGenerator
        import statistics
        gen = NetworkGenerator()
        config = self._default_config()
        result = gen.generate(config, seed=42)
        degrees = sorted([d for _, d in result.graph.degree()], reverse=True)
        top_1pct_cutoff = max(1, len(degrees) // 100)
        top_1pct_min_degree = degrees[top_1pct_cutoff - 1]
        median_degree = statistics.median(degrees)
        assert top_1pct_min_degree > 10 * median_degree

    def test_net03_clustering_coefficient_range(self):
        """NET-03: 0.2 <= clustering_coefficient <= 0.6."""
        from app.engine.network.generator import NetworkGenerator
        gen = NetworkGenerator()
        config = self._default_config()
        result = gen.generate(config, seed=42)
        cc = result.metrics.clustering_coefficient
        assert 0.2 <= cc <= 0.6, f"clustering_coefficient={cc} out of [0.2, 0.6]"

    def test_net04_avg_path_length_range(self):
        """NET-04: 3.0 <= avg_path_length <= 7.0."""
        from app.engine.network.generator import NetworkGenerator
        gen = NetworkGenerator()
        config = self._default_config()
        result = gen.generate(config, seed=42)
        apl = result.metrics.avg_path_length
        assert 3.0 <= apl <= 7.0, f"avg_path_length={apl} out of [3.0, 7.0]"

    def test_net05_cross_community_edges_exist(self):
        """NET-05: bridge_count > 0."""
        from app.engine.network.generator import NetworkGenerator
        gen = NetworkGenerator()
        config = self._default_config()
        result = gen.generate(config, seed=42)
        assert result.metrics.bridge_count > 0

    def test_net06_all_agent_nodes_present(self):
        """NET-06: len(G.nodes) == total_agents (1000)."""
        from app.engine.network.generator import NetworkGenerator
        gen = NetworkGenerator()
        config = self._default_config()
        result = gen.generate(config, seed=42)
        total_agents = sum(c.size for c in config.communities)
        assert len(result.graph.nodes) == total_agents

    def test_net07_edge_weights_in_range(self):
        """NET-07: All edge weights in [0.0, 1.0]."""
        from app.engine.network.generator import NetworkGenerator
        gen = NetworkGenerator()
        config = self._default_config()
        result = gen.generate(config, seed=42)
        for u, v, data in result.graph.edges(data=True):
            weight = data.get("weight", 0.0)
            assert 0.0 <= weight <= 1.0, f"Edge ({u},{v}) weight={weight} out of [0,1]"

    def test_net08_dynamic_evolution_changes_weights(self):
        """NET-08: Weights change after step with SHARE action."""
        from app.engine.network.generator import NetworkGenerator
        from app.engine.network.evolution import NetworkEvolver
        from app.engine.network.schema import NetworkConfig, CommunityConfig
        from app.engine.agent.schema import AgentAction
        gen = NetworkGenerator()
        config = NetworkConfig(communities=[
            CommunityConfig(id="A", name="a", size=50, agent_type="consumer"),
            CommunityConfig(id="B", name="b", size=50, agent_type="consumer"),
        ])
        network = gen.generate(config, seed=42)
        # Get initial weights
        initial_weights = {(u, v): d["weight"] for u, v, d in network.graph.edges(data=True)
                           if "weight" in d}
        # Create a SHARE action for a node that has edges
        node = list(network.graph.nodes)[0]
        neighbors = list(network.graph.neighbors(node))
        assert len(neighbors) > 0, "Need at least one neighbor for test"
        # Simulate a SHARE action from node
        from dataclasses import dataclass
        from uuid import uuid4

        @dataclass
        class FakeTickResult:
            agent_id: int
            action: AgentAction
            content_id: object
            step: int

        actions = [FakeTickResult(agent_id=node, action=AgentAction.SHARE,
                                  content_id=uuid4(), step=1)]
        evolver = NetworkEvolver()
        updated = evolver.evolve(network, actions=actions, step=1)
        # At least some edge weights should have changed
        changed = False
        for u, v, d in updated.graph.edges(data=True):
            if "weight" in d and (u, v) in initial_weights:
                if abs(d["weight"] - initial_weights[(u, v)]) > 1e-9:
                    changed = True
                    break
        assert changed, "No edge weights changed after SHARE action"

    def test_net09_generation_completes_within_5s(self):
        """NET-09: Network generation completes within 5s for 1000 agents."""
        from app.engine.network.generator import NetworkGenerator
        gen = NetworkGenerator()
        config = self._default_config()
        start = time.monotonic()
        result = gen.generate(config, seed=42)
        elapsed = time.monotonic() - start
        assert elapsed <= 5.0, f"Generation took {elapsed:.2f}s, exceeds 5s limit"
        assert result is not None

    def test_net10_reproducible_with_seed(self):
        """NET-10: Same seed -> identical network."""
        from app.engine.network.generator import NetworkGenerator
        gen = NetworkGenerator()
        config = self._default_config()
        n1 = gen.generate(config, seed=123)
        n2 = gen.generate(config, seed=123)
        assert list(n1.graph.nodes()) == list(n2.graph.nodes())
        assert list(n1.graph.edges()) == list(n2.graph.edges())
        assert n1.metrics.clustering_coefficient == n2.metrics.clustering_coefficient
        assert n1.metrics.avg_path_length == n2.metrics.avg_path_length
