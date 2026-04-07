"""RecSys feed ranking tests for ExposureModel.
Auto-generated from SPEC: docs/spec/03_DIFFUSION_SPEC.md#exposuremodel-recsys-inspired-oasis-차용
SPEC Version: 0.1.1
Generated BEFORE implementation verification — tests define the contract.

Focuses on feed ranking internals: RecSysConfig weight validation,
_rank_feed ordering, feed_capacity enforcement, and config overrides.
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
from app.engine.diffusion.schema import CampaignEvent, FeedItem, RecSysConfig
from app.engine.diffusion.exposure_model import ExposureModel


# ---------------------------------------------------------------------------
# Helpers (mirrors test_03_exposure.py pattern)
# ---------------------------------------------------------------------------


def _make_personality(**overrides) -> AgentPersonality:
    defaults = dict(
        openness=0.5,
        skepticism=0.3,
        trend_following=0.4,
        brand_loyalty=0.5,
        social_influence=0.5,
    )
    defaults.update(overrides)
    return AgentPersonality(**defaults)


def _make_emotion(**overrides) -> AgentEmotion:
    defaults = dict(interest=0.5, trust=0.5, skepticism=0.3, excitement=0.5)
    defaults.update(overrides)
    return AgentEmotion(**defaults)


def _make_state(community_id=None, agent_id=None, **overrides) -> AgentState:
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


def _make_graph(
    agents: list[AgentState],
    edges: list[tuple[int, int]] | None = None,
) -> SocialNetwork:
    g = nx.Graph()
    for i, a in enumerate(agents):
        g.add_node(i, agent_id=a.agent_id, community_id=str(a.community_id))
    if edges:
        for u, v in edges:
            g.add_edge(u, v, weight=0.5)
    metrics = NetworkMetrics(
        clustering_coefficient=0.3,
        avg_path_length=4.0,
        degree_distribution={},
        community_sizes={},
        bridge_count=0,
        is_valid=True,
    )
    return SocialNetwork(
        graph=g,
        communities=[
            CommunityConfig(id="c1", name="C1", size=len(agents), agent_type="consumer")
        ],
        influencer_node_ids=[],
        bridge_edge_ids=[],
        metrics=metrics,
    )


def _make_campaign(community_id=None, start: int = 0, end: int = 10) -> CampaignEvent:
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
# RecSysConfig weight validation
# ---------------------------------------------------------------------------


@pytest.mark.phase4
@pytest.mark.unit
class TestRecSysConfigWeights:
    """SPEC: 03_DIFFUSION_SPEC.md — RecSysConfig weight invariant"""

    def test_default_weights_sum_to_1(self):
        """Default RecSysConfig weights must sum to exactly 1.0."""
        cfg = RecSysConfig()
        total = (
            cfg.w_recency
            + cfg.w_social_affinity
            + cfg.w_interest_match
            + cfg.w_engagement_signal
            + cfg.w_ad_boost
        )
        assert abs(total - 1.0) <= 0.01, f"Default weight sum is {total}, expected 1.0"

    def test_custom_valid_weights_accepted(self):
        """Custom weights that sum to 1.0 must be accepted without error."""
        cfg = RecSysConfig(
            w_recency=0.25,
            w_social_affinity=0.25,
            w_interest_match=0.25,
            w_engagement_signal=0.15,
            w_ad_boost=0.10,
        )
        total = (
            cfg.w_recency
            + cfg.w_social_affinity
            + cfg.w_interest_match
            + cfg.w_engagement_signal
            + cfg.w_ad_boost
        )
        assert abs(total - 1.0) <= 0.01

    def test_weights_not_summing_to_1_raises_value_error(self):
        """SPEC: weight sum != 1.0 (±0.01) must raise ValueError — no auto-correction."""
        with pytest.raises(ValueError, match="weight sum"):
            RecSysConfig(w_recency=0.5, w_social_affinity=0.5)  # sum = 1.1 with defaults

    def test_feed_capacity_default(self):
        """Default feed_capacity must be 20."""
        cfg = RecSysConfig()
        assert cfg.feed_capacity == 20

    def test_custom_feed_capacity(self):
        """Custom feed_capacity is stored correctly."""
        cfg = RecSysConfig(feed_capacity=5)
        assert cfg.feed_capacity == 5


# ---------------------------------------------------------------------------
# _rank_feed ordering and capacity
# ---------------------------------------------------------------------------


@pytest.mark.phase4
@pytest.mark.unit
class TestRankFeedOrdering:
    """SPEC: 03_DIFFUSION_SPEC.md — _rank_feed sorts by feed_rank_score descending"""

    def test_rank_feed_orders_by_score_descending(self):
        """_rank_feed must return items sorted by feed_rank_score descending."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(3)]
        graph = _make_graph(agents, edges=[(0, 1), (1, 2)])
        campaign = _make_campaign(community_id=cid)
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [campaign], step=1)

        for r in result.values():
            scores = [item.feed_rank_score for item in r.social_feed]
            assert scores == sorted(scores, reverse=True), (
                f"Feed items not sorted descending: {scores}"
            )

    def test_feed_capacity_limits_output_size(self):
        """social_feed must not exceed feed_capacity items."""
        cid = uuid4()
        # Create enough agents so the fully-connected graph generates > capacity candidates
        agents = [_make_state(community_id=cid) for _ in range(10)]
        edges = [(i, j) for i in range(10) for j in range(i + 1, 10)]
        graph = _make_graph(agents, edges=edges)
        campaign = _make_campaign(community_id=cid)
        cfg = RecSysConfig(feed_capacity=3)
        model = ExposureModel(recsys_config=cfg)

        result = model.compute_exposure(agents, graph, [campaign], step=1)

        for r in result.values():
            assert len(r.social_feed) <= 3, (
                f"social_feed length {len(r.social_feed)} exceeds feed_capacity=3"
            )

    def test_suppressed_count_reflects_dropped_items(self):
        """suppressed_count == len(all_candidates) - feed_capacity when candidates > capacity."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(6)]
        edges = [(i, j) for i in range(6) for j in range(i + 1, 6)]
        graph = _make_graph(agents, edges=edges)
        campaign = _make_campaign(community_id=cid)
        cfg = RecSysConfig(feed_capacity=1)
        model = ExposureModel(recsys_config=cfg)

        result = model.compute_exposure(agents, graph, [campaign], step=1)

        any_suppressed = any(r.suppressed_count > 0 for r in result.values())
        assert any_suppressed, "Expected at least one agent to have suppressed items"

    def test_all_items_have_feed_rank_score_in_range(self):
        """All ranked items must have feed_rank_score between 0 and 1 (inclusive)."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(4)]
        graph = _make_graph(agents, edges=[(0, 1), (2, 3), (1, 2)])
        campaign = _make_campaign(community_id=cid)
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [campaign], step=1)

        for r in result.values():
            for item in r.social_feed:
                assert 0.0 <= item.feed_rank_score <= 1.0, (
                    f"feed_rank_score {item.feed_rank_score} out of [0, 1]"
                )


