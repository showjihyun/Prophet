"""
Auto-generated from SPEC: docs/spec/01_AGENT_SPEC.md#data-schema
SPEC Version: 0.2.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest
from uuid import uuid4


@pytest.mark.phase2
class TestAgentPersonality:
    """SPEC: 01_AGENT_SPEC.md#data-schema — AgentPersonality"""

    def test_valid_construction(self):
        """All fields in [0.0, 1.0] should succeed."""
        from app.engine.agent.schema import AgentPersonality
        p = AgentPersonality(
            openness=0.5, skepticism=0.5, trend_following=0.5,
            brand_loyalty=0.5, social_influence=0.5,
        )
        assert p.openness == 0.5
        assert p.skepticism == 0.5

    def test_boundary_zero(self):
        """All fields at 0.0 should succeed."""
        from app.engine.agent.schema import AgentPersonality
        p = AgentPersonality(0.0, 0.0, 0.0, 0.0, 0.0)
        assert p.openness == 0.0

    def test_boundary_one(self):
        """All fields at 1.0 should succeed."""
        from app.engine.agent.schema import AgentPersonality
        p = AgentPersonality(1.0, 1.0, 1.0, 1.0, 1.0)
        assert p.social_influence == 1.0

    def test_rejects_negative(self):
        """Negative value raises ValueError."""
        from app.engine.agent.schema import AgentPersonality
        with pytest.raises(ValueError, match="openness"):
            AgentPersonality(-0.1, 0.5, 0.5, 0.5, 0.5)

    def test_rejects_over_one(self):
        """Value > 1.0 raises ValueError."""
        from app.engine.agent.schema import AgentPersonality
        with pytest.raises(ValueError, match="skepticism"):
            AgentPersonality(0.5, 1.1, 0.5, 0.5, 0.5)

    def test_as_vector(self):
        """as_vector() returns 5-element list in field order."""
        from app.engine.agent.schema import AgentPersonality
        p = AgentPersonality(0.1, 0.2, 0.3, 0.4, 0.5)
        assert p.as_vector() == [0.1, 0.2, 0.3, 0.4, 0.5]

    def test_frozen(self):
        """AgentPersonality is immutable (frozen dataclass)."""
        from app.engine.agent.schema import AgentPersonality
        p = AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5)
        with pytest.raises(AttributeError):
            p.openness = 0.9


@pytest.mark.phase2
class TestAgentEmotion:
    """SPEC: 01_AGENT_SPEC.md#data-schema — AgentEmotion"""

    def test_valid_construction(self):
        from app.engine.agent.schema import AgentEmotion
        e = AgentEmotion(interest=0.5, trust=0.5, skepticism=0.5, excitement=0.3)
        assert e.interest == 0.5

    def test_clamped_returns_valid(self):
        """clamped() should bring out-of-range values into [0.0, 1.0]."""
        from app.engine.agent.schema import AgentEmotion
        e = AgentEmotion(interest=1.5, trust=-0.3, skepticism=0.5, excitement=2.0)
        c = e.clamped()
        assert c.interest == 1.0
        assert c.trust == 0.0
        assert c.skepticism == 0.5
        assert c.excitement == 1.0

    def test_clamped_no_change_if_valid(self):
        from app.engine.agent.schema import AgentEmotion
        e = AgentEmotion(0.5, 0.5, 0.5, 0.3)
        c = e.clamped()
        assert c.interest == e.interest
        assert c.trust == e.trust


@pytest.mark.phase2
class TestAgentState:
    """SPEC: 01_AGENT_SPEC.md#data-schema — AgentState"""

    def test_construction_with_defaults(self):
        from app.engine.agent.schema import (
            AgentState, AgentPersonality, AgentEmotion, AgentType, AgentAction,
        )
        state = AgentState(
            agent_id=uuid4(),
            simulation_id=uuid4(),
            agent_type=AgentType.CONSUMER,
            step=0,
            personality=AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5),
            emotion=AgentEmotion(0.5, 0.5, 0.5, 0.3),
            belief=0.0,
            action=AgentAction.IGNORE,
            exposure_count=0,
            adopted=False,
            community_id=uuid4(),
            influence_score=0.0,
            llm_tier_used=None,
        )
        assert len(state.activity_vector) == 24
        assert all(0.0 <= v <= 1.0 for v in state.activity_vector)


