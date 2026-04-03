"""
Auto-generated from SPEC: docs/spec/02_NETWORK_SPEC.md#error-specification
SPEC Version: 0.1.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest


@pytest.mark.phase3
class TestNetworkGenerationValidation:
    """SPEC: 02_NETWORK_SPEC.md#error-specification — input validation"""

    def test_total_agents_less_than_2_raises(self):
        """total_agents < 2 raises ValueError."""
        from app.engine.network.generator import NetworkGenerator
        from app.engine.network.schema import NetworkConfig, CommunityConfig
        gen = NetworkGenerator()
        config = NetworkConfig(communities=[
            CommunityConfig(id="A", name="solo", size=1, agent_type="consumer"),
        ])
        with pytest.raises(ValueError):
            gen.generate(config, seed=42)

    def test_community_size_zero_raises(self):
        """Community size <= 0 raises ValueError."""
        from app.engine.network.generator import NetworkGenerator
        from app.engine.network.schema import NetworkConfig, CommunityConfig
        gen = NetworkGenerator()
        config = NetworkConfig(communities=[
            CommunityConfig(id="A", name="empty", size=0, agent_type="consumer"),
            CommunityConfig(id="B", name="normal", size=100, agent_type="consumer"),
        ])
        with pytest.raises(ValueError):
            gen.generate(config, seed=42)

    def test_community_size_negative_raises(self):
        """Community size < 0 raises ValueError."""
        from app.engine.network.generator import NetworkGenerator
        from app.engine.network.schema import NetworkConfig, CommunityConfig
        gen = NetworkGenerator()
        config = NetworkConfig(communities=[
            CommunityConfig(id="A", name="neg", size=-5, agent_type="consumer"),
            CommunityConfig(id="B", name="normal", size=100, agent_type="consumer"),
        ])
        with pytest.raises(ValueError):
            gen.generate(config, seed=42)

    def test_invalid_rewiring_prob_raises(self):
        """rewiring_prob not in [0, 1] raises ValueError."""
        from app.engine.network.generator import NetworkGenerator
        from app.engine.network.schema import NetworkConfig, CommunityConfig
        gen = NetworkGenerator()
        config = NetworkConfig(
            communities=[
                CommunityConfig(id="A", name="a", size=50, agent_type="consumer"),
                CommunityConfig(id="B", name="b", size=50, agent_type="consumer"),
            ],
            rewiring_prob=1.5,
        )
        with pytest.raises(ValueError):
            gen.generate(config, seed=42)


@pytest.mark.phase3
class TestNetworkGenerationRecovery:
    """SPEC: 02_NETWORK_SPEC.md#error-specification — auto-recovery"""

    def test_watts_strogatz_k_too_large_recovers(self):
        """WS k >= n auto-reduces k and retries (NetworkValidationError logged as WARN)."""
        from app.engine.network.generator import NetworkGenerator
        from app.engine.network.schema import NetworkConfig, CommunityConfig
        gen = NetworkGenerator()
        # Very small community where default k might exceed n
        config = NetworkConfig(communities=[
            CommunityConfig(id="A", name="tiny", size=3, agent_type="consumer"),
            CommunityConfig(id="B", name="normal", size=97, agent_type="consumer"),
        ])
        # Should NOT raise — auto-recovery reduces k
        result = gen.generate(config, seed=42)
        assert result is not None
        assert result.metrics.is_valid

    def test_disconnected_graph_auto_repairs(self):
        """Graph not connected after merge → auto-add bridge edges."""
        from app.engine.network.generator import NetworkGenerator
        from app.engine.network.schema import NetworkConfig, CommunityConfig
        gen = NetworkGenerator()
        # Many isolated small communities — likely disconnected without bridges
        config = NetworkConfig(
            communities=[
                CommunityConfig(id=chr(65 + i), name=f"c{i}", size=10,
                                agent_type="consumer")
                for i in range(10)
            ],
            bridge_ratio=0.0,  # explicitly no bridges
        )
        result = gen.generate(config, seed=42)
        # Auto-repair should ensure weak connectivity
        assert result.metrics.is_valid

    def test_edge_weight_update_missing_edge_skips(self):
        """Edge weight update on non-existent edge is silently skipped."""
        from app.engine.network.evolution import NetworkEvolver
        from uuid import uuid4
        evolver = NetworkEvolver()
        fake_edge = (uuid4(), uuid4())
        # Should not raise — just skip
        evolver.update_edge_weight(graph={}, edge=fake_edge, delta=0.1)

    def test_evolution_empty_actions_noop(self):
        """Network evolution with empty action list returns unchanged network."""
        from app.engine.network.generator import NetworkGenerator
        from app.engine.network.evolution import NetworkEvolver
        from app.engine.network.schema import NetworkConfig, CommunityConfig
        gen = NetworkGenerator()
        config = NetworkConfig(communities=[
            CommunityConfig(id="A", name="a", size=50, agent_type="consumer"),
            CommunityConfig(id="B", name="b", size=50, agent_type="consumer"),
        ])
        network = gen.generate(config, seed=42)
        evolver = NetworkEvolver()
        updated = evolver.evolve_step(network, actions=[], step=1)
        assert updated.graph.number_of_edges() == network.graph.number_of_edges()

    def test_seed_reuse_deterministic(self):
        """Same seed produces identical network (not an error)."""
        from app.engine.network.generator import NetworkGenerator
        from app.engine.network.schema import NetworkConfig, CommunityConfig
        gen = NetworkGenerator()
        config = NetworkConfig(communities=[
            CommunityConfig(id="A", name="a", size=50, agent_type="consumer"),
            CommunityConfig(id="B", name="b", size=50, agent_type="consumer"),
        ])
        n1 = gen.generate(config, seed=42)
        n2 = gen.generate(config, seed=42)
        assert list(n1.graph.edges()) == list(n2.graph.edges())
