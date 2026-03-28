"""
Auto-generated from SPEC: docs/spec/05_LLM_SPEC.md#error-specification
SPEC Version: 0.1.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestLLMTimeoutFallback:
    """SPEC: 05_LLM_SPEC.md#error-specification — timeout recovery"""

    def test_tier3_timeout_falls_back_to_tier2(self):
        """LLM timeout on Tier 3 → fallback to Tier 2."""
        from app.engine.llm.adapter import LLMAdapterManager
        from app.engine.llm.exceptions import LLMTimeoutError
        manager = LLMAdapterManager()
        mock_adapter = MagicMock()
        mock_adapter.complete = AsyncMock(side_effect=LLMTimeoutError("10s exceeded"))
        manager.register_adapter("claude", mock_adapter)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            manager.evaluate(prompt="test", tier=3)
        )
        assert result.tier_used == 2  # fell back

    def test_tier2_timeout_falls_back_to_tier1(self):
        """Tier 2 → Tier 1 fallback chain."""
        from app.engine.llm.adapter import LLMAdapterManager
        from app.engine.llm.exceptions import LLMTimeoutError
        manager = LLMAdapterManager()
        mock_adapter = MagicMock()
        mock_adapter.complete = AsyncMock(side_effect=LLMTimeoutError("timeout"))
        manager.register_adapter("claude", mock_adapter)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            manager.evaluate(prompt="test", tier=2)
        )
        assert result.tier_used == 1


class TestLLMParseError:
    """SPEC: 05_LLM_SPEC.md#error-specification — parse error recovery"""

    def test_invalid_json_retries_then_fallback(self):
        """Invalid JSON → retry once with stricter prompt → fallback tier."""
        from app.engine.llm.adapter import LLMAdapterManager
        from app.engine.llm.exceptions import LLMParseError
        manager = LLMAdapterManager()
        mock_adapter = MagicMock()
        mock_adapter.complete = AsyncMock(side_effect=LLMParseError("not json"))
        manager.register_adapter("claude", mock_adapter)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            manager.evaluate(prompt="test", tier=3)
        )
        # Should have retried once, then fallen back
        assert mock_adapter.complete.await_count >= 2
        assert result.tier_used < 3


class TestLLMRateLimit:
    """SPEC: 05_LLM_SPEC.md#error-specification — rate limit handling"""

    def test_http_429_retries_with_backoff(self):
        """HTTP 429 → exponential backoff (1s, 2s, 4s), max 3 retries."""
        from app.engine.llm.adapter import LLMAdapterManager
        from app.engine.llm.exceptions import LLMRateLimitError
        manager = LLMAdapterManager()
        mock_adapter = MagicMock()
        mock_adapter.complete = AsyncMock(side_effect=LLMRateLimitError("429"))
        manager.register_adapter("claude", mock_adapter)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            manager.evaluate(prompt="test", tier=3)
        )
        # After 3 retries, should fallback
        assert mock_adapter.complete.await_count <= 4  # 1 initial + 3 retries max
        assert result.tier_used < 3


class TestLLMAuthError:
    """SPEC: 05_LLM_SPEC.md#error-specification — auth failure"""

    def test_http_401_no_retry_immediate_fallback(self):
        """HTTP 401 → immediate fallback (no retry)."""
        from app.engine.llm.adapter import LLMAdapterManager
        from app.engine.llm.exceptions import LLMAuthError
        manager = LLMAdapterManager()
        mock_adapter = MagicMock()
        mock_adapter.complete = AsyncMock(side_effect=LLMAuthError("401"))
        manager.register_adapter("claude", mock_adapter)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            manager.evaluate(prompt="test", tier=3)
        )
        assert mock_adapter.complete.await_count == 1  # no retry
        assert result.tier_used < 3