@pytest.mark.phase2
class TestMemoryConfig:
    """SPEC: 01_AGENT_SPEC.md#layer-2-memorylayer — MemoryConfig"""

    def test_default_weights_sum_to_one(self):
        from app.engine.agent.memory import MemoryConfig
        cfg = MemoryConfig()
        total = cfg.alpha + cfg.beta + cfg.gamma + cfg.delta
        assert abs(total - 1.0) < 0.01

    def test_rejects_invalid_weight_sum(self):
        from app.engine.agent.memory import MemoryConfig
        with pytest.raises(ValueError, match="sum to 1.0"):
            MemoryConfig(alpha=0.5, beta=0.5, gamma=0.5, delta=0.5)


@pytest.mark.phase2
class TestMessageStrength:
    """SPEC: 01_AGENT_SPEC.md#layer-6-influencelayer — MessageStrength
    SPEC: 26_DIFFUSION_CALIBRATION_SPEC.md (Round 8-3)

    Round 8-3 formula: 0.6·utility + 0.5·novelty − 0.7·controversy + 0.3.
    Stronger coefficients than R7-d so extreme campaign designs can
    actually produce "stuck at 12%" and "viral cascade" outcomes in
    community-level simulations.
    """

    def test_score_neutral_inputs_equals_baseline(self):
        """Neutral 0.5/0.5/0.5 → 0.3 + 0.25 − 0.35 + 0.3 = 0.50."""
        from app.engine.agent.influence import MessageStrength
        ms = MessageStrength(novelty=0.5, controversy=0.5, utility=0.5)
        assert abs(ms.score - 0.50) < 0.001

    def test_score_best_case_clamps_to_one(self):
        """Best (u=1, n=1, c=0) → 0.6 + 0.5 + 0 + 0.3 = 1.4 → clamp 1.0."""
        from app.engine.agent.influence import MessageStrength
        ms = MessageStrength(novelty=1.0, controversy=0.0, utility=1.0)
        assert ms.score == 1.0

    def test_score_worst_case_clamps_to_zero(self):
        """Worst (u=0, n=0, c=1) → 0 + 0 − 0.7 + 0.3 = −0.4 → clamp 0.0.

        Crucial for "stuck at 12%" scenarios: the worst possible
        campaign produces zero propagation headroom, so downstream
        factors (influence × trust × emotion) can drive cohort
        adoption all the way to stall.
        """
        from app.engine.agent.influence import MessageStrength
        ms = MessageStrength(novelty=0.0, controversy=1.0, utility=0.0)
        assert ms.score == 0.0

    def test_reframed_campaign_scores_higher_than_controversial_one(self):
        """Round 8-3 spread: reframed (0.86) vs high-controversy (0.31)."""
        from app.engine.agent.influence import MessageStrength
        reframed = MessageStrength(novelty=0.8, controversy=0.2, utility=0.5)
        hot = MessageStrength(novelty=0.4, controversy=0.7, utility=0.5)
        assert abs(reframed.score - 0.86) < 0.01
        assert abs(hot.score - 0.31) < 0.01
        # Spread should be > 2× so community-level divergence is visible
        assert reframed.score / hot.score > 2.0

    def test_rejects_out_of_range(self):
        from app.engine.agent.influence import MessageStrength
        with pytest.raises(ValueError, match="novelty"):
            MessageStrength(novelty=1.5, controversy=0.3, utility=0.9)


@pytest.mark.phase2
class TestTierConfig:
    """SPEC: 01_AGENT_SPEC.md#tier-selection — TierConfig"""

    def test_default_ratios(self):
        from app.engine.agent.tier_selector import TierConfig
        cfg = TierConfig()
        assert cfg.max_tier3_ratio == 0.10
        assert cfg.max_tier2_ratio == 0.10

    def test_rejects_over_half(self):
        from app.engine.agent.tier_selector import TierConfig
        with pytest.raises(ValueError, match="50%"):
            TierConfig(max_tier3_ratio=0.3, max_tier2_ratio=0.3)
