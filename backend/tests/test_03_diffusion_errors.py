"""
Auto-generated from SPEC: docs/spec/03_DIFFUSION_SPEC.md#error-specification
SPEC Version: 0.1.1
Updated to match Phase 4 implementation.
"""
import pytest
from uuid import uuid4

import networkx as nx

from app.engine.agent.schema import (
    AgentState, AgentPersonality, AgentEmotion, AgentType, AgentAction,
)
from app.engine.network.schema import CommunityConfig, NetworkMetrics, SocialNetwork
from app.engine.diffusion.schema import RecSysConfig, CascadeConfig
from app.engine.diffusion.exposure_model import ExposureModel
from app.engine.diffusion.cascade_detector import CascadeDetector, StepResult
from app.engine.diffusion.propagation_model import PropagationModel
from app.engine.diffusion.sentiment_model import SentimentModel


def _agent() -> AgentState:
    return AgentState(
        agent_id=uuid4(), simulation_id=uuid4(), agent_type=AgentType.CONSUMER,
        step=1, personality=AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5),
        emotion=AgentEmotion(0.5, 0.5, 0.5, 0.3), belief=0.0,
        action=AgentAction.IGNORE, exposure_count=0, adopted=False,
        community_id=uuid4(), influence_score=0.3, llm_tier_used=None,
    )


def _empty_graph() -> SocialNetwork:
    g = nx.Graph()
    m = NetworkMetrics(
        clustering_coefficient=0.0, avg_path_length=0.0,
        degree_distribution={}, community_sizes={}, bridge_count=0, is_valid=True,
    )
    return SocialNetwork(
        graph=g, communities=[], influencer_node_ids=[], bridge_edge_ids=[], metrics=m,
    )


class TestDiffusionConfigValidation:
    """SPEC: 03_DIFFUSION_SPEC.md#error-specification — config validation"""

    def test_recsys_weight_sum_not_one_raises(self):
        """RecSys weight sum != 1.0 (+-0.01) raises ValueError."""
        with pytest.raises(ValueError, match="weight sum"):
            RecSysConfig(w_recency=0.5, w_social_affinity=0.5)
            # sum = 0.5+0.5+0.2+0.2+0.1 = 1.5

    def test_recsys_weight_sum_exact_one_ok(self):
        """RecSys weight sum == 1.0 passes validation."""
        config = RecSysConfig()  # default weights sum to 1.0
        model = ExposureModel(config)
        assert model is not None

    def test_empty_agent_list_raises(self):
        """ExposureModel with empty agent list raises ValueError."""
        model = ExposureModel()
        with pytest.raises(ValueError, match="agents list must not be empty"):
            model.compute_exposure(agents=[], graph=_empty_graph(), active_events=[], step=1)

    def test_cascade_threshold_zero_raises(self):
        """Cascade threshold <= 0 raises ValueError."""
        with pytest.raises(ValueError):
            CascadeConfig(viral_cascade_threshold=0)

    def test_cascade_threshold_negative_raises(self):
        """Cascade threshold < 0 raises ValueError."""
        with pytest.raises(ValueError):
            CascadeConfig(viral_cascade_threshold=-5)


class TestDiffusionPropagationClamping:
    """SPEC: 03_DIFFUSION_SPEC.md#error-specification — probability clamping"""

    def test_negative_diffusion_rate_clamped(self):
        """Negative R(t) is clamped to 0.0."""
        model = PropagationModel()
        rate = model.compute_diffusion_rate([15, 10])
        assert rate == 0.0

    def test_probability_always_in_range(self):
        """All propagation event probabilities are in [0, 1]."""
        source = AgentState(
            agent_id=uuid4(), simulation_id=uuid4(), agent_type=AgentType.INFLUENCER,
            step=1, personality=AgentPersonality(0.9, 0.1, 0.9, 0.9, 0.9),
            emotion=AgentEmotion(0.9, 0.9, 0.0, 0.9), belief=0.8,
            action=AgentAction.SHARE, exposure_count=1, adopted=False,
            community_id=uuid4(), influence_score=1.0, llm_tier_used=None,
        )
        g = nx.Graph()
        g.add_node(0, agent_id=source.agent_id)
        for i in range(1, 6):
            aid = uuid4()
            g.add_node(i, agent_id=aid)
            g.add_edge(0, i, weight=1.0)
        m = NetworkMetrics(
            clustering_coefficient=0.3, avg_path_length=4.0,
            degree_distribution={}, community_sizes={}, bridge_count=0, is_valid=True,
        )
        graph = SocialNetwork(
            graph=g, communities=[], influencer_node_ids=[0], bridge_edge_ids=[], metrics=m,
        )
        model = PropagationModel()
        events = model.propagate(source, AgentAction.SHARE, graph, uuid4(), step=1, seed=0)
        for e in events:
            assert 0.0 <= e.probability <= 1.0


class TestDiffusionGracefulDegradation:
    """SPEC: 03_DIFFUSION_SPEC.md#error-specification — graceful degradation"""

    def test_no_active_campaign_returns_zero_exposure(self):
        """No active campaign -> all exposure scores = 0.0."""
        model = ExposureModel()
        agents = [_agent()]
        g = nx.Graph()
        g.add_node(0, agent_id=agents[0].agent_id)
        m = NetworkMetrics(
            clustering_coefficient=0.0, avg_path_length=0.0,
            degree_distribution={}, community_sizes={}, bridge_count=0, is_valid=True,
        )
        graph = SocialNetwork(
            graph=g, communities=[], influencer_node_ids=[], bridge_edge_ids=[], metrics=m,
        )
        result = model.compute_exposure(agents=agents, graph=graph, active_events=[], step=1)
        assert all(r.exposure_score == 0.0 for r in result.values())

    def test_cascade_detector_insufficient_steps_returns_empty(self):
        """CascadeDetector with fewer steps than window returns empty for slow adoption."""
        detector = CascadeDetector()
        current = StepResult(
            step=1, total_agents=100, adopted_count=5, adoption_rate=0.05,
            community_sentiments={}, community_variances={},
            community_adoption_rates={}, internal_links={}, external_links={},
            adopted_agent_ids=[],
        )
        events = detector.detect(current, [])
        slow = [e for e in events if e.event_type == "slow_adoption"]
        assert slow == []

    def test_empty_community_sentiment_returns_zero(self):
        """Empty community sentiment = 0.0 (no division by zero)."""
        model = SentimentModel()
        result = model.update_community_sentiment(uuid4(), [], [])
        assert result.mean_belief == 0.0
        assert result.sentiment_variance == 0.0
