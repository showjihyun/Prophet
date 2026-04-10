"""Tests for Simulation Quality Phase 3: Reflection, Homophily, Memory Persistence.

Auto-generated from SPEC: docs/spec/21_SIMULATION_QUALITY_P3_SPEC.md
SPEC Version: 0.1.0
Generated BEFORE implementation — tests define the contract.
"""
import pytest
from uuid import uuid4

from app.engine.agent.memory import MemoryRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _memory(
    content: str = "test memory",
    emotion_weight: float = 0.6,
    social_importance: float = 0.3,
    step: int = 0,
) -> MemoryRecord:
    return MemoryRecord(
        memory_id=uuid4(),
        agent_id=uuid4(),
        memory_type="episodic",
        content=content,
        timestamp=step,
        emotion_weight=emotion_weight,
        social_importance=social_importance,
        embedding=None,
        relevance_score=None,
    )


# ===========================================================================
# §1 — RF: Agent Reflection
# ===========================================================================

class TestReflectionEngine:
    """SPEC: docs/spec/21_SIMULATION_QUALITY_P3_SPEC.md#§1"""

    @pytest.fixture
    def engine(self):
        from app.engine.agent.reflection import ReflectionEngine
        return ReflectionEngine()

    def test_rf_ac_01_should_reflect_memory_threshold(self, engine):
        """RF-AC-01: should_reflect True when memory_count >= threshold."""
        assert engine.should_reflect(
            memory_count_since_last=5,
            step=3,
            last_reflection_step=1,
        ) is True

    def test_rf_ac_02_should_reflect_step_interval(self, engine):
        """RF-AC-02: should_reflect True when step interval elapsed."""
        assert engine.should_reflect(
            memory_count_since_last=1,  # below memory threshold
            step=15,
            last_reflection_step=0,  # 15 steps elapsed > default 10
        ) is True

    def test_rf_ac_03_should_reflect_false_neither_condition(self, engine):
        """RF-AC-03: should_reflect False when neither condition met."""
        assert engine.should_reflect(
            memory_count_since_last=2,  # below 5
            step=5,
            last_reflection_step=3,  # only 2 steps elapsed
        ) is False

    def test_rf_ac_04_belief_delta_in_range(self, engine):
        """RF-AC-04: apply_reflection_heuristic returns belief_delta in [-0.3, 0.3]."""
        from app.engine.agent.reflection import ReflectionInput
        inp = ReflectionInput(
            agent_id=uuid4(),
            recent_memories=[_memory(emotion_weight=0.8) for _ in range(5)],
            current_belief=0.5,
            step=10,
        )
        result = engine.apply_reflection_heuristic(inp)
        assert -0.3 <= result.belief_delta <= 0.3

    def test_rf_ac_05_positive_memories_positive_delta(self, engine):
        """RF-AC-05: All positive memories → positive belief_delta."""
        from app.engine.agent.reflection import ReflectionInput
        pos_memories = [_memory(emotion_weight=0.9) for _ in range(5)]
        inp = ReflectionInput(
            agent_id=uuid4(),
            recent_memories=pos_memories,
            current_belief=0.0,
            step=10,
        )
        result = engine.apply_reflection_heuristic(inp)
        assert result.belief_delta > 0.0

    def test_rf_ac_06_negative_memories_negative_delta(self, engine):
        """RF-AC-06: All negative memories → negative belief_delta."""
        from app.engine.agent.reflection import ReflectionInput
        neg_memories = [_memory(emotion_weight=0.1) for _ in range(5)]
        inp = ReflectionInput(
            agent_id=uuid4(),
            recent_memories=neg_memories,
            current_belief=0.0,
            step=10,
        )
        result = engine.apply_reflection_heuristic(inp)
        assert result.belief_delta < 0.0

    def test_rf_ac_07_empty_memories_zero_delta(self, engine):
        """RF-AC-07: Empty memories → belief_delta == 0.0."""
        from app.engine.agent.reflection import ReflectionInput
        inp = ReflectionInput(
            agent_id=uuid4(),
            recent_memories=[],
            current_belief=0.5,
            step=10,
        )
        result = engine.apply_reflection_heuristic(inp)
        assert result.belief_delta == pytest.approx(0.0, abs=1e-9)

    def test_rf_ac_08_build_reflection_input_contains_fields(self, engine):
        """RF-AC-08: build_reflection_input includes current_belief and memories."""
        from app.engine.agent.reflection import ReflectionInput
        memories = [_memory() for _ in range(3)]
        inp = engine.build_reflection_input(
            recent_memories=memories,
            current_belief=0.3,
        )
        assert isinstance(inp, ReflectionInput)
        assert inp.current_belief == 0.3
        assert len(inp.recent_memories) == 3

    def test_rf_custom_thresholds(self):
        """Custom MEMORY_THRESHOLD and STEP_INTERVAL are respected."""
        from app.engine.agent.reflection import ReflectionEngine
        eng = ReflectionEngine(memory_threshold=2, step_interval=3)
        assert eng.should_reflect(memory_count_since_last=2, step=1, last_reflection_step=0) is True

    def test_rf_result_has_insight_string(self, engine):
        """ReflectionResult.insight is a non-empty string."""
        from app.engine.agent.reflection import ReflectionInput
        inp = ReflectionInput(
            agent_id=uuid4(),
            recent_memories=[_memory(emotion_weight=0.7) for _ in range(3)],
            current_belief=0.2,
            step=10,
        )
        result = engine.apply_reflection_heuristic(inp)
        assert isinstance(result.insight, str)
        assert len(result.insight) > 0


