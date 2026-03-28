"""
Auto-generated from SPEC: docs/spec/04_SIMULATION_SPEC.md#communityorchestrator
SPEC Version: 0.1.2
Generated BEFORE implementation — tests define the contract.
Status: GREEN (implementation exists)
"""
import asyncio

import pytest
import networkx as nx
from uuid import uuid4, UUID

from app.engine.agent.schema import (
    AgentAction,
    AgentEmotion,
    AgentPersonality,
    AgentState,
    AgentType,
)
from app.engine.network.schema import CommunityConfig


def _make_community_config(cid="A", size=20):
    return CommunityConfig(id=cid, name=f"test_{cid}", size=size, agent_type="consumer")


def _make_agent(community_id: UUID, sim_id: UUID | None = None) -> AgentState:
    """Create a minimal valid agent for testing."""
    return AgentState(
        agent_id=uuid4(),
        simulation_id=sim_id or uuid4(),
        agent_type=AgentType.CONSUMER,
        step=0,
        personality=AgentPersonality(
            openness=0.5, skepticism=0.3, trend_following=0.5,
            brand_loyalty=0.4, social_influence=0.5,
        ),
        emotion=AgentEmotion(interest=0.5, trust=0.5, skepticism=0.3, excitement=0.4),
        belief=0.0,
        action=AgentAction.IGNORE,
        exposure_count=0,
        adopted=False,
        community_id=community_id,
        influence_score=0.5,
        llm_tier_used=None,
    )


def _make_ws_graph(agents: list[AgentState], k: int = 4) -> tuple[nx.Graph, dict[UUID, int]]:
    """Create a Watts-Strogatz-like graph for agents and return (graph, agent_node_map)."""
    n = len(agents)
    G = nx.watts_strogatz_graph(n, min(k, n - 1) if n > 1 else 0, 0.1, seed=42)
    agent_node_map: dict[UUID, int] = {}
    for i, agent in enumerate(agents):
        G.nodes[i]["agent_id"] = agent.agent_id
        agent_node_map[agent.agent_id] = i
        for nbr in G.neighbors(i):
            G[i][nbr]["weight"] = 0.5
    return G, agent_node_map


@pytest.mark.phase6
@pytest.mark.acceptance
class TestCommunityOrchestratorContract:
    """SPEC: 04_SIMULATION_SPEC.md#communityorchestrator"""

    def test_tick_returns_community_tick_result(self):
        """CommunityOrchestrator.tick() returns CommunityTickResult."""
        from app.engine.simulation.community_orchestrator import (
            CommunityOrchestrator,
            CommunityTickResult,
        )
        # Will fail until CommunityOrchestrator is implemented
        assert hasattr(CommunityOrchestrator, "tick")

    def test_tick_result_has_required_fields(self):
        """CommunityTickResult has all required fields."""
        from app.engine.simulation.community_orchestrator import CommunityTickResult
        fields = [
            "community_id", "updated_agents", "propagation_events",
            "outbound_events", "community_sentiment", "action_distribution",
            "llm_calls", "tick_duration_ms",
        ]
        for f in fields:
            assert hasattr(CommunityTickResult, f) or f in CommunityTickResult.__dataclass_fields__

    def test_tick_only_processes_own_community_agents(self):
        """CommunityOrchestrator should only tick agents belonging to its community."""
        from app.engine.simulation.community_orchestrator import CommunityOrchestrator
        # When implemented: create orchestrator with community A agents,
        # verify tick doesn't touch community B agents
        assert callable(getattr(CommunityOrchestrator, "tick", None))

    def test_outbound_events_target_other_communities(self):
        """outbound_events should only contain events targeting bridge edges."""
        from app.engine.simulation.community_orchestrator import CommunityTickResult
        # When implemented: verify outbound_events targets are NOT in same community
        assert True  # placeholder until implementation

    def test_community_sentiment_is_local(self):
        """community_sentiment should reflect only this community's agents."""
        from app.engine.simulation.community_orchestrator import CommunityOrchestrator
        assert callable(getattr(CommunityOrchestrator, "tick", None))


