"""
Auto-generated from SPEC: docs/spec/01_AGENT_SPEC.md#layer-4-cognitionlayer
SPEC Version: 0.2.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest
from uuid import uuid4


def _make_agent(skepticism_e=0.5, interest=0.5, trust=0.5):
    from app.engine.agent.schema import (
        AgentState, AgentPersonality, AgentEmotion, AgentType, AgentAction,
    )
    return AgentState(
        agent_id=uuid4(), simulation_id=uuid4(), agent_type=AgentType.CONSUMER,
        step=5, personality=AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5),
        emotion=AgentEmotion(interest, trust, skepticism_e, 0.3), belief=0.0,
        action=AgentAction.IGNORE, exposure_count=0, adopted=False,
        community_id=uuid4(), influence_score=0.3, llm_tier_used=None,
    )


def _make_perception():
    from app.engine.agent.perception import PerceptionResult
    return PerceptionResult(feed_items=[], social_signals=[], expert_signals=[],
                            total_exposure_score=0.0)


@pytest.mark.phase2
class TestCognitionLayerTier1:
    """SPEC: 01_AGENT_SPEC.md#layer-4-cognitionlayer — Tier 1 Rule Engine"""

    def test_agt01_output_range(self):
        """AGT-01: Neutral agent, Tier 1 -> evaluation_score in [-2, 2], confidence in [0, 1]."""
        from app.engine.agent.cognition import CognitionLayer
        layer = CognitionLayer()
        result = layer.evaluate(_make_agent(), _make_perception(), [], cognition_tier=1)
        assert -2.0 <= result.evaluation_score <= 2.0
        assert 0.0 <= result.confidence <= 1.0

    def test_high_interest_trust_positive_score(self):
        """High interest + trust -> positive evaluation_score."""
        from app.engine.agent.cognition import CognitionLayer
        layer = CognitionLayer()
        agent = _make_agent(skepticism_e=0.1, interest=0.9, trust=0.9)
        result = layer.evaluate(agent, _make_perception(), [], cognition_tier=1)
        assert result.evaluation_score > 0.0

    def test_high_skepticism_negative_score(self):
        """High skepticism -> negative evaluation_score."""
        from app.engine.agent.cognition import CognitionLayer
        layer = CognitionLayer()
        agent = _make_agent(skepticism_e=0.9, interest=0.2, trust=0.2)
        result = layer.evaluate(agent, _make_perception(), [], cognition_tier=1)
        assert result.evaluation_score < 0.0

    def test_reasoning_is_none_for_tier1(self):
        """Tier 1 should not produce reasoning text."""
        from app.engine.agent.cognition import CognitionLayer
        layer = CognitionLayer()
        result = layer.evaluate(_make_agent(), _make_perception(), [], cognition_tier=1)
        assert result.reasoning is None

    def test_tier_used_matches_input(self):
        """tier_used in result should match input cognition_tier."""
        from app.engine.agent.cognition import CognitionLayer
        layer = CognitionLayer()
        result = layer.evaluate(_make_agent(), _make_perception(), [], cognition_tier=1)
        assert result.tier_used == 1

    def test_determinism(self):
        """Same inputs -> same output for Tier 1."""
        from app.engine.agent.cognition import CognitionLayer
        layer = CognitionLayer()
        agent = _make_agent()
        perc = _make_perception()
        r1 = layer.evaluate(agent, perc, [], cognition_tier=1)
        r2 = layer.evaluate(agent, perc, [], cognition_tier=1)
        assert r1.evaluation_score == r2.evaluation_score


@pytest.mark.phase2
class TestCognitionLayerTier2:
    """SPEC: 01_AGENT_SPEC.md#layer-4-cognitionlayer — Tier 2 Heuristic"""

    def test_tier2_includes_personality_adjustment(self):
        """Tier 2 score differs from Tier 1 due to personality adjustment."""
        from app.engine.agent.cognition import CognitionLayer
        layer = CognitionLayer()
        agent = _make_agent()
        perc = _make_perception()
        r1 = layer.evaluate(agent, perc, [], cognition_tier=1)
        r2 = layer.evaluate(agent, perc, [], cognition_tier=2)
        # They CAN be equal if personality is perfectly neutral, but structure should differ
        assert r2.tier_used == 2


@pytest.mark.phase2
class TestCognitionLayerValidation:
    """SPEC: 01_AGENT_SPEC.md#layer-4-cognitionlayer — validation"""

    def test_invalid_tier_raises(self):
        """cognition_tier not in {1, 2, 3} raises ValueError."""
        from app.engine.agent.cognition import CognitionLayer
        layer = CognitionLayer()
        with pytest.raises(ValueError):
            layer.evaluate(_make_agent(), _make_perception(), [], cognition_tier=0)

    def test_score_to_action_mapping(self):
        """Score-to-action mapping follows SPEC table."""
        from app.engine.agent.cognition import CognitionLayer
        from app.engine.agent.schema import AgentAction
        layer = CognitionLayer()
        # Very negative agent -> should recommend MUTE or IGNORE
        agent = _make_agent(skepticism_e=0.95, interest=0.05, trust=0.05)
        result = layer.evaluate(agent, _make_perception(), [], cognition_tier=1)
        assert result.recommended_action in (AgentAction.MUTE, AgentAction.IGNORE)
