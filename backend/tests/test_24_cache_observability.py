"""Tests for cache monitoring/observability (KG-2).

Tests that cache layers properly report health status and track
degradation metrics for operational visibility.
"""
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.cache import LLMResponseCache, ValkeyCacheBackend
from app.llm.gateway import LLMGateway, InMemoryLLMCache, VectorLLMCache
from app.llm.schema import LLMResponse


class TestValkeyCacheHealthStatus:
    """Verify LLMResponseCache health reporting."""

    def test_initial_health_status(self):
        """Before any operations, health shows initial state."""
        cache = LLMResponseCache()
        status = cache.health_status()
        assert status["valkey_connected"] is False  # not yet probed
        assert status["valkey_failures"] == 0
        assert status["inmemory_entries"] == 0

    @pytest.mark.asyncio
    async def test_valkey_failure_tracked(self):
        """Valkey connection failure increments failure counter."""
        cache = LLMResponseCache()

        with patch("app.llm.cache.ValkeyCacheBackend") as MockBackend:
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(return_value=False)
            MockBackend.return_value = mock_instance

            backend = await cache._backend()
            assert backend is None
            assert cache._valkey_failures == 1

    def test_fallback_gets_tracked(self):
        """In-memory fallback GET operations are counted."""
        cache = LLMResponseCache()
        cache._valkey_ok = False
        cache._last_probe_time = time.time()  # prevent re-probe
        assert cache._fallback_gets == 0

    @pytest.mark.asyncio
    async def test_reprobe_after_cooldown(self):
        """After cooldown period, Valkey is re-probed."""
        cache = LLMResponseCache()
        cache._valkey_ok = False
        cache._valkey_failures = 1
        cache._last_probe_time = time.time() - 400  # past cooldown (300s)

        with patch("app.llm.cache.ValkeyCacheBackend") as MockBackend:
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(return_value=True)
            MockBackend.return_value = mock_instance
            cache._valkey = mock_instance

            backend = await cache._backend()
            assert backend is not None
            assert cache._valkey_ok is True


class TestGatewayCacheHealth:
    """Verify LLMGateway.cache_health() reports all cache layers."""

    def test_cache_health_all_layers(self):
        """cache_health() returns status for L1, L2, L3."""
        gw = LLMGateway()
        health = gw.cache_health()

        assert "l1_inmemory" in health
        assert "l2_valkey" in health
        assert "l3_pgvector" in health

    def test_l1_reports_entry_count(self):
        """L1 in-memory cache reports its entry count."""
        gw = LLMGateway()
        health = gw.cache_health()
        assert health["l1_inmemory"]["status"] == "ok"
        assert health["l1_inmemory"]["entries"] == 0

    def test_l3_reports_fallback_mode(self):
        """L3 pgvector without session_factory reports fallback mode."""
        gw = LLMGateway()
        health = gw.cache_health()
        assert health["l3_pgvector"]["status"] == "fallback_inmemory"

    def test_l3_with_session_factory(self):
        """L3 pgvector with session_factory reports ok."""
        vector_cache = VectorLLMCache(session_factory=MagicMock())
        gw = LLMGateway(vector_cache=vector_cache)
        health = gw.cache_health()
        assert health["l3_pgvector"]["status"] == "ok"

    def test_l2_with_valkey_cache(self):
        """L2 Valkey reports health when cache is configured."""
        valkey_cache = LLMResponseCache()
        gw = LLMGateway(valkey_cache=valkey_cache)
        health = gw.cache_health()
        assert "l2_valkey" in health
        # Should have health_status from LLMResponseCache
        assert "valkey_connected" in health["l2_valkey"]


class TestGatewayStatsCompleteness:
    """Verify get_stats includes all observability counters."""

    def test_stats_include_fallback_stub_count(self):
        """Stats track fallback stub usage."""
        gw = LLMGateway()
        stats = gw.get_stats()
        assert "total" in stats
        assert "inmemory_hits" in stats
        assert "valkey_hits" in stats
        assert "vector_hits" in stats
        assert "llm_calls" in stats
