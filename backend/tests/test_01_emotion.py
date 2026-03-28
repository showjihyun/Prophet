"""
Auto-generated from SPEC: docs/spec/01_AGENT_SPEC.md#layer-3-emotionlayer
SPEC Version: 0.2.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest


@pytest.mark.phase2
class TestEmotionLayerUpdate:
    """SPEC: 01_AGENT_SPEC.md#layer-3-emotionlayer — update()"""

    def test_positive_expert_signal_increases_trust(self):
        """AGT-03: Expert signal=0.8 increases trust."""
        from app.engine.agent.emotion import EmotionLayer
        from app.engine.agent.schema import AgentEmotion
        layer = EmotionLayer()
        current = AgentEmotion(interest=0.5, trust=0.3, skepticism=0.5, excitement=0.3)
        result = layer.update(current, social_signal=0.0, media_signal=0.0, expert_signal=0.8)
        assert result.trust > 0.3

    def test_all_fields_clamped_to_unit(self):
        """All output fields in [0.0, 1.0]."""
        from app.engine.agent.emotion import EmotionLayer
        from app.engine.agent.schema import AgentEmotion
        layer = EmotionLayer()
        current = AgentEmotion(interest=0.95, trust=0.95, skepticism=0.05, excitement=0.95)
        result = layer.update(current, social_signal=1.0, media_signal=1.0, expert_signal=1.0)
        assert 0.0 <= result.interest <= 1.0
        assert 0.0 <= result.trust <= 1.0
        assert 0.0 <= result.skepticism <= 1.0
        assert 0.0 <= result.excitement <= 1.0

    def test_decay_reduces_emotions(self):
        """With zero signals and decay=0.1, all emotions should decrease."""
        from app.engine.agent.emotion import EmotionLayer
        from app.engine.agent.schema import AgentEmotion
        layer = EmotionLayer()
        current = AgentEmotion(interest=0.5, trust=0.5, skepticism=0.5, excitement=0.5)
        result = layer.update(current, social_signal=0.0, media_signal=0.0, expert_signal=0.0, decay=0.1)
        assert result.interest < 0.5
        assert result.trust < 0.5
        assert result.excitement < 0.5

    def test_negative_decay_raises(self):
        """decay < 0 raises ValueError."""
        from app.engine.agent.emotion import EmotionLayer
        from app.engine.agent.schema import AgentEmotion
        layer = EmotionLayer()
        with pytest.raises(ValueError):
            layer.update(AgentEmotion(0.5, 0.5, 0.5, 0.5), 0.0, 0.0, 0.0, decay=-0.1)

    def test_determinism(self):
        """Same inputs -> same output (pure function)."""
        from app.engine.agent.emotion import EmotionLayer
        from app.engine.agent.schema import AgentEmotion
        layer = EmotionLayer()
        current = AgentEmotion(0.5, 0.5, 0.5, 0.3)
        r1 = layer.update(current, 0.3, 0.2, 0.1)
        r2 = layer.update(current, 0.3, 0.2, 0.1)
        assert r1.interest == r2.interest
        assert r1.trust == r2.trust


@pytest.mark.phase2
class TestEmotionFactor:
    """SPEC: 01_AGENT_SPEC.md#layer-3-emotionlayer — emotion_factor()"""

    def test_positive_when_excited(self):
        from app.engine.agent.emotion import EmotionLayer
        from app.engine.agent.schema import AgentEmotion
        layer = EmotionLayer()
        e = AgentEmotion(interest=0.5, trust=0.5, skepticism=0.2, excitement=0.8)
        assert layer.emotion_factor(e) == pytest.approx(0.6, abs=0.01)

    def test_negative_when_skeptical(self):
        from app.engine.agent.emotion import EmotionLayer
        from app.engine.agent.schema import AgentEmotion
        layer = EmotionLayer()
        e = AgentEmotion(interest=0.5, trust=0.5, skepticism=0.9, excitement=0.2)
        assert layer.emotion_factor(e) == pytest.approx(-0.7, abs=0.01)

    def test_clamped_to_minus_one_one(self):
        """Result always in [-1.0, 1.0]."""
        from app.engine.agent.emotion import EmotionLayer
        from app.engine.agent.schema import AgentEmotion
        layer = EmotionLayer()
        e = AgentEmotion(interest=0.5, trust=0.5, skepticism=0.0, excitement=1.0)
        assert -1.0 <= layer.emotion_factor(e) <= 1.0
