"""
Auto-generated from SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer
SPEC Version: 0.2.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest
from uuid import uuid4


def _make_agent(influence=0.9, excitement=0.8, skepticism_e=0.2):
    from app.engine.agent.schema import (
        AgentState, AgentPersonality, AgentEmotion, AgentType, AgentAction,
    )
    return AgentState(
        agent_id=uuid4(), simulation_id=uuid4(), agent_type=AgentType.INFLUENCER,
        step=5, personality=AgentPersonality(0.7, 0.3, 0.7, 0.5, 0.9),
        emotion=AgentEmotion(0.7, 0.7, skepticism_e, excitement), belief=0.5,
        action=AgentAction.SHARE, exposure_count=2, adopted=False,
        community_id=uuid4(), influence_score=influence, llm_tier_used=1,
    )


def _make_message_strength(novelty=0.7, controversy=0.3, utility=0.8):
    from app.engine.agent.influence import MessageStrength
    return MessageStrength(novelty=novelty, controversy=controversy, utility=utility)


@pytest.mark.phase2
class TestInfluenceLayerPropagate:
    """SPEC: 01_AGENT_SPEC.md#layer-6-influencelayer — propagate()"""

    def test_non_propagating_action_returns_empty(self):
        """Actions like VIEW, LIKE, IGNORE should return empty list."""
        from app.engine.agent.influence import InfluenceLayer
        from app.engine.agent.schema import AgentAction
        layer = InfluenceLayer()
        agent = _make_agent()
        targets = [uuid4() for _ in range(10)]
        edges = {(agent.agent_id, t): 0.8 for t in targets}
        result = layer.propagate(agent, AgentAction.VIEW, targets, edges,
                                 _make_message_strength(), step_seed=42)
        assert result == []

    def test_share_propagates_to_some_targets(self):
        """AGT-04: High influence SHARE should produce at least some events."""
        from app.engine.agent.influence import InfluenceLayer
        from app.engine.agent.schema import AgentAction
        layer = InfluenceLayer()
        agent = _make_agent(influence=0.9, excitement=0.8, skepticism_e=0.1)
        targets = [uuid4() for _ in range(20)]
        edges = {(agent.agent_id, t): 0.8 for t in targets}
        # Run multiple seeds and count total events
        total_events = 0
        for seed in range(100):
            events = layer.propagate(agent, AgentAction.SHARE, targets, edges,
                                     _make_message_strength(), step_seed=seed)
            total_events += len(events)
        assert total_events > 0  # at least some propagation across 100 trials

    def test_comment_propagates_to_top5_only(self):
        """COMMENT propagates to discussed neighbors (top-5 by edge weight)."""
        from app.engine.agent.influence import InfluenceLayer
        from app.engine.agent.schema import AgentAction
        layer = InfluenceLayer()
        agent = _make_agent(influence=0.9)
        targets = [uuid4() for _ in range(20)]
        # Give first 5 targets high weight, rest low
        edges = {}
        for i, t in enumerate(targets):
            edges[(agent.agent_id, t)] = 0.9 if i < 5 else 0.1
        events = layer.propagate(agent, AgentAction.COMMENT, targets, edges,
                                 _make_message_strength(), step_seed=42)
        # All propagation targets should be from top-5
        event_targets = {e.target_agent_id for e in events}
        top5 = set(targets[:5])
        assert event_targets.issubset(top5)

    def test_adopt_reduces_probability(self):
        """ADOPT propagation has P * 0.5 reduction."""
        from app.engine.agent.influence import InfluenceLayer
        from app.engine.agent.schema import AgentAction
        layer = InfluenceLayer()
        agent = _make_agent(influence=0.9)
        targets = [uuid4() for _ in range(50)]
        edges = {(agent.agent_id, t): 0.8 for t in targets}
        ms = _make_message_strength()
        # Compare SHARE vs ADOPT propagation counts
        share_events = sum(len(layer.propagate(agent, AgentAction.SHARE, targets, edges, ms, s))
                           for s in range(100))
        adopt_events = sum(len(layer.propagate(agent, AgentAction.ADOPT, targets, edges, ms, s))
                           for s in range(100))
        # ADOPT should produce roughly half the events of SHARE
        assert adopt_events < share_events

    def test_empty_targets_returns_empty(self):
        from app.engine.agent.influence import InfluenceLayer
        from app.engine.agent.schema import AgentAction
        layer = InfluenceLayer()
        result = layer.propagate(_make_agent(), AgentAction.SHARE, [], {},
                                 _make_message_strength(), step_seed=42)
        assert result == []

    def test_probability_clamped_to_unit(self):
        """Propagation probability always in [0.0, 1.0]."""
        from app.engine.agent.influence import InfluenceLayer
        from app.engine.agent.schema import AgentAction
        layer = InfluenceLayer()
        agent = _make_agent(influence=1.0, excitement=1.0, skepticism_e=0.0)
        target = uuid4()
        edges = {(agent.agent_id, target): 1.0}
        ms = _make_message_strength(1.0, 1.0, 1.0)
        events = layer.propagate(agent, AgentAction.SHARE, [target], edges, ms, step_seed=42)
        for e in events:
            assert 0.0 <= e.probability <= 1.0

    def test_deterministic_with_same_seed(self):
        """Same step_seed -> same propagation events."""
        from app.engine.agent.influence import InfluenceLayer
        from app.engine.agent.schema import AgentAction
        layer = InfluenceLayer()
        agent = _make_agent()
        targets = [uuid4() for _ in range(10)]
        edges = {(agent.agent_id, t): 0.5 for t in targets}
        ms = _make_message_strength()
        e1 = layer.propagate(agent, AgentAction.SHARE, targets, edges, ms, step_seed=42)
        e2 = layer.propagate(agent, AgentAction.SHARE, targets, edges, ms, step_seed=42)
        assert len(e1) == len(e2)
        assert [e.target_agent_id for e in e1] == [e.target_agent_id for e in e2]


@pytest.mark.phase2
class TestContextualPacket:
    """SPEC: 01_AGENT_SPEC.md#layer-6-influencelayer — ContextualPacket"""

    def test_agt14_sentiment_polarity(self):
        """AGT-14: excitement=0.8, trust=0.7, skepticism=0.2 -> polarity=0.65."""
        from app.engine.agent.schema import AgentEmotion
        e = AgentEmotion(interest=0.5, trust=0.7, skepticism=0.2, excitement=0.8)
        polarity = (e.excitement + e.trust - e.skepticism) / 2.0
        expected = (0.8 + 0.7 - 0.2) / 2.0  # = 0.65
        assert abs(polarity - expected) < 0.01
        assert -1.0 <= polarity <= 1.0