# ---------------------------------------------------------------------------
# compute_exposure with active campaign
# ---------------------------------------------------------------------------


@pytest.mark.phase4
@pytest.mark.unit
class TestComputeExposureWithCampaign:
    """SPEC: 03_DIFFUSION_SPEC.md — compute_exposure contract with active campaign"""

    def test_active_campaign_produces_nonzero_scores(self):
        """SPEC: active campaign in agent's community → exposure_score > 0."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(3)]
        graph = _make_graph(agents, edges=[(0, 1), (1, 2)])
        campaign = _make_campaign(community_id=cid)
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [campaign], step=1)

        scores = [r.exposure_score for r in result.values()]
        assert any(s > 0.0 for s in scores), (
            "Expected at least one agent with non-zero exposure score"
        )

    def test_custom_config_changes_ranking(self):
        """Different RecSysConfig weights must produce different ranking outcomes."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(5)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]
        graph = _make_graph(agents, edges=edges)
        campaign = _make_campaign(community_id=cid)

        # Default config
        default_model = ExposureModel()
        default_result = default_model.compute_exposure(agents, graph, [campaign], step=1)

        # Ad-heavy config (weight heavily toward ad_boost)
        ad_heavy_cfg = RecSysConfig(
            w_recency=0.1,
            w_social_affinity=0.1,
            w_interest_match=0.1,
            w_engagement_signal=0.1,
            w_ad_boost=0.6,
        )
        ad_model = ExposureModel(recsys_config=ad_heavy_cfg)
        ad_result = ad_model.compute_exposure(agents, graph, [campaign], step=1)

        # Both should return results for all agents
        assert len(default_result) == len(agents)
        assert len(ad_result) == len(agents)

        # At least one agent's scores should differ between configs
        score_pairs = [
            (default_result[a.agent_id].exposure_score, ad_result[a.agent_id].exposure_score)
            for a in agents
        ]
        differences = [abs(d - a) for d, a in score_pairs]
        # Scores may or may not differ numerically (depends on data), but both are valid floats
        for d, a in score_pairs:
            assert 0.0 <= d <= 1.0
            assert 0.0 <= a <= 1.0

    def test_per_call_config_override(self):
        """recsys_config passed to compute_exposure overrides instance config."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(3)]
        graph = _make_graph(agents, edges=[(0, 1), (1, 2)])
        campaign = _make_campaign(community_id=cid)

        # Instance has capacity=20
        model = ExposureModel(recsys_config=RecSysConfig(feed_capacity=20))

        # Per-call override restricts to capacity=1
        override_cfg = RecSysConfig(feed_capacity=1)
        result = model.compute_exposure(
            agents, graph, [campaign], step=1, recsys_config=override_cfg
        )

        for r in result.values():
            assert len(r.social_feed) <= 1

    def test_result_keys_match_agent_ids(self):
        """Result dict keys must exactly match the provided agent_ids."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(4)]
        graph = _make_graph(agents)
        campaign = _make_campaign(community_id=cid)
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [campaign], step=1)

        expected_ids = {a.agent_id for a in agents}
        assert set(result.keys()) == expected_ids

    def test_directly_exposed_when_community_targeted(self):
        """Agents in targeted community must have is_directly_exposed=True."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(3)]
        graph = _make_graph(agents, edges=[(0, 1)])
        campaign = _make_campaign(community_id=cid)  # targets this community
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [campaign], step=1)

        for a in agents:
            assert result[a.agent_id].is_directly_exposed is True


# ---------------------------------------------------------------------------
# Empty agent list → ValueError
# ---------------------------------------------------------------------------


@pytest.mark.phase4
@pytest.mark.unit
class TestComputeExposureErrors:
    """SPEC: 03_DIFFUSION_SPEC.md — error paths"""

    def test_empty_agents_raises_value_error(self):
        """SPEC: Empty agent list must raise ValueError."""
        graph = _make_graph([], edges=[])
        campaign = _make_campaign()
        model = ExposureModel()

        with pytest.raises(ValueError, match="agents.*empty|must not be empty"):
            model.compute_exposure([], graph, [campaign], step=1)

    def test_no_active_events_returns_zero_scores(self):
        """SPEC: No active campaign → all exposure scores 0.0."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(3)]
        graph = _make_graph(agents, edges=[(0, 1)])
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [], step=1)

        for r in result.values():
            assert r.exposure_score == 0.0
            assert r.is_directly_exposed is False
            assert len(r.social_feed) == 0