class TestLLMGracefulDegradation:
    """SPEC: 05_LLM_SPEC.md#error-specification — graceful degradation"""

    def test_all_providers_down_degrades_to_tier1(self):
        """All external LLM providers unavailable → degrade to Tier 1 SLM."""
        from app.engine.llm.adapter import LLMAdapterManager
        from app.engine.llm.exceptions import LLMProviderError
        manager = LLMAdapterManager()
        for name in ["claude", "openai"]:
            mock = MagicMock()
            mock.complete = AsyncMock(side_effect=LLMProviderError("5xx"))
            manager.register_adapter(name, mock)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            manager.evaluate(prompt="test", tier=3)
        )
        assert result.tier_used == 1

    def test_ollama_down_is_fatal(self):
        """Ollama unreachable → OllamaConnectionError (CRITICAL, simulation fails)."""
        from app.engine.llm.adapter import LLMAdapterManager
        from app.engine.llm.exceptions import OllamaConnectionError
        manager = LLMAdapterManager()
        with patch.object(manager, '_get_ollama_adapter',
                          side_effect=OllamaConnectionError("connection refused")):
            import asyncio
            with pytest.raises(OllamaConnectionError):
                asyncio.get_event_loop().run_until_complete(
                    manager.evaluate(prompt="test", tier=1)
                )


class TestLLMQuotaManager:
    """SPEC: 05_LLM_SPEC.md#error-specification — quota management"""

    def test_quota_exceeded_skips_llm(self):
        """Quota > 10% → skip LLM, use Tier 2."""
        from app.engine.llm.quota import QuotaManager
        manager = QuotaManager(max_ratio=0.10, total_agents=100)
        # Simulate 10 LLM calls already made
        for _ in range(10):
            manager.record_call()
        assert manager.can_call_llm() is False


class TestLLMScoreClamping:
    """SPEC: 05_LLM_SPEC.md#error-specification — response validation"""

    def test_score_outside_range_clamped(self):
        """LLM score outside [-1, 1] is clamped."""
        from app.engine.llm.adapter import LLMAdapterManager
        result_score = LLMAdapterManager._clamp_score(1.5, min_val=-1.0, max_val=1.0)
        assert result_score == 1.0

    def test_score_negative_outside_range_clamped(self):
        """LLM score < -1 is clamped to -1."""
        from app.engine.llm.adapter import LLMAdapterManager
        result_score = LLMAdapterManager._clamp_score(-2.0, min_val=-1.0, max_val=1.0)
        assert result_score == -1.0


class TestLLMEmbedding:
    """SPEC: 05_LLM_SPEC.md#error-specification — embedding errors"""

    def test_embedding_dimension_mismatch_raises(self):
        """Wrong embedding dimension raises EmbeddingDimensionError."""
        from app.engine.llm.exceptions import EmbeddingDimensionError
        from app.engine.llm.adapter import LLMAdapterManager
        manager = LLMAdapterManager()
        mock_adapter = MagicMock()
        # Return wrong dimension
        mock_adapter.embed = AsyncMock(return_value=[0.1] * 512)  # expect 768
        manager.register_adapter("ollama", mock_adapter)
        import asyncio
        with pytest.raises(EmbeddingDimensionError):
            asyncio.get_event_loop().run_until_complete(
                manager.embed(text="test", expected_dim=768)
            )

    def test_token_limit_truncates_context(self):
        """Prompt exceeding token limit → truncate oldest memories, retry."""
        from app.engine.llm.adapter import LLMAdapterManager
        from app.engine.llm.exceptions import LLMTokenLimitError
        manager = LLMAdapterManager()
        mock_adapter = MagicMock()
        # First call: token limit, second call: success
        mock_adapter.complete = AsyncMock(
            side_effect=[LLMTokenLimitError("8192 exceeded"), MagicMock(text="ok")]
        )
        manager.register_adapter("claude", mock_adapter)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            manager.evaluate(prompt="very long prompt", tier=3,
                             memories=["mem1", "mem2", "mem3"])
        )
        assert mock_adapter.complete.await_count == 2  # retried with truncated context
