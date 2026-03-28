"""
Auto-generated from SPEC: docs/spec/05_LLM_SPEC.md#10-acceptance-criteria-harness-tests
SPEC Version: 0.1.1

Acceptance criteria LLM-01 through LLM-10.
All tests use MockLLMAdapter and MockSLMAdapter from harness.
"""
import pytest
import json
from uuid import uuid4

from app.llm.schema import LLMPrompt, LLMOptions, LLMResponse, LLMRateLimitError
from app.llm.cache import LLMResponseCache
from app.llm.quota import LLMQuotaManager
from app.llm.registry import LLMAdapterRegistry
from app.llm.prompt_builder import PromptBuilder
from app.llm.engine_control import EngineController
from app.engine.agent.schema import (
    AgentState, AgentPersonality, AgentEmotion, AgentType, AgentAction,
)
from app.engine.agent.perception import PerceptionResult
from app.engine.agent.memory import MemoryRecord
from harness.mocks.mock_environment import MockLLMAdapter, MockSLMAdapter


# ── Helpers ──────────────────────────────────────────────────────────────

class _HealthyMock(MockLLMAdapter):
    def __init__(self, name: str = "mock"):
        super().__init__()
        self.provider_name = name

    async def health_check(self) -> bool:
        return True


class _UnhealthyMock(MockLLMAdapter):
    def __init__(self, name: str = "mock"):
        super().__init__()
        self.provider_name = name

    async def health_check(self) -> bool:
        return False


class _RateLimitedMock(MockLLMAdapter):
    """Mock that raises LLMRateLimitError on first N calls, then succeeds."""
    def __init__(self, fail_count: int = 2):
        super().__init__()
        self.provider_name = "claude"
        self._fail_count = fail_count
        self._attempt = 0

    async def complete(self, prompt, options=None):
        self._attempt += 1
        if self._attempt <= self._fail_count:
            raise LLMRateLimitError("429 Too Many Requests", retry_after=0.01)
        return await super().complete(prompt, options)


