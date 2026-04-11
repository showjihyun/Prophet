"""Tests for conversation thread capture and persistence (SPEC 22 CT-01~08).

Auto-generated from SPEC: docs/spec/22_CONVERSATION_THREAD_SPEC.md
SPEC Version: 0.1.0
Generated BEFORE full integration — tests define the contract.
"""
import pytest
from uuid import uuid4, UUID
from dataclasses import dataclass, field

from app.engine.agent.schema import AgentAction, AgentEmotion, AgentPersonality, AgentState
from app.engine.agent.tick import AgentTickResult
from app.engine.agent.influence import PropagationEvent, ContextualPacket, MessageStrength
from app.engine.agent.memory import MemoryRecord
from app.engine.simulation.thread_capture import (
    collect_thread_messages,
    CapturedMessage,
    _stance_content,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_agent(agent_id: UUID | None = None, belief: float = 0.0, action: AgentAction = AgentAction.IGNORE) -> AgentState:
    aid = agent_id or uuid4()
    return AgentState(
        agent_id=aid,
        simulation_id=uuid4(),
        community_id=uuid4(),
        agent_type="consumer",
        personality=AgentPersonality(
            openness=0.5, skepticism=0.5, trend_following=0.5,
            brand_loyalty=0.5, social_influence=0.5,
        ),
        emotion=AgentEmotion(interest=0.5, trust=0.5, skepticism=0.3, excitement=0.5),
        belief=belief,
        adopted=False,
        step=5,
        action=action,
        exposure_count=0,
        influence_score=0.5,
        llm_tier_used=1,
    )


def _make_packet(agent: AgentState) -> ContextualPacket:
    return ContextualPacket(
        source_agent_id=agent.agent_id,
        source_emotion=agent.emotion,
        source_summary="test",
        message_strength=MessageStrength(novelty=0.5, controversy=0.3, utility=0.5),
        sentiment_polarity=agent.belief,
        action_taken=agent.action,
        step=agent.step,
    )


def _make_tick_result(
    agent: AgentState,
    action: AgentAction = AgentAction.SHARE,
    propagation_events: list | None = None,
) -> AgentTickResult:
    return AgentTickResult(
        updated_state=agent,
        propagation_events=propagation_events or [],
        memory_stored=None,
        llm_call_log=None,
        action=action,
        llm_tier_used=1,
    )


# ---------------------------------------------------------------------------
# CT-AC-01: collect returns empty for all-IGNORE step
# ---------------------------------------------------------------------------

class TestCollectThreadMessages:
    """SPEC: 22_CONVERSATION_THREAD_SPEC.md#CT-03"""

    def test_all_ignore_returns_empty(self):
        """CT-AC-01: All IGNORE actions produce no thread messages."""
        agent = _make_agent(action=AgentAction.IGNORE)
        result = _make_tick_result(agent, AgentAction.IGNORE)
        msgs = collect_thread_messages(
            community_id=uuid4(), simulation_id=uuid4(), step=1,
            tick_results=[result], agents={agent.agent_id: agent},
        )
        assert msgs == []

    def test_share_produces_message(self):
        """CT-AC-02: SHARE action produces message with campaign content for Tier 1."""
        agent = _make_agent(belief=0.5, action=AgentAction.SHARE)
        result = _make_tick_result(agent, AgentAction.SHARE)
        msgs = collect_thread_messages(
            community_id=uuid4(), simulation_id=uuid4(), step=3,
            tick_results=[result], agents={agent.agent_id: agent},
            campaign_message="Buy our product!",
        )
        assert len(msgs) == 1
        assert msgs[0].content == "Buy our product!"
        assert msgs[0].action == "share"

    def test_adopt_with_generated_content(self):
        """CT-AC-03: ADOPT with generated_content uses Tier 3 content."""
        agent = _make_agent(belief=0.8, action=AgentAction.ADOPT)
        pe = PropagationEvent(
            source_agent_id=agent.agent_id,
            target_agent_id=uuid4(),
            content_id=uuid4(),
            probability=0.9,
            packet=_make_packet(agent),
            step=5,
            generated_content="I'm convinced this product is revolutionary!",
        )
        result = _make_tick_result(agent, AgentAction.ADOPT, [pe])
        msgs = collect_thread_messages(
            community_id=uuid4(), simulation_id=uuid4(), step=5,
            tick_results=[result], agents={agent.agent_id: agent},
        )
        assert len(msgs) == 1
        assert msgs[0].content == "I'm convinced this product is revolutionary!"

    def test_comment_produces_message(self):
        """COMMENT action produces a thread message."""
        agent = _make_agent(belief=-0.3, action=AgentAction.COMMENT)
        result = _make_tick_result(agent, AgentAction.COMMENT)
        msgs = collect_thread_messages(
            community_id=uuid4(), simulation_id=uuid4(), step=2,
            tick_results=[result], agents={agent.agent_id: agent},
        )
        assert len(msgs) == 1
        assert msgs[0].action == "comment"

    def test_no_campaign_uses_stance_template(self):
        """Without campaign message or generated content, uses stance-based template."""
        agent = _make_agent(belief=0.5, action=AgentAction.SHARE)
        result = _make_tick_result(agent, AgentAction.SHARE)
        msgs = collect_thread_messages(
            community_id=uuid4(), simulation_id=uuid4(), step=1,
            tick_results=[result], agents={agent.agent_id: agent},
            campaign_message="",
        )
        assert len(msgs) == 1
        assert len(msgs[0].content) > 0  # some stance template

    def test_multiple_agents_multiple_messages(self):
        """Multiple agents with visible actions produce multiple messages."""
        agents = {}
        results = []
        for i in range(5):
            a = _make_agent(belief=0.1 * i, action=AgentAction.SHARE)
            agents[a.agent_id] = a
            results.append(_make_tick_result(a, AgentAction.SHARE))
        # Add one IGNORE agent
        ignore_agent = _make_agent(action=AgentAction.IGNORE)
        agents[ignore_agent.agent_id] = ignore_agent
        results.append(_make_tick_result(ignore_agent, AgentAction.IGNORE))

        msgs = collect_thread_messages(
            community_id=uuid4(), simulation_id=uuid4(), step=1,
            tick_results=results, agents=agents,
            campaign_message="campaign msg",
        )
        assert len(msgs) == 5  # 5 SHARE, 1 IGNORE excluded

    def test_reply_to_links_to_propagation_target(self):
        """reply_to_id is set from propagation event target."""
        agent = _make_agent(action=AgentAction.SHARE)
        target_id = uuid4()
        pe = PropagationEvent(
            source_agent_id=agent.agent_id,
            target_agent_id=target_id,
            content_id=uuid4(),
            probability=0.5,
            packet=_make_packet(agent),
            step=1,
        )
        result = _make_tick_result(agent, AgentAction.SHARE, [pe])
        msgs = collect_thread_messages(
            community_id=uuid4(), simulation_id=uuid4(), step=1,
            tick_results=[result], agents={agent.agent_id: agent},
            campaign_message="msg",
        )
        assert msgs[0].reply_to_id == target_id


class TestStanceContent:
    """Test stance-based content templates."""

    def test_positive_belief_positive_content(self):
        content = _stance_content(0.5, 0)
        assert "compelling" in content or "supports" in content or "initiative" in content

    def test_negative_belief_negative_content(self):
        content = _stance_content(-0.5, 0)
        assert "convinced" in content or "hype" in content or "concerns" in content

    def test_neutral_belief_neutral_content(self):
        content = _stance_content(0.0, 0)
        assert "Interesting" in content or "campaign" in content or "Watching" in content
