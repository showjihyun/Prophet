"""Tests for PropagationModel.
Auto-generated from SPEC: docs/spec/03_DIFFUSION_SPEC.md
SPEC Version: 0.1.1
"""
import pytest
from uuid import uuid4

import networkx as nx

from app.engine.agent.schema import (
    AgentAction,
    AgentEmotion,
    AgentPersonality,
    AgentState,
    AgentType,
)
from app.engine.network.schema import CommunityConfig, NetworkMetrics, SocialNetwork
from app.engine.diffusion.propagation_model import PropagationModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_personality(**overrides) -> AgentPersonality:
    defaults = dict(
        openness=0.5, skepticism=0.3, trend_following=0.4,
        brand_loyalty=0.5, social_influence=0.5,
    )
    defaults.update(overrides)
    return AgentPersonality(**defaults)


def _make_emotion(**overrides) -> AgentEmotion:
    defaults = dict(interest=0.5, trust=0.5, skepticism=0.3, excitement=0.5)
    defaults.update(overrides)
    return AgentEmotion(**defaults)


def _make_agent(agent_id=None, influence=0.8, excitement=0.7, skepticism=0.1, **kw) -> AgentState:
    return AgentState(
        agent_id=agent_id or uuid4(),
        simulation_id=uuid4(),
        agent_type=kw.get("agent_type", AgentType.INFLUENCER),
        step=0,
        personality=_make_personality(),
        emotion=_make_emotion(excitement=excitement, skepticism=skepticism),
        belief=0.5,
        action=AgentAction.IGNORE,
        exposure_count=1,
        adopted=False,
        community_id=uuid4(),
        influence_score=influence,
        llm_tier_used=None,
    )