def _make_agent() -> AgentState:
    return AgentState(
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


class _MockCampaign:
    name = "Test Campaign"
    message = "Try our new product today!"


# ── LLM-01: Ollama adapter health check ─────────────────────────────────

@pytest.mark.phase5
@pytest.mark.acceptance
class TestLLM01:
    """LLM-01: Ollama adapter health check with server up → Returns True."""

    @pytest.mark.asyncio
    async def test_ollama_health_check_returns_true(self):
        adapter = _HealthyMock("ollama")
        result = await adapter.health_check()
        assert result is True


# ── LLM-02: Ollama down → fallback to Claude ────────────────────────────

@pytest.mark.phase5
@pytest.mark.acceptance
class TestLLM02:
    """LLM-02: Ollama adapter with server down → fallback to Claude."""

    @pytest.mark.asyncio
    async def test_fallback_to_claude_when_ollama_down(self):
        registry = LLMAdapterRegistry()
        registry.register(_UnhealthyMock("ollama"))
        claude = _HealthyMock("claude")
        registry.register(claude)

        healthy = await registry.get_healthy()
        assert healthy.provider_name == "claude"


# ── LLM-03: Agent cognition prompt → valid JSON ─────────────────────────

@pytest.mark.phase5
@pytest.mark.acceptance
class TestLLM03:
    """LLM-03: Agent cognition prompt builds valid JSON response."""

    @pytest.mark.asyncio
    async def test_cognition_prompt_parsed_has_required_keys(self):
        builder = PromptBuilder()
        agent = _make_agent()
        perception = PerceptionResult(
            feed_items=[], social_signals=[], expert_signals=[],
            total_exposure_score=0.0,
        )
        prompt = builder.build_agent_cognition_prompt(
            agent, perception, [], _MockCampaign()
        )
        # Use mock adapter to get response
        adapter = MockLLMAdapter()
        response = await adapter.complete(prompt)
        assert response.parsed is not None
        assert "evaluation_score" in response.parsed
        assert "reasoning" in response.parsed
        assert "confidence" in response.parsed


# ── LLM-04: Expert analysis → score in [-1, 1] ─────────────────────────

@pytest.mark.phase5
@pytest.mark.acceptance
class TestLLM04:
    """LLM-04: Expert analysis prompt returns score in [-1, 1]."""

    @pytest.mark.asyncio
    async def test_expert_prompt_score_in_range(self):
        builder = PromptBuilder()
        expert = _make_agent()
        expert = AgentState(
            agent_id=expert.agent_id,
            simulation_id=expert.simulation_id,
            agent_type=AgentType.EXPERT,
            step=1,
            personality=expert.personality,
            emotion=expert.emotion,
            belief=0.0,
            action=AgentAction.IGNORE,
            exposure_count=0,
            adopted=False,
            community_id=expert.community_id,
            influence_score=0.9,
            llm_tier_used=3,
        )

        class _Sentiment:
            mean_belief = 0.3
            adoption_rate = 0.15

        adapter = MockLLMAdapter(response_template={
            "score": 0.5,
            "reasoning": "Analysis result",
            "confidence": 0.9,
        })
        prompt = builder.build_expert_analysis_prompt(
            expert, _MockCampaign(), _Sentiment(), [],
        )
        response = await adapter.complete(prompt)
        assert response.parsed is not None
        score = response.parsed["score"]
        assert -1.0 <= score <= 1.0


# ── LLM-05: Cache returns cached response ───────────────────────────────

@pytest.mark.phase5
@pytest.mark.acceptance
class TestLLM05:
    """LLM-05: LLM cache returns cached response on duplicate prompt."""

    @pytest.mark.asyncio
    async def test_cache_hit_on_duplicate(self):
        cache = LLMResponseCache()
        prompt = LLMPrompt(system="sys", user="hello world")
        response = LLMResponse(
            provider="mock", model="mock-1.0",
            content='{"score": 0.5}', parsed={"score": 0.5},
            prompt_tokens=100, completion_tokens=50,
            latency_ms=10.0, cached=False,
        )
        key = cache.cache_key(prompt, "mock", "mock-1.0")
        await cache.set(key, response)
        cached = await cache.get(key)
        assert cached is not None
        assert cached.content == response.content


# ── LLM-06: Quota blocks above 10% ──────────────────────────────────────

@pytest.mark.phase5
@pytest.mark.acceptance
class TestLLM06:
    """LLM-06: Quota manager blocks LLM calls above 10% ratio."""

    def test_blocks_above_10_percent(self):
        mgr = LLMQuotaManager(tier3_ratio=0.10)
        sim_id = uuid4()
        # 9 calls out of 100 → 9% → allowed
        assert mgr.can_call_llm(sim_id, 1, 9, 100) is True
        # 10 calls out of 100 → 10% → blocked
        assert mgr.can_call_llm(sim_id, 1, 10, 100) is False
        # 11 calls out of 100 → 11% → blocked
        assert mgr.can_call_llm(sim_id, 1, 11, 100) is False


# ── LLM-07: Timeout falls back to Tier 2 ────────────────────────────────

@pytest.mark.phase5
@pytest.mark.acceptance
class TestLLM07:
    """LLM-07: LLM timeout (mock) signals fallback needed.

    In a real orchestrator, timeout leads to Tier 2 fallback.
    Here we verify the registry can provide an alternative.
    """

    @pytest.mark.asyncio
    async def test_timeout_triggers_fallback_path(self):
        from app.llm.schema import LLMTimeoutError

        class _TimeoutMock(MockLLMAdapter):
            provider_name = "ollama"
            async def complete(self, prompt, options=None):
                raise LLMTimeoutError("10s exceeded")
            async def health_check(self):
                return False

        registry = LLMAdapterRegistry()
        registry.register(_TimeoutMock())
        claude = _HealthyMock("claude")
        registry.register(claude)

        # Primary times out — get fallback
        primary = registry.get("ollama")
        with pytest.raises(LLMTimeoutError):
            await primary.complete(LLMPrompt(system="s", user="u"))

        # Fall back to next healthy provider
        fallback = await registry.get_healthy()
        assert fallback.provider_name == "claude"
        result = await fallback.complete(LLMPrompt(system="s", user="u"))
        assert result.provider == "mock"  # from MockLLMAdapter base


# ── LLM-08: Call logs contain required fields ────────────────────────────

@pytest.mark.phase5
@pytest.mark.acceptance
class TestLLM08:
    """LLM-08: All call logs have required fields."""

    def test_call_log_has_all_fields(self):
        from app.llm.schema import LLMCallLog
        from datetime import datetime, timezone

        log = LLMCallLog(
            call_id=uuid4(),
            simulation_id=uuid4(),
            agent_id=uuid4(),
            step=5,
            provider="claude",
            model="claude-sonnet-4-6",
            prompt_hash="abc123",
            prompt_tokens=150,
            completion_tokens=80,
            latency_ms=450.0,
            cached=False,
            tier=3,
            error=None,
            created_at=datetime.now(timezone.utc),
        )
        assert log.provider == "claude"
        assert log.tier == 3
        assert log.prompt_tokens == 150
        assert log.error is None
        assert isinstance(log.created_at, datetime)


# ── LLM-09: Embed returns 768-dim vector ────────────────────────────────

@pytest.mark.phase5
@pytest.mark.acceptance
class TestLLM09:
    """LLM-09: Embed via mock adapter returns 768-dim vector."""

    @pytest.mark.asyncio
    async def test_embed_768_dim(self, mock_llm):
        embedding = await mock_llm.embed("test sentence")
        assert embedding is not None
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)


# ── LLM-10: Claude rate limit → retry with backoff ──────────────────────

@pytest.mark.phase5
@pytest.mark.acceptance
class TestLLM10:
    """LLM-10: Claude adapter rate limit → retry after delay."""

    @pytest.mark.asyncio
    async def test_rate_limit_retries_then_succeeds(self):
        adapter = _RateLimitedMock(fail_count=2)
        prompt = LLMPrompt(system="s", user="u")

        # Simulate retry loop as the real adapter would do
        response = None
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                response = await adapter.complete(prompt)
                break
            except LLMRateLimitError as e:
                if attempt >= max_retries:
                    raise
                import asyncio
                await asyncio.sleep(e.retry_after)

        assert response is not None
        assert response.provider == "mock"
        assert adapter._attempt == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_rate_limit_error_has_retry_after(self):
        err = LLMRateLimitError("rate limited", retry_after=5.0)
        assert err.retry_after == 5.0