# ===========================================================================
# §2 — HM: Homophily Edge Weighting
# ===========================================================================

class TestHomophilyEdgeWeighting:
    """SPEC: docs/spec/21_SIMULATION_QUALITY_P3_SPEC.md#§2"""

    def _build_small_network_with_personalities(self, homophily_weight: float = 0.0):
        """Build a 10-node network with personality attributes on nodes."""
        import networkx as nx
        from app.engine.network.schema import NetworkConfig, CommunityConfig
        from app.engine.network.generator import NetworkGenerator

        config = NetworkConfig(
            communities=[CommunityConfig(id="A", name="A", size=10, agent_type="consumer")],
            ws_k_neighbors=4,
            ws_rewire_prob=0.1,
            homophily_weight=homophily_weight,
            min_clustering_coefficient=0.0,
            max_clustering_coefficient=1.0,
            min_avg_path_length=1.0,
            max_avg_path_length=20.0,
        )
        gen = NetworkGenerator()
        network = gen.generate(config, seed=42)

        # Set personality attributes on nodes
        for node in network.graph.nodes():
            # Similar personalities for nodes 0-4, different for 5-9
            if node < 5:
                network.graph.nodes[node]["personality"] = {
                    "openness": 0.8, "skepticism": 0.2,
                    "trend_following": 0.7, "brand_loyalty": 0.6,
                    "social_influence": 0.5,
                }
            else:
                network.graph.nodes[node]["personality"] = {
                    "openness": 0.1, "skepticism": 0.9,
                    "trend_following": 0.2, "brand_loyalty": 0.1,
                    "social_influence": 0.3,
                }

        return network, config, gen

    def test_hm_ac_01_zero_weight_matches_original(self):
        """HM-AC-01: homophily_weight=0 → same behavior as original."""
        network, config, gen = self._build_small_network_with_personalities(homophily_weight=0.0)
        # Re-compute edge weights
        gen._compute_edge_weights(network.graph, config)

        # With homophily_weight=0, same-community edges should be 0.7*0.6 + 0.5*0.4 = 0.62
        for u, v, data in network.graph.edges(data=True):
            if data.get("is_bridge", False):
                continue
            w = data["weight"]
            expected = 0.6 * 0.7 + 0.4 * 0.5  # trust_weight * trust + freq_weight * freq
            assert w == pytest.approx(expected, abs=0.01)

    def test_hm_ac_02_similar_personalities_higher_weight(self):
        """HM-AC-02: Similar personalities → higher edge weight."""
        network, config, gen = self._build_small_network_with_personalities(homophily_weight=0.3)
        gen._compute_edge_weights(network.graph, config)

        # Find an edge between similar nodes (0-4) and dissimilar nodes (0 and 5+)
        similar_weights = []
        dissimilar_weights = []
        for u, v, data in network.graph.edges(data=True):
            if data.get("is_bridge", False):
                continue
            u_pers = network.graph.nodes[u].get("personality")
            v_pers = network.graph.nodes[v].get("personality")
            if u_pers and v_pers:
                if u < 5 and v < 5:
                    similar_weights.append(data["weight"])
                elif (u < 5 and v >= 5) or (u >= 5 and v < 5):
                    dissimilar_weights.append(data["weight"])

        if similar_weights and dissimilar_weights:
            assert max(similar_weights) > min(dissimilar_weights)

    def test_hm_ac_03_missing_personality_graceful_fallback(self):
        """HM-AC-03: Missing personality → fallback to community-only weight."""
        network, config, gen = self._build_small_network_with_personalities(homophily_weight=0.3)
        # Remove personality from some nodes
        for node in [0, 1, 2]:
            if "personality" in network.graph.nodes[node]:
                del network.graph.nodes[node]["personality"]

        gen._compute_edge_weights(network.graph, config)

        # Should not crash; edges involving nodes 0-2 should still have valid weights
        for u, v, data in network.graph.edges(data=True):
            if data.get("is_bridge", False):
                continue
            assert 0.0 <= data["weight"] <= 1.0

    def test_hm_ac_04_personality_sim_unit_interval(self):
        """HM-AC-04: personality_sim in [0.0, 1.0] for valid personality vectors."""
        from app.engine.network.generator import _personality_similarity
        p1 = {"openness": 0.8, "skepticism": 0.2, "trend_following": 0.7,
               "brand_loyalty": 0.6, "social_influence": 0.5}
        p2 = {"openness": 0.1, "skepticism": 0.9, "trend_following": 0.2,
               "brand_loyalty": 0.1, "social_influence": 0.3}

        sim = _personality_similarity(p1, p2)
        assert 0.0 <= sim <= 1.0

        # Same personality → sim = 1.0
        sim_same = _personality_similarity(p1, p1)
        assert sim_same == pytest.approx(1.0, abs=1e-6)

    def test_hm_network_config_has_homophily_weight(self):
        """NetworkConfig accepts homophily_weight parameter."""
        from app.engine.network.schema import NetworkConfig, CommunityConfig
        config = NetworkConfig(
            communities=[CommunityConfig(id="X", name="X", size=5, agent_type="consumer")],
            homophily_weight=0.2,
        )
        assert config.homophily_weight == 0.2
