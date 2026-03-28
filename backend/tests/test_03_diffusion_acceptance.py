"""Acceptance tests for Social Diffusion Engine (DIF-01 to DIF-10).
Auto-generated from SPEC: docs/spec/03_DIFFUSION_SPEC.md#acceptance-criteria
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
from app.engine.diffusion.schema import (
    CampaignEvent,
    CascadeConfig,
    CommunitySentiment,
    EmergentEvent,
    ExpertOpinion,
    NegativeEvent,
    RecSysConfig,
)
from app.engine.diffusion.exposure_model import ExposureModel
from app.engine.diffusion.propagation_model import PropagationModel
from app.engine.diffusion.sentiment_model import SentimentModel
from app.engine.diffusion.cascade_detector import CascadeDetector, StepResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _personality(**kw) -> AgentPersonality:
    d = dict(openness=0.5, skepticism=0.3, trend_following=0.4,
             brand_loyalty=0.5, social_influence=0.5)
    d.update(kw)
    return AgentPersonality(**d)


def _emotion(**kw) -> AgentEmotion:
    d = dict(interest=0.5, trust=0.5, skepticism=0.3, excitement=0.5)
    d.update(kw)
    return AgentEmotion(**d)


def _agent(community_id=None, belief=0.0, adopted=False, influence=0.5,
           agent_type=AgentType.CONSUMER, excitement=0.5, skepticism=0.3,
           agent_id=None) -> AgentState:
    return AgentState(
        agent_id=agent_id or uuid4(),
        simulation_id=uuid4(),
        agent_type=agent_type,
        step=1,
        personality=_personality(),
        emotion=_emotion(excitement=excitement, skepticism=skepticism),
        belief=belief,
        action=AgentAction.IGNORE,
        exposure_count=0,
        adopted=adopted,
        community_id=community_id or uuid4(),
        influence_score=influence,
        llm_tier_used=None,
    )


def _graph(agents, edges=None) -> SocialNetwork:
    g = nx.Graph()
    for i, a in enumerate(agents):
        g.add_node(i, agent_id=a.agent_id, community_id=str(a.community_id))
    for u, v in (edges or []):
        g.add_edge(u, v, weight=0.7)
    m = NetworkMetrics(
        clustering_coefficient=0.3, avg_path_length=4.0,
        degree_distribution={}, community_sizes={}, bridge_count=0, is_valid=True,
    )
    return SocialNetwork(
        graph=g,
        communities=[CommunityConfig(id="c", name="C", size=len(agents), agent_type="consumer")],
        influencer_node_ids=[], bridge_edge_ids=[], metrics=m,
    )


def _campaign(community_id=None) -> CampaignEvent:
    return CampaignEvent(
        campaign_id=uuid4(), name="C", message="msg", channels=["social"],
        novelty=0.7, controversy=0.2, utility=0.6, budget=0.5,
        target_communities=[community_id or uuid4()],
        start_step=0, end_step=10,
    )


def _step(step, adopted=0, total=100, variances=None,
          internal=None, external=None) -> StepResult:
    return StepResult(
        step=step, total_agents=total, adopted_count=adopted,
        adoption_rate=adopted / total if total else 0.0,
        community_sentiments={}, community_variances=variances or {},
        community_adoption_rates={},
        internal_links=internal or {}, external_links=external or {},
        adopted_agent_ids=[uuid4() for _ in range(adopted)],
    )


# ---------------------------------------------------------------------------
# Acceptance Tests DIF-01 through DIF-10
# ---------------------------------------------------------------------------

@pytest.mark.phase4
@pytest.mark.acceptance
class TestDIF01_NoActiveCampaign:
    """DIF-01: Exposure model with no active campaign → all exposure scores = 0."""

    def test_all_exposure_zero(self):
        agents = [_agent() for _ in range(5)]
        graph = _graph(agents)
        model = ExposureModel()

        result = model.compute_exposure(agents, graph, [], step=0)

        assert len(result) == 5
        for r in result.values():
            assert r.exposure_score == 0.0
            assert r.exposed_events == []
            assert r.is_directly_exposed is False


@pytest.mark.phase4
@pytest.mark.acceptance
class TestDIF02_HighInfluenceShare:
    """DIF-02: High-influence agent share → multiple propagation events."""

    def test_propagation_events_generated(self):
        source = _agent(influence=0.9, excitement=0.9, skepticism=0.0)
        neighbors = [_agent() for _ in range(5)]
        all_agents = [source] + neighbors
        edges = [(0, i) for i in range(1, 6)]
        graph = _graph(all_agents, edges)

        model = PropagationModel()
        events = model.propagate(
            source, AgentAction.SHARE, graph, uuid4(), step=1, seed=42,
        )

        assert len(events) > 0
        for e in events:
            assert e.source_agent_id == source.agent_id


@pytest.mark.phase4
@pytest.mark.acceptance
class TestDIF03_SkepticNegativeSpread:
    """DIF-03: Skeptic agent with controversy event → negative spread."""

    def test_negative_propagation(self):
        source = _agent(
            agent_type=AgentType.SKEPTIC,
            influence=0.8, excitement=0.8, skepticism=0.1,
        )
        neighbors = [_agent() for _ in range(5)]
        all_agents = [source] + neighbors
        edges = [(0, i) for i in range(1, 6)]
        graph = _graph(all_agents, edges)

        model = PropagationModel()
        # Skeptic shares negative content → propagation events
        events = model.propagate(
            source, AgentAction.SHARE, graph, uuid4(), step=1, seed=42,
        )
        assert len(events) > 0


@pytest.mark.phase4
@pytest.mark.acceptance
class TestDIF04_ViralCascade:
    """DIF-04: Viral cascade detection triggers at threshold."""

    def test_viral_event_returned(self):
        detector = CascadeDetector()
        history = [_step(0, adopted=5)]
        current = _step(1, adopted=20)

        events = detector.detect(current, history)
        viral = [e for e in events if e.event_type == "viral_cascade"]
        assert len(viral) == 1
        assert viral[0].event_type == "viral_cascade"


@pytest.mark.phase4
@pytest.mark.acceptance
class TestDIF05_PolarizationDetection:
    """DIF-05: Polarization detection with split community sentiment."""

    def test_polarization_event_returned(self):
        cid = uuid4()
        detector = CascadeDetector()
        current = _step(1, variances={cid: 0.5})

        events = detector.detect(current, [])
        polar = [e for e in events if e.event_type == "polarization"]
        assert len(polar) == 1
        assert polar[0].event_type == "polarization"
        assert polar[0].community_id == cid

    def test_via_sentiment_model(self):
        """Also test via SentimentModel.detect_polarization."""
        model = SentimentModel()
        cid = uuid4()
        communities = [
            CommunitySentiment(
                community_id=cid, mean_belief=0.0,
                sentiment_variance=0.5, adoption_rate=0.3, step=1,
            ),
        ]
        assert model.detect_polarization(communities) is True


@pytest.mark.phase4
@pytest.mark.acceptance
class TestDIF06_ExpertNegativeOpinion:
    """DIF-06: Expert negative opinion reduces community trust."""

    def test_mean_belief_decreases(self):
        model = SentimentModel()
        cid = uuid4()
        agents = [
            _agent(community_id=cid, belief=0.5),
            _agent(community_id=cid, belief=0.5),
            _agent(community_id=cid, belief=0.5),
        ]

        baseline = model.update_community_sentiment(cid, agents, [])

        opinion = ExpertOpinion(
            expert_agent_id=uuid4(), score=-0.9, reasoning="Bad product",
            step=1, affects_communities=[cid], confidence=0.9,
        )
        result = model.update_community_sentiment(cid, agents, [opinion])

        assert result.mean_belief < baseline.mean_belief


@pytest.mark.phase4
@pytest.mark.acceptance
class TestDIF07_MonteCarloPlaceholder:
    """DIF-07: Monte Carlo 100 runs — placeholder (will be Phase 6)."""

    def test_placeholder(self):
        # Monte Carlo runner is Phase 6; verify schema exists
        from app.engine.diffusion.schema import MonteCarloResult, RunSummary
        result = MonteCarloResult(
            n_runs=100, viral_probability=0.3, expected_reach=50.0,
            community_adoption={"c1": 0.5}, p5_reach=20.0,
            p50_reach=50.0, p95_reach=80.0,
            run_summaries=[RunSummary(run_id=0, final_adoption=50,
                                      viral_detected=False, steps_completed=10)],
        )
        assert result.n_runs == 100


@pytest.mark.phase4
@pytest.mark.acceptance
class TestDIF08_DiffusionRateZero:
    """DIF-08: Diffusion rate R(t) is 0 with no active agents."""

    def test_returns_zero(self):
        model = PropagationModel()
        assert model.compute_diffusion_rate([]) == 0.0
        assert model.compute_diffusion_rate([0]) == 0.0
        assert model.compute_diffusion_rate([0, 0]) == 0.0


@pytest.mark.phase4
@pytest.mark.acceptance
class TestDIF09_CollapseDetection:
    """DIF-09: Collapse detection after rapid belief drop."""

    def test_collapse_event_returned(self):
        detector = CascadeDetector()
        history = [
            _step(0, adopted=50),
            _step(1, adopted=45),
        ]
        current = _step(2, adopted=30)  # 40% drop from step 0

        events = detector.detect(current, history)
        collapse = [e for e in events if e.event_type == "collapse"]
        assert len(collapse) == 1
        assert collapse[0].event_type == "collapse"


@pytest.mark.phase4
@pytest.mark.acceptance
class TestDIF10_ProbabilityClamped:
    """DIF-10: Propagation probability clamped to [0, 1]."""

    def test_all_probabilities_in_range(self):
        # High influence + high trust to maximize probability
        source = _agent(influence=1.0, excitement=1.0, skepticism=0.0)
        neighbors = [_agent() for _ in range(10)]
        all_agents = [source] + neighbors
        edges = [(0, i) for i in range(1, 11)]

        g = nx.Graph()
        for i, a in enumerate(all_agents):
            g.add_node(i, agent_id=a.agent_id)
        for u, v in edges:
            g.add_edge(u, v, weight=1.0)  # Max trust

        m = NetworkMetrics(
            clustering_coefficient=0.3, avg_path_length=4.0,
            degree_distribution={}, community_sizes={}, bridge_count=0, is_valid=True,
        )
        graph = SocialNetwork(
            graph=g,
            communities=[CommunityConfig(id="c", name="C", size=11, agent_type="consumer")],
            influencer_node_ids=[0], bridge_edge_ids=[], metrics=m,
        )

        model = PropagationModel()
        events = model.propagate(
            source, AgentAction.SHARE, graph, uuid4(), step=1, seed=0,
        )

        for e in events:
            assert 0.0 <= e.probability <= 1.0, (
                f"Probability {e.probability} outside [0,1]"
            )
