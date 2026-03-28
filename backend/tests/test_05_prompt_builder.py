"""
Auto-generated from SPEC: docs/spec/05_LLM_SPEC.md#5-prompt-builder
SPEC Version: 0.1.1
Generated BEFORE implementation verification — tests define the contract.
"""
import pytest
from uuid import uuid4

from app.llm.prompt_builder import PromptBuilder
from app.llm.schema import LLMPrompt
from app.engine.agent.schema import (
    AgentState,
    AgentPersonality,
    AgentEmotion,
    AgentType,
    AgentAction,
)
from app.engine.agent.perception import PerceptionResult, FeedItem, SocialSignal, ExpertSignal
from app.engine.agent.memory import MemoryRecord


def _make_agent(**overrides) -> AgentState:
    defaults = dict(
        agent_id=uuid4(),
        simulation_id=uuid4(),
        agent_type=AgentType.CONSUMER,
        step=1,
        personality=AgentPersonality(0.7, 0.3, 0.5, 0.4, 0.6),
        emotion=AgentEmotion(0.8, 0.6, 0.2, 0.5),
        belief=0.0,
        action=AgentAction.IGNORE,
        exposure_count=0,
        adopted=False,
        community_id=uuid4(),
        influence_score=0.5,
        llm_tier_used=None,
    )
    defaults.update(overrides)
    return AgentState(**defaults)


def _make_perception() -> PerceptionResult:
    return PerceptionResult(
        feed_items=[
            FeedItem(
                content_id=uuid4(),
                event_type="campaign_ad",
                message="Buy our product!",
                source_agent_id=None,
                exposure_score=0.8,
                channel="social_feed",
            )
        ],
        social_signals=[
            SocialSignal(
                neighbor_id=uuid4(),
                action=AgentAction.LIKE,
                edge_weight=0.9,
                weighted_score=0.27,
            )
        ],
        expert_signals=[],
        total_exposure_score=0.8,
    )


def _make_memory() -> MemoryRecord:
    return MemoryRecord(
        memory_id=uuid4(),
        agent_id=uuid4(),
        memory_type="episodic",
        content="Saw a positive review of the product",
        timestamp=1,
        emotion_weight=0.7,
        social_importance=0.5,
        embedding=None,
        relevance_score=None,
    )


class _MockCampaign:
    """Lightweight campaign mock for prompt building."""
    def __init__(self):
        self.name = "Summer Sale 2026"
        self.message = "Get 50% off all products this summer!"


class _MockSentiment:
    """Lightweight community sentiment mock."""
    def __init__(self):
        self.mean_belief = 0.3
        self.adoption_rate = 0.15


@pytest.mark.phase5
class TestAgentCognitionPrompt:
    """SPEC: 05_LLM_SPEC.md#5-prompt-builder — agent cognition"""

    def test_returns_llm_prompt(self):
        builder = PromptBuilder()
        agent = _make_agent()
        perception = _make_perception()
        memories = [_make_memory()]
        campaign = _MockCampaign()

        result = builder.build_agent_cognition_prompt(agent, perception, memories, campaign)
        assert isinstance(result, LLMPrompt)

    def test_response_format_is_json(self):
        builder = PromptBuilder()
        result = builder.build_agent_cognition_prompt(
            _make_agent(), _make_perception(), [], _MockCampaign()
        )
        assert result.response_format == "json"

    def test_system_contains_agent_id(self):
        agent = _make_agent()
        builder = PromptBuilder()
        result = builder.build_agent_cognition_prompt(
            agent, _make_perception(), [], _MockCampaign()
        )
        assert str(agent.agent_id) in result.system

    def test_system_contains_personality(self):
        builder = PromptBuilder()
        result = builder.build_agent_cognition_prompt(
            _make_agent(), _make_perception(), [], _MockCampaign()
        )
        assert "openness=" in result.system
        assert "skepticism=" in result.system

    def test_user_contains_campaign_message(self):
        builder = PromptBuilder()
        campaign = _MockCampaign()
        result = builder.build_agent_cognition_prompt(
            _make_agent(), _make_perception(), [], campaign
        )
        assert campaign.message in result.user

    def test_user_contains_emotion(self):
        builder = PromptBuilder()
        result = builder.build_agent_cognition_prompt(
            _make_agent(), _make_perception(), [], _MockCampaign()
        )
        assert "interest=" in result.user
        assert "trust=" in result.user

    def test_user_contains_actions(self):
        builder = PromptBuilder()
        result = builder.build_agent_cognition_prompt(
            _make_agent(), _make_perception(), [], _MockCampaign()
        )
        assert "evaluation_score" in result.user
        assert "confidence" in result.user

    def test_context_has_agent_id(self):
        agent = _make_agent()
        builder = PromptBuilder()
        result = builder.build_agent_cognition_prompt(
            agent, _make_perception(), [], _MockCampaign()
        )
        assert "agent_id" in result.context
        assert result.context["agent_id"] == str(agent.agent_id)

    def test_memories_included_in_user(self):
        builder = PromptBuilder()
        memory = _make_memory()
        result = builder.build_agent_cognition_prompt(
            _make_agent(), _make_perception(), [memory], _MockCampaign()
        )
        assert memory.content in result.user


