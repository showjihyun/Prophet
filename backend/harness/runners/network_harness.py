"""F18 Unit Test Hooks — Network Harness.
SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks
"""
import math

from app.engine.network.generator import NetworkGenerator
from app.engine.network.schema import CommunityConfig, NetworkConfig, SocialNetwork


class NetworkHarness:
    """Per-layer test entry points for Network generator.

    SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks
    """

    def generate_minimal(self, n_agents: int = 10) -> SocialNetwork:
        """Fast small network for unit tests.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks

        Generates a single community with n_agents agents using
        NetworkGenerator with minimal parameters.
        """
        community_size = max(n_agents, 2)
        config = NetworkConfig(
            communities=[
                CommunityConfig(
                    id="test_community",
                    name="Test Community",
                    size=community_size,
                    agent_type="consumer",
                    personality_profile={
                        "openness": 0.5,
                        "skepticism": 0.3,
                        "trend_following": 0.4,
                        "brand_loyalty": 0.5,
                        "social_influence": 0.4,
                    },
                )
            ],
            ws_k_neighbors=min(4, community_size - 1),
            ws_rewire_prob=0.1,
            ba_m_edges=min(2, community_size - 1),
            cross_community_prob=0.0,
        )
        generator = NetworkGenerator()
        return generator.generate(config, seed=42)

    def assert_scale_free(self, network: SocialNetwork) -> None:
        """Assert degree distribution follows a power law (scale-free property).

        SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks

        A scale-free network has a few very high-degree nodes (hubs) and many
        low-degree nodes. We validate:
          1. Maximum degree > mean degree (hub existence).
          2. Degree variance > 0 (heterogeneous connectivity).

        Raises:
            AssertionError: if the network does not exhibit scale-free properties.
        """
        G = network.graph
        if G.number_of_nodes() < 2:
            raise AssertionError("Network too small to assert scale-free property (< 2 nodes)")

        degrees = [d for _, d in G.degree()]
        mean_deg = sum(degrees) / len(degrees)
        max_deg = max(degrees)
        variance = sum((d - mean_deg) ** 2 for d in degrees) / len(degrees)

        assert max_deg > mean_deg, (
            f"Scale-free networks require max_degree ({max_deg}) > mean_degree ({mean_deg:.2f})"
        )
        assert variance > 0.0, (
            f"Scale-free networks require degree variance > 0, got {variance:.4f}"
        )


__all__ = ["NetworkHarness"]
