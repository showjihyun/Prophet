"""Tests for ExposureModel.
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
from app.engine.diffusion.schema import CampaignEvent, ExposureResult, RecSysConfig
from app.engine.diffusion.exposure_model import ExposureModel


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


def _make_agent(community_id=None, agent_id=None, **overrides) -> AgentState:
    aid = agent_id or uuid4()
    cid = community_id or uuid4()
    defaults = dict(
        agent_id=aid,
        simulation_id=uuid4(),
        agent_type=AgentType.CONSUMER,
        step=0,
        personality=_make_personality(),
        emotion=_make_emotion(),
        belief=0.0,
        action=AgentAction.IGNORE,
        exposure_count=0,
        adopted=False,
        community_id=cid,
        influence_score=0.5,
        llm_tier_used=None,
    )
    defaults.update(overrides)
    return AgentState(**defaults)


def _make_graph(agents: list[AgentState], edges: list[tuple[int, int]] | None = None) -> SocialNetwork:
    g = nx.Graph()
    for i, a in enumerate(agents):
        g.add_node(i, agent_id=a.agent_id, community_id=str(a.community_id))
    if edges:
        for u, v in edges:
            g.add_edge(u, v, weight=0.5)
    metrics = NetworkMetrics(
        clustering_coefficient=0.3, avg_path_length=4.0,
        degree_distribution={}, community_sizes={}, bridge_count=0,
        is_valid=True,
    )
    return SocialNetwork(
        graph=g,
        communities=[CommunityConfig(id="c1", name="C1", size=len(agents), agent_type="consumer")],
        influencer_node_ids=[],
        bridge_edge_ids=[],
        metrics=metrics,
    )


def _make_campaign(community_id=None, start=0, end=10) -> CampaignEvent:
    return CampaignEvent(
        campaign_id=uuid4(),
        name="Test Campaign",
        message="Buy this!",
        channels=["social"],
        novelty=0.7,
        controversy=0.2,
        utility=0.6,
        budget=0.5,
        target_communities=[community_id or uuid4()],
        start_step=start,
        end_step=end,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.phase4
@pytest.mark.unit
class TestExposureModelInit:
    """SPEC: 03_DIFFUSION_SPEC.md#exposuremodel-recsys-inspired-oasis-차용"""

    def test_default_config(self):
        model = ExposureModel()
        assert model._config.feed_capacity == 20

    def test_custom_config(self):
        cfg = RecSysConfig(feed_capacity=10)
        model = ExposureModel(recsys_config=cfg)
        assert model._config.feed_capacity == 10

    def test_invalid_weight_sum_raises(self):
        with pytest.raises(ValueError, match="weight sum"):
            RecSysConfig(w_recency=0.5, w_social_affinity=0.5)


@pytest.mark.phase4
@pytest.mark.unit
class TestExposureModelComputeExposure:
    """SPEC: 03_DIFFUSION_SPEC.md#exposuremodel-recsys-inspired-oasis-차용"""

    def test_empty_agents_raises(self):
        model = ExposureModel()
        graph = _make_graph([])
        with pytest.raises(ValueError, match="agents list must not be empty"):
            model.compute_exposure([], graph, [], step=0)

    def test_no_campaign_all_zero(self):
        """DIF-01: No active campaign → all exposure scores = 0."""
        agents = [_make_agent() for _ in range(3)]
        graph = _make_graph(agents)
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [], step=0)

        assert len(result) == 3
        for agent in agents:
            r = result[agent.agent_id]
            assert r.exposure_score == 0.0
            assert r.exposed_events == []
            assert r.social_feed == []
            assert r.suppressed_count == 0
            assert r.is_directly_exposed is False

    def test_with_campaign_returns_scores(self):
        cid = uuid4()
        agents = [_make_agent(community_id=cid) for _ in range(3)]
        graph = _make_graph(agents, edges=[(0, 1), (1, 2)])
        campaign = _make_campaign(community_id=cid)
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [campaign], step=1)

        assert len(result) == 3
        for agent in agents:
            r = result[agent.agent_id]
            assert isinstance(r, ExposureResult)
            assert r.agent_id == agent.agent_id
            assert r.is_directly_exposed is True

    def test_exposure_score_range(self):
        cid = uuid4()
        agents = [_make_agent(community_id=cid) for _ in range(5)]
        graph = _make_graph(agents, edges=[(0, 1), (1, 2), (2, 3), (3, 4)])
        campaign = _make_campaign(community_id=cid)
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [campaign], step=1)

        for r in result.values():
            assert 0.0 <= r.exposure_score <= 1.0

    def test_feed_diversity_score_range(self):
        cid = uuid4()
        agents = [_make_agent(community_id=cid) for _ in range(3)]
        graph = _make_graph(agents, edges=[(0, 1), (1, 2)])
        campaign = _make_campaign(community_id=cid)
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [campaign], step=1)

        for r in result.values():
            assert 0.0 <= r.feed_diversity_score <= 1.0

    def test_suppressed_count_with_small_capacity(self):
        cid = uuid4()
        agents = [_make_agent(community_id=cid) for _ in range(5)]
        # Many edges = many candidates
        edges = [(i, j) for i in range(5) for j in range(i + 1, 5)]
        graph = _make_graph(agents, edges=edges)
        campaign = _make_campaign(community_id=cid)
        cfg = RecSysConfig(feed_capacity=1)
        model = ExposureModel(recsys_config=cfg)

        result = model.compute_exposure(agents, graph, [campaign], step=1)

        # At least some agents should have suppressed items
        any_suppressed = any(r.suppressed_count > 0 for r in result.values())
        assert any_suppressed

    def test_config_override_per_call(self):
        agents = [_make_agent() for _ in range(2)]
        graph = _make_graph(agents, edges=[(0, 1)])
        campaign = _make_campaign()
        model = ExposureModel()
        override = RecSysConfig(feed_capacity=1)

        result = model.compute_exposure(
            agents, graph, [campaign], step=1, recsys_config=override
        )
        assert len(result) == 2