@pytest.mark.phase5
class TestExpertAnalysisPrompt:
    """SPEC: 05_LLM_SPEC.md#5-prompt-builder — expert analysis"""

    def test_returns_llm_prompt(self):
        builder = PromptBuilder()
        expert = _make_agent(agent_type=AgentType.EXPERT)
        result = builder.build_expert_analysis_prompt(
            expert, _MockCampaign(), _MockSentiment(), []
        )
        assert isinstance(result, LLMPrompt)

    def test_response_format_json(self):
        builder = PromptBuilder()
        result = builder.build_expert_analysis_prompt(
            _make_agent(agent_type=AgentType.EXPERT),
            _MockCampaign(), _MockSentiment(), [],
        )
        assert result.response_format == "json"

    def test_system_contains_expert_role(self):
        builder = PromptBuilder()
        result = builder.build_expert_analysis_prompt(
            _make_agent(agent_type=AgentType.EXPERT),
            _MockCampaign(), _MockSentiment(), [],
        )
        assert "expert" in result.system.lower()

    def test_user_contains_campaign_info(self):
        builder = PromptBuilder()
        campaign = _MockCampaign()
        result = builder.build_expert_analysis_prompt(
            _make_agent(agent_type=AgentType.EXPERT),
            campaign, _MockSentiment(), [],
        )
        assert campaign.name in result.user
        assert campaign.message in result.user

    def test_user_contains_sentiment(self):
        builder = PromptBuilder()
        result = builder.build_expert_analysis_prompt(
            _make_agent(agent_type=AgentType.EXPERT),
            _MockCampaign(), _MockSentiment(), [],
        )
        assert "0.3" in result.user  # mean_belief
        assert "0.15" in result.user  # adoption_rate


@pytest.mark.phase5
class TestMemoryReflectionPrompt:
    """SPEC: 05_LLM_SPEC.md#5-prompt-builder — memory reflection"""

    def test_returns_llm_prompt(self):
        builder = PromptBuilder()
        result = builder.build_memory_reflection_prompt(
            _make_agent(), [_make_memory()],
        )
        assert isinstance(result, LLMPrompt)

    def test_response_format_json(self):
        builder = PromptBuilder()
        result = builder.build_memory_reflection_prompt(
            _make_agent(), [_make_memory()],
        )
        assert result.response_format == "json"

    def test_user_contains_belief_delta(self):
        builder = PromptBuilder()
        result = builder.build_memory_reflection_prompt(
            _make_agent(), [_make_memory()],
        )
        assert "belief_delta" in result.user

    def test_user_contains_events(self):
        builder = PromptBuilder()
        memory = _make_memory()
        result = builder.build_memory_reflection_prompt(
            _make_agent(), [memory],
        )
        assert memory.content in result.user

    def test_context_has_event_count(self):
        builder = PromptBuilder()
        events = [_make_memory() for _ in range(5)]
        result = builder.build_memory_reflection_prompt(
            _make_agent(), events,
        )
        assert result.context["event_count"] == 5