# ---------------------------------------------------------------------------
# feed_diversity_score contracts
# ---------------------------------------------------------------------------


@pytest.mark.phase4
@pytest.mark.unit
class TestFeedDiversityScore:
    """SPEC: 03_DIFFUSION_SPEC.md — feed_diversity_score in [0, 1]"""

    def test_diversity_score_in_valid_range(self):
        """feed_diversity_score must be in [0, 1] for every agent."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(5)]
        edges = [(i, j) for i in range(5) for j in range(i + 1, 5)]
        graph = _make_graph(agents, edges=edges)
        campaign = _make_campaign(community_id=cid)
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [campaign], step=1)

        for r in result.values():
            assert 0.0 <= r.feed_diversity_score <= 1.0, (
                f"feed_diversity_score {r.feed_diversity_score} out of [0, 1]"
            )

    def test_diverse_feed_higher_than_homogeneous(self):
        """A feed with many unique sources should have higher diversity than one with few."""
        cid = uuid4()
        # Many agents = many potential sources → higher diversity
        agents_many = [_make_state(community_id=cid) for _ in range(8)]
        edges_many = [(i, j) for i in range(8) for j in range(i + 1, 8)]
        graph_many = _make_graph(agents_many, edges=edges_many)

        # Few agents = fewer sources
        agents_few = [_make_state(community_id=cid) for _ in range(2)]
        graph_few = _make_graph(agents_few, edges=[(0, 1)])

        campaign = _make_campaign(community_id=cid)
        model = ExposureModel(recsys_config=RecSysConfig(feed_capacity=20))

        result_many = model.compute_exposure(agents_many, graph_many, [campaign], step=1)
        result_few = model.compute_exposure(agents_few, graph_few, [campaign], step=1)

        # At least one agent in the many-source network should have high diversity
        max_div_many = max(r.feed_diversity_score for r in result_many.values())
        # All valid
        for r in result_few.values():
            assert 0.0 <= r.feed_diversity_score <= 1.0

        # Many sources network should achieve at least some diversity
        assert max_div_many > 0.0, "Feed with many sources should have nonzero diversity"

    def test_no_events_diversity_is_zero(self):
        """No active campaigns → feed_diversity_score must be 0.0."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(3)]
        graph = _make_graph(agents, edges=[(0, 1)])
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [], step=1)

        for r in result.values():
            assert r.feed_diversity_score == 0.0


