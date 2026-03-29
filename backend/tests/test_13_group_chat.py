"""Tests for Group Chat (G6) and Interview (G8) agent extensions.

Auto-generated from SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md
Generated BEFORE full integration — tests define the contract.
"""
import pytest
from uuid import uuid4, UUID

from app.engine.agent.group_chat import GroupChat, GroupMessage, GroupChatManager
from app.engine.agent.interview import AgentInterviewer, InterviewResponse
from app.engine.agent.schema import (
    AgentState,
    AgentPersonality,
    AgentEmotion,
    AgentType,
    AgentAction,
)


def _make_agent(
    belief: float = 0.5,
    agent_type: AgentType = AgentType.CONSUMER,
    openness: float = 0.7,
    skepticism: float = 0.3,
    trust: float = 0.6,
    excitement: float = 0.5,
) -> AgentState:
    """Helper to create an AgentState for testing."""
    return AgentState(
        agent_id=uuid4(),
        simulation_id=uuid4(),
        agent_type=agent_type,
        step=0,
        personality=AgentPersonality(
            openness=openness,
            skepticism=skepticism,
            trend_following=0.5,
            brand_loyalty=0.5,
            social_influence=0.5,
        ),
        emotion=AgentEmotion(
            interest=0.5,
            trust=trust,
            skepticism=0.3,
            excitement=excitement,
        ),
        belief=belief,
        action=AgentAction.IGNORE,
        exposure_count=0,
        adopted=False,
        community_id=uuid4(),
        influence_score=0.5,
        llm_tier_used=None,
    )


# ---- Group Chat Manager Tests ----


@pytest.mark.phase8
class TestGroupChatManager:
    """SPEC: 13_SCALE_VALIDATION_SPEC.md#group-chat-action"""

    def test_create_group(self) -> None:
        mgr = GroupChatManager()
        members = [uuid4(), uuid4(), uuid4()]
        chat = mgr.create_group(members=members, topic="test topic")

        assert isinstance(chat, GroupChat)
        assert chat.topic == "test topic"
        assert chat.member_count == 3
        assert chat.message_count == 0

    def test_add_message(self) -> None:
        mgr = GroupChatManager()
        a1, a2 = uuid4(), uuid4()
        chat = mgr.create_group(members=[a1, a2], topic="chat")

        msg = mgr.add_message(
            group_id=chat.group_id,
            agent_id=a1,
            content="Hello!",
            step=1,
            sentiment=0.8,
        )
        assert isinstance(msg, GroupMessage)
        assert msg.agent_id == a1
        assert msg.content == "Hello!"
        assert msg.step == 1
        assert msg.sentiment == 0.8
        assert chat.message_count == 1

    def test_non_member_rejected(self) -> None:
        mgr = GroupChatManager()
        a1 = uuid4()
        outsider = uuid4()
        chat = mgr.create_group(members=[a1], topic="private")

        with pytest.raises(ValueError, match="not a member"):
            mgr.add_message(
                group_id=chat.group_id,
                agent_id=outsider,
                content="Intruder!",
                step=0,
            )

    def test_get_messages(self) -> None:
        mgr = GroupChatManager()
        a1 = uuid4()
        chat = mgr.create_group(members=[a1], topic="scroll")

        for i in range(25):
            mgr.add_message(
                group_id=chat.group_id,
                agent_id=a1,
                content=f"msg {i}",
                step=i,
            )

        recent = chat.get_messages(last_n=10)
        assert len(recent) == 10
        assert recent[0].content == "msg 15"
        assert recent[-1].content == "msg 24"

        all_msgs = chat.get_messages(last_n=100)
        assert len(all_msgs) == 25

    def test_delete_group(self) -> None:
        mgr = GroupChatManager()
        chat = mgr.create_group(members=[uuid4()], topic="ephemeral")
        gid = chat.group_id

        mgr.delete_group(gid)
        with pytest.raises(KeyError):
            mgr.get_group(gid)

    def test_delete_nonexistent_group_raises(self) -> None:
        mgr = GroupChatManager()
        with pytest.raises(KeyError):
            mgr.delete_group(uuid4())

    def test_list_groups(self) -> None:
        mgr = GroupChatManager()
        mgr.create_group(members=[uuid4()], topic="a")
        mgr.create_group(members=[uuid4()], topic="b")

        groups = mgr.list_groups()
        assert len(groups) == 2
        topics = {g.topic for g in groups}
        assert topics == {"a", "b"}

    def test_get_nonexistent_group_raises(self) -> None:
        mgr = GroupChatManager()
        with pytest.raises(KeyError):
            mgr.get_group(uuid4())


# ---- Agent Interviewer Tests ----


@pytest.mark.phase8
class TestAgentInterviewer:
    """SPEC: 13_SCALE_VALIDATION_SPEC.md#interview-action"""

    def test_interview_positive_agent(self) -> None:
        agent = _make_agent(belief=0.7)
        interviewer = AgentInterviewer()
        result = interviewer.interview(agent, "What do you think?")

        assert isinstance(result, InterviewResponse)
        assert result.belief == 0.7
        assert "positive" in result.answer.lower()

    def test_interview_negative_agent(self) -> None:
        agent = _make_agent(belief=-0.6)
        interviewer = AgentInterviewer()
        result = interviewer.interview(agent, "What do you think?")

        assert result.belief == -0.6
        assert "negative" in result.answer.lower()

    def test_interview_response_fields(self) -> None:
        agent = _make_agent(belief=0.3)
        interviewer = AgentInterviewer()
        result = interviewer.interview(agent, "Tell me more")

        assert result.agent_id == agent.agent_id
        assert result.question == "Tell me more"
        assert isinstance(result.answer, str)
        assert len(result.answer) > 0
        assert isinstance(result.reasoning, str)
        assert len(result.reasoning) > 0
        assert 0.0 <= result.confidence <= 1.0

    def test_confidence_scales_with_belief(self) -> None:
        interviewer = AgentInterviewer()

        # Agent with strong belief -> higher confidence
        strong = _make_agent(belief=0.9)
        r_strong = interviewer.interview(strong, "q")

        # Agent with weak belief -> lower confidence
        weak = _make_agent(belief=0.1)
        r_weak = interviewer.interview(weak, "q")

        assert r_strong.confidence > r_weak.confidence

    def test_interview_different_agent_types(self) -> None:
        interviewer = AgentInterviewer()
        for atype in AgentType:
            agent = _make_agent(belief=0.5, agent_type=atype)
            result = interviewer.interview(agent, "opinion?")
            assert atype.value in result.reasoning

    def test_interview_extreme_beliefs(self) -> None:
        interviewer = AgentInterviewer()

        pos = _make_agent(belief=1.0)
        r_pos = interviewer.interview(pos, "q")
        assert "strongly positive" in r_pos.answer.lower()

        neg = _make_agent(belief=-1.0)
        r_neg = interviewer.interview(neg, "q")
        assert "strongly negative" in r_neg.answer.lower()