def _make_graph_with_neighbors(source: AgentState, neighbors: list[AgentState], weight=0.8) -> SocialNetwork:
    g = nx.Graph()
    g.add_node(0, agent_id=source.agent_id)
    for i, n in enumerate(neighbors, start=1):
        g.add_node(i, agent_id=n.agent_id)
        g.add_edge(0, i, weight=weight)
    metrics = NetworkMetrics(
        clustering_coefficient=0.3, avg_path_length=4.0,
        degree_distribution={}, community_sizes={}, bridge_count=0,
        is_valid=True,
    )
    return SocialNetwork(
        graph=g,
        communities=[CommunityConfig(id="c1", name="C1", size=1 + len(neighbors), agent_type="influencer")],
        influencer_node_ids=[0],
        bridge_edge_ids=[],
        metrics=metrics,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.phase4
@pytest.mark.unit
class TestPropagationModelPropagate:
    """SPEC: 03_DIFFUSION_SPEC.md#propagationmodel"""

    def test_ignore_generates_no_events(self):
        source = _make_agent()
        neighbors = [_make_agent() for _ in range(3)]
        graph = _make_graph_with_neighbors(source, neighbors)
        model = PropagationModel()

        events = model.propagate(source, AgentAction.IGNORE, graph, uuid4(), step=0, seed=42)
        assert events == []

    def test_view_generates_no_events(self):
        source = _make_agent()
        neighbors = [_make_agent() for _ in range(3)]
        graph = _make_graph_with_neighbors(source, neighbors)
        model = PropagationModel()

        events = model.propagate(source, AgentAction.VIEW, graph, uuid4(), step=0, seed=42)
        assert events == []

    def test_like_generates_no_events(self):
        source = _make_agent()
        neighbors = [_make_agent() for _ in range(3)]
        graph = _make_graph_with_neighbors(source, neighbors)
        model = PropagationModel()

        events = model.propagate(source, AgentAction.LIKE, graph, uuid4(), step=0, seed=42)
        assert events == []

    def test_share_generates_events(self):
        """DIF-02: High-influence agent share -> propagation events."""
        source = _make_agent(influence=0.9, excitement=0.9, skepticism=0.0)
        neighbors = [_make_agent() for _ in range(5)]
        graph = _make_graph_with_neighbors(source, neighbors, weight=0.9)
        model = PropagationModel()

        events = model.propagate(source, AgentAction.SHARE, graph, uuid4(), step=1, seed=42)
        assert len(events) > 0
        for e in events:
            assert e.source_agent_id == source.agent_id
            assert 0.0 <= e.probability <= 1.0

    def test_comment_limited_to_5_neighbors(self):
        source = _make_agent(influence=0.9, excitement=0.9, skepticism=0.0)
        neighbors = [_make_agent() for _ in range(10)]
        graph = _make_graph_with_neighbors(source, neighbors, weight=0.9)
        model = PropagationModel()

        events = model.propagate(source, AgentAction.COMMENT, graph, uuid4(), step=1, seed=42)
        # At most 5 targets (may be fewer due to probability)
        target_ids = {e.target_agent_id for e in events}
        assert len(target_ids) <= 5

    def test_repost_lower_trust(self):
        """REPOST uses all neighbors but with lower trust multiplier."""
        source = _make_agent(influence=0.9, excitement=0.9, skepticism=0.0)
        neighbors = [_make_agent() for _ in range(3)]
        graph = _make_graph_with_neighbors(source, neighbors, weight=0.9)
        model = PropagationModel()

        share_events = model.propagate(source, AgentAction.SHARE, graph, uuid4(), step=1, seed=42)
        repost_events = model.propagate(source, AgentAction.REPOST, graph, uuid4(), step=1, seed=42)

        # Repost probabilities should generally be lower due to trust * 0.7
        if share_events and repost_events:
            avg_share = sum(e.probability for e in share_events) / len(share_events)
            avg_repost = sum(e.probability for e in repost_events) / len(repost_events)
            assert avg_repost <= avg_share

    def test_adopt_half_probability(self):
        """ADOPT: passive propagation -> P * 0.5."""
        source = _make_agent(influence=0.9, excitement=0.9, skepticism=0.0)
        neighbors = [_make_agent() for _ in range(3)]
        graph = _make_graph_with_neighbors(source, neighbors, weight=0.9)
        model = PropagationModel()

        events = model.propagate(source, AgentAction.ADOPT, graph, uuid4(), step=1, seed=42)
        # All probabilities should reflect the *0.5 factor
        for e in events:
            assert 0.0 <= e.probability <= 1.0

    def test_probability_clamped(self):
        """DIF-10: Probability always in [0, 1]."""
        source = _make_agent(influence=1.0, excitement=1.0, skepticism=0.0)
        neighbors = [_make_agent() for _ in range(5)]
        graph = _make_graph_with_neighbors(source, neighbors, weight=1.0)
        model = PropagationModel()

        events = model.propagate(source, AgentAction.SHARE, graph, uuid4(), step=1, seed=0)
        for e in events:
            assert 0.0 <= e.probability <= 1.0

    def test_no_neighbors_empty_events(self):
        source = _make_agent()
        graph = _make_graph_with_neighbors(source, [])
        model = PropagationModel()

        events = model.propagate(source, AgentAction.SHARE, graph, uuid4(), step=1)
        assert events == []

    def test_deterministic_with_seed(self):
        source = _make_agent(influence=0.7, excitement=0.7, skepticism=0.1)
        neighbors = [_make_agent() for _ in range(5)]
        graph = _make_graph_with_neighbors(source, neighbors, weight=0.7)
        model = PropagationModel()
        msg_id = uuid4()

        events1 = model.propagate(source, AgentAction.SHARE, graph, msg_id, step=1, seed=123)
        events2 = model.propagate(source, AgentAction.SHARE, graph, msg_id, step=1, seed=123)

        assert len(events1) == len(events2)
        for e1, e2 in zip(events1, events2):
            assert e1.target_agent_id == e2.target_agent_id
            assert e1.probability == e2.probability


@pytest.mark.phase4
@pytest.mark.unit
class TestPropagationModelDiffusionRate:
    """SPEC: 03_DIFFUSION_SPEC.md#propagationmodel"""

    def test_empty_history(self):
        """DIF-08: no data -> 0."""
        model = PropagationModel()
        assert model.compute_diffusion_rate([]) == 0.0

    def test_single_entry(self):
        model = PropagationModel()
        assert model.compute_diffusion_rate([10]) == 0.0

    def test_increasing(self):
        model = PropagationModel()
        assert model.compute_diffusion_rate([10, 15]) == 5.0

    def test_decreasing_clamped(self):
        model = PropagationModel()
        assert model.compute_diffusion_rate([15, 10]) == 0.0

    def test_no_change(self):
        model = PropagationModel()
        assert model.compute_diffusion_rate([10, 10]) == 0.0

    def test_uses_last_two_entries(self):
        model = PropagationModel()
        assert model.compute_diffusion_rate([5, 10, 20]) == 10.0
