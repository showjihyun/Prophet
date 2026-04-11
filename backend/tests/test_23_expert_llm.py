"""Tests for Expert Engine LLM Integration (SPEC 23 EX-01~05).

Auto-generated from SPEC: docs/spec/23_EXPERT_LLM_SPEC.md
SPEC Version: 0.1.0
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.engine.agent.schema import (
    AgentAction, AgentEmotion, AgentPersonality, AgentState, AgentType,
)
from app.engine.agent.expert_engine import ExpertInterventionEngine


def _make_expert(belief: float = 0.5, skepticism: float = 0.6) -> AgentState:
    return AgentState(
        agent_id=uuid4(),
        simulation_id=uuid4(),
        community_id=uuid4(),
        agent_type=AgentType.EXPERT,
        personality=AgentPersonality(
            openness=0.5, skepticism=skepticism, trend_following=0.3,
            brand_loyalty=0.4, social_influence=0.8,
        ),
        emotion=AgentEmotion(interest=0.5, trust=0.5, skepticism=0.3, excitement=0.5),
        belief=belief,
        adopted=False,
        step=5,
        action=AgentAction.IGNORE,
        exposure_count=0,
        influence_score=0.8,
        llm_tier_used=3,
    )


def _make_consumer() -> AgentState:
    return AgentState(
        agent_id=uuid4(),
        simulation_id=uuid4(),
        community_id=uuid4(),
        agent_type=AgentType.CONSUMER,
        personality=AgentPersonality(
            openness=0.5, skepticism=0.5, trend_following=0.5,
            brand_loyalty=0.5, social_influence=0.5,
        ),
        emotion=AgentEmotion(interest=0.5, trust=0.5, skepticism=0.3, excitement=0.5),
        belief=0.0,
        adopted=False,
        step=5,
        action=AgentAction.IGNORE,
        exposure_count=0,
        influence_score=0.5,
        llm_tier_used=1,
    )


class _MockCampaign:
    def __init__(self):
        self.name = "TestCampaign"
        self.message = "Buy our product!"
        self.target_communities = []


# ---------------------------------------------------------------------------
# EX-AC-01: Sync method unchanged
# ---------------------------------------------------------------------------

class TestSyncExpertOpinion:
    """SPEC: 23_EXPERT_LLM_SPEC.md#EX-03"""

    def test_sync_generates_heuristic_opinion(self):
        """Sync generate_expert_opinion works as before."""
        engine = ExpertInterventionEngine()
        agent = _make_expert(belief=0.8, skepticism=0.6)
        opinion = engine.generate_expert_opinion(agent, _MockCampaign(), step=5)
        assert opinion is not None
        assert abs(opinion.score - 0.8 * 0.6) < 0.001
        assert opinion.confidence == abs(opinion.score)

    def test_sync_non_expert_returns_none(self):
        """EX-AC-06: Non-EXPERT agent returns None."""
        engine = ExpertInterventionEngine()
        consumer = _make_consumer()
        opinion = engine.generate_expert_opinion(consumer, _MockCampaign(), step=5)
        assert opinion is None


# ---------------------------------------------------------------------------
# EX-AC-02: Async with gateway returns LLM-based opinion
# ---------------------------------------------------------------------------

class TestAsyncExpertOpinion:
    """SPEC: 23_EXPERT_LLM_SPEC.md#EX-01/02"""

    @pytest.mark.asyncio
    async def test_async_with_gateway_uses_llm(self):
        """EX-AC-02: With gateway, returns LLM-generated opinion."""
        engine = ExpertInterventionEngine()
        agent = _make_expert(belief=0.7, skepticism=0.5)

        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "score": 0.85,
            "reasoning": "The campaign shows strong market alignment based on data",
            "confidence": 0.9,
        })

        mock_gateway = AsyncMock()
        mock_gateway.complete = AsyncMock(return_value=mock_response)

        opinion = await engine.generate_expert_opinion_async(
            agent, _MockCampaign(), step=5, gateway=mock_gateway,
        )

        assert opinion is not None
        assert abs(opinion.score - 0.85) < 0.001
        assert "market alignment" in opinion.reasoning
        assert abs(opinion.confidence - 0.9) < 0.001
        mock_gateway.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_without_gateway_falls_back(self):
        """EX-AC-03: Without gateway, falls back to heuristic."""
        engine = ExpertInterventionEngine()
        agent = _make_expert(belief=0.8, skepticism=0.6)

        opinion = await engine.generate_expert_opinion_async(
            agent, _MockCampaign(), step=5, gateway=None,
        )

        assert opinion is not None
        assert abs(opinion.score - 0.8 * 0.6) < 0.001

    @pytest.mark.asyncio
    async def test_async_non_expert_returns_none(self):
        """EX-AC-06: Non-EXPERT returns None even in async path."""
        engine = ExpertInterventionEngine()
        consumer = _make_consumer()

        opinion = await engine.generate_expert_opinion_async(
            consumer, _MockCampaign(), step=5, gateway=AsyncMock(),
        )
        assert opinion is None


