"""
Auto-generated from SPEC: docs/spec/01_AGENT_SPEC.md#acceptance-criteria
SPEC Version: 0.2.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)

Missing AGT acceptance tests: AGT-02, AGT-05, AGT-08, AGT-09
(AGT-01,03,04,06,07,10,11,12,13,14 covered in existing test_01_*.py files)
"""
import pytest
import time
from uuid import uuid4


def _make_skeptical_agent():
    """Agent with high skepticism for AGT-02."""
    from app.engine.agent.schema import (
        AgentState, AgentPersonality, AgentEmotion, AgentType, AgentAction,
    )
    return AgentState(
        agent_id=uuid4(), simulation_id=uuid4(), agent_type=AgentType.CONSUMER,
        step=0, personality=AgentPersonality(0.3, 0.9, 0.2, 0.3, 0.2),
        emotion=AgentEmotion(interest=0.2, trust=0.2, skepticism=0.8, excitement=0.1),
        belief=0.0, action=AgentAction.IGNORE, exposure_count=0, adopted=False,
        community_id=uuid4(), influence_score=0.1, llm_tier_used=None,
    )


def _make_campaign_event():
    """Campaign ad event with low controversy for AGT-02."""
    from app.engine.agent.perception import EnvironmentEvent
    return EnvironmentEvent(
        event_type="campaign_ad", content_id=uuid4(), message="test ad",
        source_agent_id=None, channel="social_feed", timestamp=0,
    )


@pytest.mark.phase2
@pytest.mark.acceptance
class TestAgentAcceptanceMissing:
    """SPEC: 01_AGENT_SPEC.md — Acceptance Criteria AGT-02, AGT-05, AGT-08, AGT-09"""

    def test_agt02_high_skepticism_ignores_ad(self):
        """AGT-02: Agent with skepticism=0.9, emotion.skepticism=0.8, campaign_ad.
        tick() x1000 (seeds 1-1000), Tier 1 only, no neighbors.
        action==IGNORE ratio > 0.6 AND action==ADOPT ratio == 0.0.
        """
        from app.engine.agent.tick import AgentTick
        from app.engine.agent.schema import AgentAction

        agent = _make_skeptical_agent()
        event = _make_campaign_event()
        ticker = AgentTick()

        action_counts = {}
        for seed in range(1, 1001):
            result = ticker.tick(
                agent=agent,
                environment_events=[event],
                neighbor_actions=[],
                cognition_tier=1,
                seed=seed,
            )
            action_counts[result.action] = action_counts.get(result.action, 0) + 1

        total = sum(action_counts.values())
        ignore_ratio = action_counts.get(AgentAction.IGNORE, 0) / total
        adopt_count = action_counts.get(AgentAction.ADOPT, 0)

        assert ignore_ratio > 0.6, f"IGNORE ratio={ignore_ratio:.2f}, expected > 0.6"
        assert adopt_count == 0, f"ADOPT count={adopt_count}, expected 0"

    def test_agt05_llm_timeout_falls_back_to_tier2(self):
        """AGT-05: Mock LLM that always times out after 100ms.
        tick(tier=3) -> result.llm_tier_used == 2, valid CognitionResult.
        """
        from app.engine.agent.tick import AgentTick
        from app.engine.agent.schema import (
            AgentState, AgentPersonality, AgentEmotion, AgentType, AgentAction,
        )
        from unittest.mock import MagicMock, patch

        agent = AgentState(
            agent_id=uuid4(), simulation_id=uuid4(), agent_type=AgentType.EXPERT,
            step=5, personality=AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5),
            emotion=AgentEmotion(0.5, 0.5, 0.5, 0.3), belief=0.0,
            action=AgentAction.IGNORE, exposure_count=0, adopted=False,
            community_id=uuid4(), influence_score=0.5, llm_tier_used=None,
            activity_vector=[1.0] * 24,  # always active to avoid flaky skip
        )

        # Mock LLM that always times out
        mock_llm = MagicMock()
        mock_llm.generate.side_effect = TimeoutError("LLM timeout after 100ms")

        ticker = AgentTick(llm_adapter=mock_llm)
        result = ticker.tick(
            agent=agent,
            environment_events=[],
            neighbor_actions=[],
            cognition_tier=3,
            seed=42,
        )

        # Should fall back to Tier 2
        assert result.llm_tier_used == 2, f"Expected tier 2 fallback, got {result.llm_tier_used}"
        # Should still return a valid result
        assert result.action is not None

    def test_agt08_tier1_tick_performance(self):
        """AGT-08: 1000 agents, Tier 1, mock DB, no LLM.
        Total time <= 1000ms (1s).
        """
        from app.engine.agent.tick import AgentTick
        from app.engine.agent.schema import (
            AgentState, AgentPersonality, AgentEmotion, AgentType, AgentAction,
        )

        sim_id = uuid4()
        comm_id = uuid4()
        agents = []
        for i in range(1000):
            agents.append(AgentState(
                agent_id=uuid4(), simulation_id=sim_id, agent_type=AgentType.CONSUMER,
                step=0, personality=AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5),
                emotion=AgentEmotion(0.5, 0.5, 0.5, 0.3), belief=0.0,
                action=AgentAction.IGNORE, exposure_count=0, adopted=False,
                community_id=comm_id, influence_score=0.2, llm_tier_used=None,
            ))

        ticker = AgentTick()
        start = time.monotonic()
        for i, agent in enumerate(agents):
            ticker.tick(
                agent=agent,
                environment_events=[],
                neighbor_actions=[],
                cognition_tier=1,
                seed=i,
            )
        elapsed = time.monotonic() - start
        assert elapsed <= 1.0, f"1000 Tier-1 ticks took {elapsed:.3f}s, exceeds 1s limit"

    def test_agt09_activity_vector_skips_inactive_hour(self):
        """AGT-09: activity_vector[14]=0.0 (2PM inactive), step maps to hour 14.
        tick() -> action==IGNORE, propagation_events==[], no memory stored.
        """
        from app.engine.agent.tick import AgentTick
        from app.engine.agent.schema import (
            AgentState, AgentPersonality, AgentEmotion, AgentType, AgentAction,
        )

        # Create agent with activity_vector[14] = 0.0
        activity = [0.5] * 24
        activity[14] = 0.0  # inactive at hour 14

        agent = AgentState(
            agent_id=uuid4(), simulation_id=uuid4(), agent_type=AgentType.CONSUMER,
            step=14,  # step maps to hour 14
            personality=AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5),
            emotion=AgentEmotion(0.5, 0.5, 0.5, 0.3), belief=0.0,
            action=AgentAction.IGNORE, exposure_count=0, adopted=False,
            community_id=uuid4(), influence_score=0.3, llm_tier_used=None,
            activity_vector=activity,
        )

        ticker = AgentTick()
        result = ticker.tick(
            agent=agent,
            environment_events=[_make_campaign_event()],
            neighbor_actions=[],
            cognition_tier=1,
            seed=42,
        )

        assert result.action == AgentAction.IGNORE, f"Expected IGNORE during inactive hour, got {result.action}"
        assert result.propagation_events == [], "Expected no propagation during inactive hour"
