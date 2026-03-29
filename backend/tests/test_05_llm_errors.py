"""
Auto-generated from SPEC: docs/spec/05_LLM_SPEC.md#error-specification
SPEC Version: 0.1.0
Tests for LLM error handling, fallback chains, quota, clamping, embeddings.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def registry():
    """Fresh LLMAdapterRegistry with no adapters."""
    from app.llm.registry import LLMAdapterRegistry
    return LLMAdapterRegistry()


def _make_mock_adapter(side_effect=None, return_value=None):
    """Create a mock adapter whose .complete() is an AsyncMock."""
    adapter = MagicMock()
    if side_effect is not None:
        adapter.complete = AsyncMock(side_effect=side_effect)
    elif return_value is not None:
        adapter.complete = AsyncMock(return_value=return_value)
    else:
        adapter.complete = AsyncMock(return_value=MagicMock(content="ok"))
    return adapter


# -----------------------------------------------------------------------
# Timeout fallback
# -----------------------------------------------------------------------

class TestLLMTimeoutFallback:
    """SPEC: 05_LLM_SPEC.md#error-specification — timeout recovery"""

    @pytest.mark.asyncio
    async def test_tier3_timeout_falls_back_to_tier2(self, registry):
        """LLM timeout on Tier 3 -> fallback to Tier 2."""
        from app.llm.schema import LLMTimeoutError

        mock_adapter = _make_mock_adapter(side_effect=LLMTimeoutError("10s exceeded"))
        registry.register_adapter("claude", mock_adapter)
        result = await registry.evaluate(prompt="test", tier=3)
        # All tiers use same mock that always times out -> eventually tier 1
        assert result.tier_used < 3

    @pytest.mark.asyncio
    async def test_tier2_timeout_falls_back_to_tier1(self, registry):
        """Tier 2 -> Tier 1 fallback chain."""
        from app.llm.schema import LLMTimeoutError

        mock_adapter = _make_mock_adapter(side_effect=LLMTimeoutError("timeout"))
        registry.register_adapter("claude", mock_adapter)
        result = await registry.evaluate(prompt="test", tier=2)
        assert result.tier_used == 1


# -----------------------------------------------------------------------
# Parse error
# -----------------------------------------------------------------------

class TestLLMParseError:
    """SPEC: 05_LLM_SPEC.md#error-specification — parse error recovery"""

    @pytest.mark.asyncio
    async def test_invalid_json_retries_then_fallback(self, registry):
        """Invalid JSON -> retry once with stricter prompt -> fallback tier."""
        from app.llm.schema import LLMParseError

        mock_adapter = _make_mock_adapter(side_effect=LLMParseError("not json"))
        registry.register_adapter("claude", mock_adapter)
        result = await registry.evaluate(prompt="test", tier=3)
        # Should have retried once (stricter), then fallen back
        assert mock_adapter.complete.await_count >= 2
        assert result.tier_used < 3


# -----------------------------------------------------------------------
# Rate limit
# -----------------------------------------------------------------------

class TestLLMRateLimit:
    """SPEC: 05_LLM_SPEC.md#error-specification — rate limit handling"""

    @pytest.mark.asyncio
    async def test_http_429_retries_with_backoff(self, registry):
        """HTTP 429 -> exponential backoff, max 3 retries, then fallback."""
        from app.llm.schema import LLMRateLimitError

        mock_adapter = _make_mock_adapter(side_effect=LLMRateLimitError("429"))
        registry.register_adapter("claude", mock_adapter)
        result = await registry.evaluate(prompt="test", tier=3)
        # 1 initial + 3 retries = 4 calls max for this tier
        assert mock_adapter.complete.await_count <= 4
        assert result.tier_used < 3


# -----------------------------------------------------------------------
# Auth error
# -----------------------------------------------------------------------

class TestLLMAuthError:
    """SPEC: 05_LLM_SPEC.md#error-specification — auth failure"""

    @pytest.mark.asyncio
    async def test_http_401_no_retry_immediate_fallback(self, registry):
        """HTTP 401 -> immediate fallback (no retry)."""
        from app.llm.schema import LLMAuthError

        mock_adapter = _make_mock_adapter(side_effect=LLMAuthError("401"))
        registry.register_adapter("claude", mock_adapter)
        result = await registry.evaluate(prompt="test", tier=3)
        assert mock_adapter.complete.await_count == 1  # no retry
        assert result.tier_used < 3