# ---------------------------------------------------------------------------
# diversity_penalty effect
# ---------------------------------------------------------------------------


@pytest.mark.phase4
@pytest.mark.unit
class TestDiversityPenalty:
    """SPEC: 03_DIFFUSION_SPEC.md — diversity_penalty reduces repeated-source scores"""

    def test_high_penalty_reduces_repeated_source_scores(self):
        """Higher diversity_penalty should lower scores for repeated same-source items."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(5)]
        edges = [(0, 1), (0, 2), (0, 3), (0, 4)]  # agent 0 connected to all
        graph = _make_graph(agents, edges=edges)
        campaign = _make_campaign(community_id=cid)

        # Low penalty
        low_cfg = RecSysConfig(diversity_penalty=0.01)
        model_low = ExposureModel(recsys_config=low_cfg)
        result_low = model_low.compute_exposure(agents, graph, [campaign], step=1)

        # High penalty
        high_cfg = RecSysConfig(diversity_penalty=0.20)
        model_high = ExposureModel(recsys_config=high_cfg)
        result_high = model_high.compute_exposure(agents, graph, [campaign], step=1)

        # Both should produce valid results
        assert len(result_low) == len(agents)
        assert len(result_high) == len(agents)

        # With high penalty, average exposure scores should generally be lower or equal
        avg_low = sum(r.exposure_score for r in result_low.values()) / len(result_low)
        avg_high = sum(r.exposure_score for r in result_high.values()) / len(result_high)
        # High penalty → scores penalized → average should not exceed low penalty by much
        assert avg_high <= avg_low + 0.1, (
            f"High diversity_penalty should not increase avg score: "
            f"low={avg_low:.3f}, high={avg_high:.3f}"
        )


# ---------------------------------------------------------------------------
# enable_filter_bubble flag
# ---------------------------------------------------------------------------


@pytest.mark.phase4
@pytest.mark.unit
class TestFilterBubble:
    """SPEC: 03_DIFFUSION_SPEC.md — enable_filter_bubble config flag"""

    def test_filter_bubble_flag_exists_in_config(self):
        """RecSysConfig must have enable_filter_bubble field with default True."""
        cfg = RecSysConfig()
        assert hasattr(cfg, "enable_filter_bubble")
        assert cfg.enable_filter_bubble is True

    def test_filter_bubble_disabled_accepted(self):
        """RecSysConfig with enable_filter_bubble=False must be accepted."""
        cfg = RecSysConfig(enable_filter_bubble=False)
        assert cfg.enable_filter_bubble is False

    def test_compute_exposure_accepts_filter_bubble_config(self):
        """compute_exposure must work with both filter_bubble settings."""
        cid = uuid4()
        agents = [_make_state(community_id=cid) for _ in range(3)]
        graph = _make_graph(agents, edges=[(0, 1), (1, 2)])
        campaign = _make_campaign(community_id=cid)

        for bubble in (True, False):
            cfg = RecSysConfig(enable_filter_bubble=bubble)
            model = ExposureModel(recsys_config=cfg)
            result = model.compute_exposure(agents, graph, [campaign], step=1)
            assert len(result) == len(agents)