# ---------------------------------------------------------------------------
# EX-AC-04: LLM response parsing
# ---------------------------------------------------------------------------

class TestLLMResponseParsing:
    """SPEC: 23_EXPERT_LLM_SPEC.md#EX-02"""

    def test_parse_json_response(self):
        """EX-AC-04: Parses JSON format correctly."""
        agent = _make_expert()
        text = json.dumps({"score": -0.3, "reasoning": "Weak campaign", "confidence": 0.7})
        result = ExpertInterventionEngine._parse_llm_response(text, agent)
        assert result is not None
        score, reasoning, confidence = result
        assert abs(score - (-0.3)) < 0.001
        assert reasoning == "Weak campaign"
        assert abs(confidence - 0.7) < 0.001

    def test_parse_text_format(self):
        """EX-AC-04: Parses SCORE:/REASONING: format."""
        agent = _make_expert()
        text = "SCORE: 0.65\nREASONING: Strong data supports the campaign's claims"
        result = ExpertInterventionEngine._parse_llm_response(text, agent)
        assert result is not None
        score, reasoning, confidence = result
        assert abs(score - 0.65) < 0.001
        assert "Strong data" in reasoning

    def test_parse_clamps_score(self):
        """Score is clamped to [-1.0, 1.0]."""
        agent = _make_expert()
        text = json.dumps({"score": 5.0, "reasoning": "extreme"})
        result = ExpertInterventionEngine._parse_llm_response(text, agent)
        assert result is not None
        assert result[0] == 1.0  # clamped

    def test_parse_malformed_uses_heuristic_score(self):
        """EX-AC-05: Malformed response uses heuristic score with raw text."""
        agent = _make_expert(belief=0.4, skepticism=0.5)
        text = "I think the campaign is good."
        result = ExpertInterventionEngine._parse_llm_response(text, agent)
        assert result is not None
        score, reasoning, _ = result
        assert abs(score - 0.4 * 0.5) < 0.001
        assert "campaign is good" in reasoning

    def test_parse_empty_returns_none(self):
        """Empty response returns None."""
        agent = _make_expert()
        assert ExpertInterventionEngine._parse_llm_response("", agent) is None
        assert ExpertInterventionEngine._parse_llm_response("  ", agent) is None


# ---------------------------------------------------------------------------
# EX-AC-05: Fallback on LLM failure
# ---------------------------------------------------------------------------

class TestExpertLLMFallback:
    """SPEC: 23_EXPERT_LLM_SPEC.md#EX-05"""

    @pytest.mark.asyncio
    async def test_gateway_error_falls_back(self):
        """Gateway exception triggers heuristic fallback."""
        engine = ExpertInterventionEngine()
        agent = _make_expert(belief=0.6, skepticism=0.7)

        mock_gateway = AsyncMock()
        mock_gateway.complete = AsyncMock(side_effect=Exception("LLM timeout"))

        opinion = await engine.generate_expert_opinion_async(
            agent, _MockCampaign(), step=5, gateway=mock_gateway,
        )

        # Should fall back to heuristic
        assert opinion is not None
        assert abs(opinion.score - 0.6 * 0.7) < 0.001

    @pytest.mark.asyncio
    async def test_none_response_falls_back(self):
        """None gateway response triggers heuristic fallback."""
        engine = ExpertInterventionEngine()
        agent = _make_expert(belief=0.5, skepticism=0.8)

        mock_gateway = AsyncMock()
        mock_gateway.complete = AsyncMock(return_value=None)

        opinion = await engine.generate_expert_opinion_async(
            agent, _MockCampaign(), step=5, gateway=mock_gateway,
        )

        assert opinion is not None
        assert abs(opinion.score - 0.5 * 0.8) < 0.001
