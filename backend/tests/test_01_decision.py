"""
Auto-generated from SPEC: docs/spec/01_AGENT_SPEC.md#layer-5-decisionlayer
SPEC Version: 0.2.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest
from uuid import uuid4


def _make_cognition(score=0.5):
    from app.engine.agent.cognition import CognitionResult
    from app.engine.agent.schema import AgentAction
    return CognitionResult(
        evaluation_score=score, reasoning=None,
        recommended_action=AgentAction.LIKE, confidence=0.5, tier_used=1,
    )


def _make_personality():
    from app.engine.agent.schema import AgentPersonality
    return AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5)


@pytest.mark.phase2
class TestDecisionLayerChooseAction:
    """SPEC: 01_AGENT_SPEC.md#layer-5-decisionlayer — choose_action()"""

    def test_returns_valid_action(self):
        """Always returns a valid AgentAction enum value."""
        from app.engine.agent.decision import DecisionLayer
        from app.engine.agent.schema import AgentAction
        layer = DecisionLayer()
        action = layer.choose_action(_make_cognition(), social_pressure=0.0,
                                     personality=_make_personality(), agent_seed=42)
        assert isinstance(action, AgentAction)

    def test_deterministic_with_same_seed(self):
        """AGT-11: Same seed -> same action."""
        from app.engine.agent.decision import DecisionLayer
        layer = DecisionLayer()
        cog = _make_cognition(0.7)
        p = _make_personality()
        a1 = layer.choose_action(cog, 0.3, p, agent_seed=42)
        a2 = layer.choose_action(cog, 0.3, p, agent_seed=42)
        assert a1 == a2

    def test_different_seeds_may_differ(self):
        """Different seeds can produce different actions (probabilistic)."""
        from app.engine.agent.decision import DecisionLayer
        layer = DecisionLayer()
        cog = _make_cognition(0.5)
        p = _make_personality()
        actions = set()
        for seed in range(100):
            actions.add(layer.choose_action(cog, 0.3, p, agent_seed=seed))
        # With 100 different seeds on a moderate score, should get at least 2 different actions
        assert len(actions) >= 2

    def test_high_positive_score_favors_positive_actions(self):
        """Very positive evaluation + social pressure -> positive actions dominate."""
        from app.engine.agent.decision import DecisionLayer
        from app.engine.agent.schema import AgentAction
        layer = DecisionLayer()
        cog = _make_cognition(1.8)
        p = _make_personality()
        actions = [layer.choose_action(cog, 2.0, p, agent_seed=s) for s in range(200)]
        positive = {AgentAction.LIKE, AgentAction.SAVE, AgentAction.COMMENT,
                    AgentAction.SHARE, AgentAction.REPOST, AgentAction.ADOPT}
        positive_count = sum(1 for a in actions if a in positive)
        assert positive_count / len(actions) > 0.7


@pytest.mark.phase2
class TestComputeSocialPressure:
    """SPEC: 01_AGENT_SPEC.md#layer-5-decisionlayer — compute_social_pressure()"""

    def test_agt13_social_pressure_example(self):
        """AGT-13: 3 neighbors SHARE(W=0.8), LIKE(W=0.5), MUTE(W=0.3)."""
        from app.engine.agent.decision import DecisionLayer
        from app.engine.agent.perception import NeighborAction
        from app.engine.agent.schema import AgentAction
        layer = DecisionLayer()
        agent_id = uuid4()
        n1, n2, n3 = uuid4(), uuid4(), uuid4()
        neighbors = [
            NeighborAction(agent_id=n1, action=AgentAction.SHARE, content_id=uuid4(), step=5),
            NeighborAction(agent_id=n2, action=AgentAction.LIKE, content_id=uuid4(), step=5),
            NeighborAction(agent_id=n3, action=AgentAction.MUTE, content_id=uuid4(), step=5),
        ]
        trust_matrix = {
            (agent_id, n1): 0.8,
            (agent_id, n2): 0.5,
            (agent_id, n3): 0.3,
        }
        result = layer.compute_social_pressure(agent_id, neighbors, trust_matrix)
        # SHARE weight=0.8, LIKE weight=0.3, MUTE weight=-0.5
        expected = 0.8 * 0.8 + 0.5 * 0.3 + 0.3 * (-0.5)
        assert abs(result - expected) < 0.01

    def test_empty_neighbors_returns_zero(self):
        """No neighbors -> social pressure = 0.0."""
        from app.engine.agent.decision import DecisionLayer
        layer = DecisionLayer()
        result = layer.compute_social_pressure(uuid4(), [], {})
        assert result == 0.0

    def test_missing_trust_defaults_to_zero(self):
        """Missing edge in trust_matrix defaults to 0.0 weight."""
        from app.engine.agent.decision import DecisionLayer
        from app.engine.agent.perception import NeighborAction
        from app.engine.agent.schema import AgentAction
        layer = DecisionLayer()
        agent_id = uuid4()
        neighbor_id = uuid4()
        neighbors = [NeighborAction(neighbor_id, AgentAction.SHARE, uuid4(), 5)]
        result = layer.compute_social_pressure(agent_id, neighbors, {})  # empty trust
        assert result == 0.0
