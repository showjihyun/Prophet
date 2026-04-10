"""Tests for SentimentModel.
Auto-generated from SPEC: docs/spec/03_DIFFUSION_SPEC.md
SPEC Version: 0.1.1
"""
import pytest
from uuid import uuid4

from app.engine.agent.schema import (
    AgentAction,
    AgentEmotion,
    AgentPersonality,
    AgentState,
    AgentType,
)
from app.engine.diffusion.schema import CommunitySentiment, ExpertOpinion
from app.engine.diffusion.sentiment_model import SentimentModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent(community_id, belief=0.0, adopted=False, step=1) -> AgentState:
    return AgentState(
        agent_id=uuid4(),
        simulation_id=uuid4(),
        agent_type=AgentType.CONSUMER,
        step=step,
        personality=AgentPersonality(
            openness=0.5, skepticism=0.3, trend_following=0.4,
            brand_loyalty=0.5, social_influence=0.5,
        ),
        emotion=AgentEmotion(interest=0.5, trust=0.5, skepticism=0.3, excitement=0.5),
        belief=belief,
        action=AgentAction.IGNORE,
        exposure_count=0,
        adopted=adopted,
        community_id=community_id,
        influence_score=0.5,
        llm_tier_used=None,
    )


def _make_expert_opinion(score, community_id, confidence=0.8) -> ExpertOpinion:
    return ExpertOpinion(
        expert_agent_id=uuid4(),
        score=score,
        reasoning="Test opinion",
        step=1,
        affects_communities=[community_id],
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.phase4
@pytest.mark.unit
class TestSentimentModelUpdateCommunity:
    """SPEC: 03_DIFFUSION_SPEC.md#sentimentmodel"""

    def test_empty_community_returns_zero(self):
        """Empty community -> 0.0 sentiment."""
        model = SentimentModel()
        cid = uuid4()
        result = model.update_community_sentiment(cid, [], [])

        assert result.community_id == cid
        assert result.mean_belief == 0.0
        assert result.sentiment_variance == 0.0
        assert result.adoption_rate == 0.0

    def test_single_agent(self):
        model = SentimentModel()
        cid = uuid4()
        agents = [_make_agent(cid, belief=0.5)]

        result = model.update_community_sentiment(cid, agents, [])

        assert result.mean_belief == pytest.approx(0.5, abs=0.01)
        assert result.sentiment_variance == pytest.approx(0.0, abs=0.01)

    def test_mean_belief_calculation(self):
        model = SentimentModel()
        cid = uuid4()
        agents = [
            _make_agent(cid, belief=0.2),
            _make_agent(cid, belief=0.8),
            _make_agent(cid, belief=-0.4),
        ]

        result = model.update_community_sentiment(cid, agents, [])

        expected_mean = (0.2 + 0.8 + (-0.4)) / 3
        assert result.mean_belief == pytest.approx(expected_mean, abs=0.01)

    def test_variance_calculation(self):
        model = SentimentModel()
        cid = uuid4()
        agents = [
            _make_agent(cid, belief=-0.5),
            _make_agent(cid, belief=0.5),
        ]

        result = model.update_community_sentiment(cid, agents, [])

        # mean = 0.0, var = (0.25 + 0.25)/(2-1) = 0.50 (Bessel's correction)
        assert result.sentiment_variance == pytest.approx(0.50, abs=0.01)

    def test_adoption_rate(self):
        model = SentimentModel()
        cid = uuid4()
        agents = [
            _make_agent(cid, adopted=True),
            _make_agent(cid, adopted=True),
            _make_agent(cid, adopted=False),
        ]

        result = model.update_community_sentiment(cid, agents, [])
        assert result.adoption_rate == pytest.approx(2 / 3, abs=0.01)

    def test_expert_negative_opinion_reduces_belief(self):
        """DIF-06: Expert negative opinion reduces community trust."""
        model = SentimentModel()
        cid = uuid4()
        agents = [
            _make_agent(cid, belief=0.5),
            _make_agent(cid, belief=0.5),
        ]

        # Without expert
        baseline = model.update_community_sentiment(cid, agents, [])

        # With negative expert
        opinion = _make_expert_opinion(score=-0.8, community_id=cid, confidence=0.9)
        result = model.update_community_sentiment(cid, agents, [opinion])

        assert result.mean_belief < baseline.mean_belief

    def test_expert_positive_opinion_increases_belief(self):
        model = SentimentModel()
        cid = uuid4()
        agents = [_make_agent(cid, belief=0.0)]

        opinion = _make_expert_opinion(score=0.8, community_id=cid, confidence=0.9)
        result = model.update_community_sentiment(cid, agents, [opinion])

        assert result.mean_belief > 0.0

    def test_filters_agents_by_community(self):
        model = SentimentModel()
        cid1 = uuid4()
        cid2 = uuid4()
        agents = [
            _make_agent(cid1, belief=1.0),
            _make_agent(cid2, belief=-1.0),  # different community
        ]

        result = model.update_community_sentiment(cid1, agents, [])
        assert result.mean_belief == pytest.approx(1.0, abs=0.01)

    def test_expert_only_affects_target_community(self):
        model = SentimentModel()
        cid1 = uuid4()
        cid2 = uuid4()
        agents = [_make_agent(cid1, belief=0.5)]

        opinion = _make_expert_opinion(score=-1.0, community_id=cid2)
        result = model.update_community_sentiment(cid1, agents, [opinion])

        # Opinion targets cid2, not cid1, so no effect
        assert result.mean_belief == pytest.approx(0.5, abs=0.01)


@pytest.mark.phase4
@pytest.mark.unit
class TestSentimentModelPolarization:
    """SPEC: 03_DIFFUSION_SPEC.md#sentimentmodel"""

    def test_no_polarization(self):
        model = SentimentModel()
        communities = [
            CommunitySentiment(
                community_id=uuid4(), mean_belief=0.5,
                sentiment_variance=0.1, adoption_rate=0.5, step=1,
            ),
        ]
        assert model.detect_polarization(communities) is False

    def test_polarization_detected(self):
        """DIF-05: Polarization detection."""
        model = SentimentModel()
        communities = [
            CommunitySentiment(
                community_id=uuid4(), mean_belief=0.5,
                sentiment_variance=0.5, adoption_rate=0.5, step=1,
            ),
        ]
        assert model.detect_polarization(communities) is True

    def test_custom_threshold(self):
        model = SentimentModel()
        communities = [
            CommunitySentiment(
                community_id=uuid4(), mean_belief=0.5,
                sentiment_variance=0.3, adoption_rate=0.5, step=1,
            ),
        ]
        assert model.detect_polarization(communities, threshold=0.2) is True
        assert model.detect_polarization(communities, threshold=0.5) is False

    def test_empty_communities(self):
        model = SentimentModel()
        assert model.detect_polarization([]) is False