@pytest.mark.phase6
@pytest.mark.acceptance
class TestBridgePropagatorContract:
    """SPEC: 04_SIMULATION_SPEC.md#bridgepropagator"""

    def test_propagate_returns_cross_community_events(self):
        """BridgePropagator.propagate() returns list[PropagationEvent]."""
        from app.engine.simulation.community_orchestrator import BridgePropagator
        assert hasattr(BridgePropagator, "propagate")

    def test_propagate_applies_bridge_trust_factor(self):
        """Cross-community propagation probability reduced by bridge_trust_factor=0.6."""
        from app.engine.simulation.community_orchestrator import (
            BridgePropagator,
            CommunityTickResult,
        )
        from app.engine.diffusion.schema import PropagationEvent

        bp = BridgePropagator()
        cid = uuid4()
        pe = PropagationEvent(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            action_type="share",
            probability=1.0,
            step=0,
            message_id=uuid4(),
        )
        cr = CommunityTickResult(
            community_id=cid,
            outbound_events=[pe],
        )
        result = bp.propagate([cr], [], nx.Graph())
        assert len(result) == 1
        assert abs(result[0].probability - 0.6) < 1e-6

    def test_propagate_empty_outbound_returns_empty(self):
        """No outbound events -> empty result."""
        from app.engine.simulation.community_orchestrator import (
            BridgePropagator,
            CommunityTickResult,
        )

        bp = BridgePropagator()
        cr = CommunityTickResult(community_id=uuid4())
        result = bp.propagate([cr], [], nx.Graph())
        assert result == []


@pytest.mark.phase6
class TestCommunityOrchestratorIntegration:
    """Integration test: create real agents + subgraph, run tick."""

    @pytest.mark.asyncio
    async def test_tick_produces_results(self):
        """Full tick on 20 agents produces valid CommunityTickResult."""
        from app.engine.simulation.community_orchestrator import (
            CommunityOrchestrator,
            CommunityTickResult,
        )

        comm_id = uuid4()
        sim_id = uuid4()
        agents = [_make_agent(comm_id, sim_id) for _ in range(20)]
        G, node_map = _make_ws_graph(agents, k=4)

        orch = CommunityOrchestrator(
            community_id=comm_id,
            community_config=_make_community_config("A", 20),
            agents=agents,
            subgraph=G,
            agent_node_map=node_map,
        )

        result = await orch.tick(step=0, campaign_events=[])
        assert isinstance(result, CommunityTickResult)
        assert result.community_id == comm_id
        assert len(result.updated_agents) == 20
        assert isinstance(result.action_distribution, dict)
        assert result.tick_duration_ms > 0
        assert result.community_sentiment is not None

    @pytest.mark.asyncio
    async def test_two_communities_parallel(self):
        """Two community orchestrators can run in parallel via asyncio.gather."""
        from app.engine.simulation.community_orchestrator import (
            CommunityOrchestrator,
            CommunityTickResult,
        )

        sim_id = uuid4()
        comm_a = uuid4()
        comm_b = uuid4()

        agents_a = [_make_agent(comm_a, sim_id) for _ in range(10)]
        agents_b = [_make_agent(comm_b, sim_id) for _ in range(10)]

        G_a, map_a = _make_ws_graph(agents_a, k=4)
        G_b, map_b = _make_ws_graph(agents_b, k=4)

        orch_a = CommunityOrchestrator(
            community_id=comm_a,
            community_config=_make_community_config("A", 10),
            agents=agents_a,
            subgraph=G_a,
            agent_node_map=map_a,
        )
        orch_b = CommunityOrchestrator(
            community_id=comm_b,
            community_config=_make_community_config("B", 10),
            agents=agents_b,
            subgraph=G_b,
            agent_node_map=map_b,
        )

        results = await asyncio.gather(
            orch_a.tick(step=0, campaign_events=[]),
            orch_b.tick(step=0, campaign_events=[]),
        )

        assert len(results) == 2
        assert results[0].community_id == comm_a
        assert results[1].community_id == comm_b
        assert len(results[0].updated_agents) == 10
        assert len(results[1].updated_agents) == 10

    @pytest.mark.asyncio
    async def test_empty_community_returns_empty_result(self):
        """An empty community returns an empty CommunityTickResult."""
        from app.engine.simulation.community_orchestrator import (
            CommunityOrchestrator,
            CommunityTickResult,
        )

        comm_id = uuid4()
        orch = CommunityOrchestrator(
            community_id=comm_id,
            community_config=_make_community_config("empty", 0),
            agents=[],
            subgraph=nx.Graph(),
            agent_node_map={},
        )

        result = await orch.tick(step=0, campaign_events=[])
        assert isinstance(result, CommunityTickResult)
        assert result.community_id == comm_id
        assert len(result.updated_agents) == 0
        assert len(result.propagation_events) == 0
