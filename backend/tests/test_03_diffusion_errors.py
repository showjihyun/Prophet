"""
Auto-generated from SPEC: docs/spec/03_DIFFUSION_SPEC.md#error-specification
SPEC Version: 0.1.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest
from uuid import uuid4


class TestDiffusionConfigValidation:
    """SPEC: 03_DIFFUSION_SPEC.md#error-specification — config validation"""

    def test_recsys_weight_sum_not_one_raises(self):
        """RecSys weight sum != 1.0 (±0.01) raises ValueError."""
        from app.engine.diffusion.exposure import ExposureModel, RecSysConfig
        with pytest.raises(ValueError):
            ExposureModel(RecSysConfig(
                relevance=0.4, recency=0.3, popularity=0.2, diversity=0.2
            ))  # sum = 1.1

    def test_recsys_weight_sum_exact_one_ok(self):
        """RecSys weight sum == 1.0 passes validation."""
        from app.engine.diffusion.exposure import ExposureModel, RecSysConfig
        model = ExposureModel(RecSysConfig(
            relevance=0.4, recency=0.3, popularity=0.2, diversity=0.1
        ))
        assert model is not None

    def test_empty_agent_list_raises(self):
        """ExposureModel with empty agent list raises ValueError."""
        from app.engine.diffusion.exposure import ExposureModel, RecSysConfig
        model = ExposureModel(RecSysConfig(
            relevance=0.4, recency=0.3, popularity=0.2, diversity=0.1
        ))
        with pytest.raises(ValueError):
            model.compute_exposure(agents=[], campaign=None, step=1)

    def test_cascade_threshold_zero_raises(self):
        """Cascade threshold <= 0 raises ValueError."""
        from app.engine.diffusion.cascade import CascadeDetector, CascadeConfig
        with pytest.raises(ValueError):
            CascadeDetector(CascadeConfig(viral_threshold=0))

    def test_cascade_threshold_negative_raises(self):
        """Cascade threshold < 0 raises ValueError."""
        from app.engine.diffusion.cascade import CascadeDetector, CascadeConfig
        with pytest.raises(ValueError):
            CascadeDetector(CascadeConfig(viral_threshold=-5))


class TestDiffusionPropagationClamping:
    """SPEC: 03_DIFFUSION_SPEC.md#error-specification — probability clamping"""

    def test_propagation_probability_clamped_above_one(self):
        """Probability > 1.0 is clamped to 1.0."""
        from app.engine.diffusion.propagation import PropagationModel
        model = PropagationModel()
        clamped = model._clamp_probability(1.5)
        assert clamped == 1.0

    def test_propagation_probability_clamped_below_zero(self):
        """Probability < 0.0 is clamped to 0.0."""
        from app.engine.diffusion.propagation import PropagationModel
        model = PropagationModel()
        clamped = model._clamp_probability(-0.3)
        assert clamped == 0.0

    def test_negative_diffusion_rate_clamped(self):
        """Negative R(t) is clamped to 0.0."""
        from app.engine.diffusion.propagation import PropagationModel
        model = PropagationModel()
        rate = model._clamp_diffusion_rate(-0.1)
        assert rate == 0.0


class TestDiffusionGracefulDegradation:
    """SPEC: 03_DIFFUSION_SPEC.md#error-specification — graceful degradation"""

    def test_no_active_campaign_returns_zero_exposure(self):
        """No active campaign → all exposure scores = 0.0."""
        from app.engine.diffusion.exposure import ExposureModel, RecSysConfig
        from app.engine.agent.schema import (
            AgentState, AgentPersonality, AgentEmotion, AgentType, AgentAction,
        )
        model = ExposureModel(RecSysConfig(
            relevance=0.4, recency=0.3, popularity=0.2, diversity=0.1
        ))
        agents = [AgentState(
            agent_id=uuid4(), simulation_id=uuid4(), agent_type=AgentType.CONSUMER,
            step=1, personality=AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5),
            emotion=AgentEmotion(0.5, 0.5, 0.5, 0.3), belief=0.0,
            action=AgentAction.IGNORE, exposure_count=0, adopted=False,
            community_id=uuid4(), influence_score=0.3, llm_tier_used=None,
        )]
        scores = model.compute_exposure(agents=agents, campaign=None, step=1)
        assert all(s == 0.0 for s in scores.values())

    def test_cascade_detector_insufficient_steps_returns_empty(self):
        """CascadeDetector with fewer steps than window_size returns empty."""
        from app.engine.diffusion.cascade import CascadeDetector, CascadeConfig
        detector = CascadeDetector(CascadeConfig(viral_threshold=10, window_size=5))
        events = detector.detect(step_data=[], current_step=2)  # only 2 steps < window 5
        assert events == []

    def test_empty_community_sentiment_returns_zero(self):
        """Empty community sentiment = 0.0 (no division by zero)."""
        from app.engine.diffusion.sentiment import SentimentModel
        model = SentimentModel()
        sentiment = model.compute_community_sentiment(community_agents=[])
        assert sentiment == 0.0


class TestDiffusionLLMFallback:
    """SPEC: 03_DIFFUSION_SPEC.md#error-specification — LLM fallback"""

    def test_expert_intervention_llm_timeout_falls_back(self):
        """ExpertIntervention LLM timeout → Tier 1 heuristic (sentiment = -0.3)."""
        from app.engine.diffusion.expert import ExpertInterventionEngine
        from unittest.mock import AsyncMock, patch
        engine = ExpertInterventionEngine()
        # Mock LLM to timeout
        with patch.object(engine, '_call_llm', side_effect=TimeoutError):
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                engine.get_expert_opinion(topic="test_campaign", context={})
            )
        assert result.score == pytest.approx(-0.3, abs=0.1)
        assert result.tier_used == 1

    def test_expert_intervention_llm_parse_error_falls_back(self):
        """ExpertIntervention LLM parse error → Tier 1 heuristic."""
        from app.engine.diffusion.expert import ExpertInterventionEngine
        from app.engine.llm.exceptions import LLMParseError
        from unittest.mock import patch
        engine = ExpertInterventionEngine()
        with patch.object(engine, '_call_llm', side_effect=LLMParseError("bad json")):
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                engine.get_expert_opinion(topic="test_campaign", context={})
            )
        assert result.tier_used == 1
