"""
Auto-generated from SPEC: docs/spec/01_AGENT_SPEC.md#personality-drift
SPEC Version: 0.2.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest


@pytest.mark.phase2
class TestPersonalityDrift:
    """SPEC: 01_AGENT_SPEC.md#personality-drift"""

    def test_agt07_adopt_increases_openness(self):
        """AGT-07: 10 ADOPT actions -> openness increases by ~0.05."""
        from app.engine.agent.drift import PersonalityDrift
        from app.engine.agent.schema import AgentPersonality, AgentAction
        drift = PersonalityDrift()
        p = AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5)
        cumulative = {"openness": 0.0, "skepticism": 0.0, "trend_following": 0.0,
                       "brand_loyalty": 0.0, "social_influence": 0.0}
        for _ in range(10):
            p, cumulative = drift.apply_drift(p, AgentAction.ADOPT, cumulative)
        # 10 * 0.01 (learning_rate) * 0.01 (delta) = 0.001 per step? No...
        # DRIFT_TABLE: ADOPT -> openness: 0.01, so 10 * 0.01 = 0.1
        assert p.openness >= 0.55  # at least some increase

    def test_agt12_drift_capped_at_03(self):
        """AGT-12: Max drift per dimension = 0.3."""
        from app.engine.agent.drift import PersonalityDrift
        from app.engine.agent.schema import AgentPersonality, AgentAction
        drift = PersonalityDrift()
        p = AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5)
        cumulative = {"openness": 0.0, "skepticism": 0.0, "trend_following": 0.0,
                       "brand_loyalty": 0.0, "social_influence": 0.0}
        for _ in range(100):
            p, cumulative = drift.apply_drift(p, AgentAction.ADOPT, cumulative)
        assert p.openness <= 0.8  # 0.5 + 0.3 cap

    def test_no_drift_for_ignore(self):
        """IGNORE action produces no personality change."""
        from app.engine.agent.drift import PersonalityDrift
        from app.engine.agent.schema import AgentPersonality, AgentAction
        drift = PersonalityDrift()
        p = AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5)
        cumulative = {"openness": 0.0, "skepticism": 0.0, "trend_following": 0.0,
                       "brand_loyalty": 0.0, "social_influence": 0.0}
        p2, cum2 = drift.apply_drift(p, AgentAction.IGNORE, cumulative)
        assert p2 == p
        assert cum2 == cumulative

    def test_mute_increases_skepticism(self):
        """MUTE action increases personality skepticism."""
        from app.engine.agent.drift import PersonalityDrift
        from app.engine.agent.schema import AgentPersonality, AgentAction
        drift = PersonalityDrift()
        p = AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5)
        cumulative = {"openness": 0.0, "skepticism": 0.0, "trend_following": 0.0,
                       "brand_loyalty": 0.0, "social_influence": 0.0}
        p2, _ = drift.apply_drift(p, AgentAction.MUTE, cumulative)
        assert p2.skepticism > 0.5

    def test_personality_stays_in_range(self):
        """All personality fields remain in [0.0, 1.0] after drift."""
        from app.engine.agent.drift import PersonalityDrift
        from app.engine.agent.schema import AgentPersonality, AgentAction
        drift = PersonalityDrift()
        p = AgentPersonality(0.99, 0.99, 0.99, 0.99, 0.99)
        cumulative = {"openness": 0.0, "skepticism": 0.0, "trend_following": 0.0,
                       "brand_loyalty": 0.0, "social_influence": 0.0}
        for _ in range(50):
            p, cumulative = drift.apply_drift(p, AgentAction.SHARE, cumulative)
        for f in ['openness', 'skepticism', 'trend_following', 'brand_loyalty', 'social_influence']:
            assert 0.0 <= getattr(p, f) <= 1.0