# -----------------------------------------------------------------------
# Graceful degradation
# -----------------------------------------------------------------------

class TestLLMGracefulDegradation:
    """SPEC: 05_LLM_SPEC.md#error-specification — graceful degradation"""

    @pytest.mark.asyncio
    async def test_all_providers_down_degrades_to_tier1(self, registry):
        """All external LLM providers unavailable -> degrade to Tier 1."""
        from app.llm.schema import LLMProviderError

        for name in ["claude", "openai"]:
            mock = _make_mock_adapter(side_effect=LLMProviderError("5xx"))
            registry.register_adapter(name, mock)
        result = await registry.evaluate(prompt="test", tier=3)
        assert result.tier_used == 1

    @pytest.mark.asyncio
    async def test_ollama_down_is_fatal(self, registry):
        """Ollama unreachable -> OllamaConnectionError (CRITICAL)."""
        from app.llm.schema import OllamaConnectionError

        with patch.object(
            registry,
            "_get_ollama_adapter",
            side_effect=OllamaConnectionError("connection refused"),
        ):
            # evaluate at tier=1 should try Ollama and raise
            # We patch _pick_adapter to raise OllamaConnectionError
            with patch.object(
                registry,
                "_call_adapter",
                side_effect=OllamaConnectionError("connection refused"),
            ):
                registry.register_adapter("ollama", MagicMock())
                with pytest.raises(OllamaConnectionError):
                    await registry.evaluate(prompt="test", tier=1)


# -----------------------------------------------------------------------
# Quota
# -----------------------------------------------------------------------

class TestLLMQuotaManager:
    """SPEC: 05_LLM_SPEC.md#error-specification — quota management"""

    def test_quota_exceeded_skips_llm(self):
        """Quota > 10% -> skip LLM, use Tier 2."""
        from app.llm.quota import LLMQuotaManager
        from uuid import uuid4

        manager = LLMQuotaManager(tier3_ratio=0.10)
        sim_id = uuid4()
        # 10 out of 100 agents = 10% -> should be blocked
        assert manager.can_call_llm(
            simulation_id=sim_id,
            step=1,
            current_llm_call_count=10,
            total_agents=100,
        ) is False


# -----------------------------------------------------------------------
# Score clamping
# -----------------------------------------------------------------------

class TestLLMScoreClamping:
    """SPEC: 05_LLM_SPEC.md#error-specification — response validation"""

    def test_score_outside_range_clamped(self):
        """LLM score outside [-1, 1] is clamped."""
        from app.llm.registry import LLMAdapterRegistry
        result_score = LLMAdapterRegistry._clamp_score(1.5, min_val=-1.0, max_val=1.0)
        assert result_score == 1.0

    def test_score_negative_outside_range_clamped(self):
        """LLM score < -1 is clamped to -1."""
        from app.llm.registry import LLMAdapterRegistry
        result_score = LLMAdapterRegistry._clamp_score(-2.0, min_val=-1.0, max_val=1.0)
        assert result_score == -1.0


# -----------------------------------------------------------------------
# Embedding
# -----------------------------------------------------------------------

class TestLLMEmbedding:
    """SPEC: 05_LLM_SPEC.md#error-specification — embedding errors"""

    @pytest.mark.asyncio
    async def test_embedding_dimension_mismatch_raises(self, registry):
        """Wrong embedding dimension raises EmbeddingDimensionError."""
        from app.llm.schema import EmbeddingDimensionError

        mock_adapter = MagicMock()
        mock_adapter.embed = AsyncMock(return_value=[0.1] * 512)  # expect 768
        registry.register_adapter("ollama", mock_adapter)
        with pytest.raises(EmbeddingDimensionError):
            await registry.embed(text="test", expected_dim=768)

    @pytest.mark.asyncio
    async def test_token_limit_truncates_context(self, registry):
        """Prompt exceeding token limit -> truncate oldest memories, retry."""
        from app.llm.schema import LLMTokenLimitError

        mock_adapter = MagicMock()
        # First call: token limit, second call: success
        mock_adapter.complete = AsyncMock(
            side_effect=[LLMTokenLimitError("8192 exceeded"), MagicMock(text="ok")]
        )
        registry.register_adapter("claude", mock_adapter)
        result = await registry.evaluate(
            prompt="very long prompt",
            tier=3,
            memories=["mem1", "mem2", "mem3"],
        )
        assert mock_adapter.complete.await_count == 2  # retried with truncated context
