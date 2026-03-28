"""
Auto-generated from SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer
SPEC Version: 0.2.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest
from uuid import uuid4


def _make_agent():
    from app.engine.agent.schema import (
        AgentState, AgentPersonality, AgentEmotion, AgentType, AgentAction,
    )
    return AgentState(
        agent_id=uuid4(), simulation_id=uuid4(), agent_type=AgentType.CONSUMER,
        step=5, personality=AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5),
        emotion=AgentEmotion(0.5, 0.5, 0.5, 0.3), belief=0.0,
        action=AgentAction.IGNORE, exposure_count=0, adopted=False,
        community_id=uuid4(), influence_score=0.3, llm_tier_used=None,
    )


def _make_event(event_type="campaign_ad"):
    from app.engine.agent.perception import EnvironmentEvent
    return EnvironmentEvent(
        event_type=event_type, content_id=uuid4(), message="test ad",
        source_agent_id=None, channel="social_feed", timestamp=5,
    )


@pytest.mark.phase2
class TestPerceptionLayer:
    """SPEC: 01_AGENT_SPEC.md#layer-1-perceptionlayer"""

    def test_empty_inputs_return_empty(self):
        """Empty events + empty neighbors -> empty results, score=0.0."""
        from app.engine.agent.perception import PerceptionLayer
        layer = PerceptionLayer(feed_capacity=20)
        result = layer.observe(agent=_make_agent(), environment_events=[], neighbor_actions=[])
        assert result.feed_items == []
        assert result.social_signals == []
        assert result.expert_signals == []
        assert result.total_exposure_score == 0.0

    def test_feed_items_sorted_by_exposure_score_desc(self):
        """feed_items must be sorted by exposure_score descending."""
        from app.engine.agent.perception import PerceptionLayer
        events = [_make_event() for _ in range(5)]
        layer = PerceptionLayer(feed_capacity=20)
        result = layer.observe(agent=_make_agent(), environment_events=events, neighbor_actions=[])
        scores = [item.exposure_score for item in result.feed_items]
        assert scores == sorted(scores, reverse=True)

    def test_feed_capacity_truncation(self):
        """Output feed_items length <= feed_capacity."""
        from app.engine.agent.perception import PerceptionLayer
        events = [_make_event() for _ in range(30)]
        layer = PerceptionLayer(feed_capacity=10)
        result = layer.observe(agent=_make_agent(), environment_events=events, neighbor_actions=[])
        assert len(result.feed_items) <= 10

    def test_total_exposure_score_is_sum(self):
        """total_exposure_score == sum of feed_items exposure_scores."""
        from app.engine.agent.perception import PerceptionLayer
        events = [_make_event() for _ in range(5)]
        layer = PerceptionLayer(feed_capacity=20)
        result = layer.observe(agent=_make_agent(), environment_events=events, neighbor_actions=[])
        expected = sum(item.exposure_score for item in result.feed_items)
        assert abs(result.total_exposure_score - expected) < 1e-6

    def test_expert_signals_from_expert_review_only(self):
        """expert_signals should only contain expert_review events."""
        from app.engine.agent.perception import PerceptionLayer
        events = [_make_event("campaign_ad"), _make_event("expert_review")]
        layer = PerceptionLayer(feed_capacity=20)
        result = layer.observe(agent=_make_agent(), environment_events=events, neighbor_actions=[])
        assert len(result.expert_signals) == 1
        assert result.expert_signals[0].content_id == events[1].content_id

    def test_feed_capacity_rejects_zero(self):
        """feed_capacity <= 0 raises ValueError."""
        from app.engine.agent.perception import PerceptionLayer
        with pytest.raises(ValueError):
            PerceptionLayer(feed_capacity=0)

    def test_determinism(self):
        """Same inputs -> same output (pure function)."""
        from app.engine.agent.perception import PerceptionLayer
        agent = _make_agent()
        events = [_make_event() for _ in range(5)]
        layer = PerceptionLayer(feed_capacity=20)
        r1 = layer.observe(agent, events, [])
        r2 = layer.observe(agent, events, [])
        assert r1.total_exposure_score == r2.total_exposure_score
        assert len(r1.feed_items) == len(r2.feed_items)
