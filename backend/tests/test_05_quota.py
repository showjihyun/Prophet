"""
Auto-generated from SPEC: docs/spec/05_LLM_SPEC.md#7-quota--rate-management
SPEC Version: 0.1.1
Generated BEFORE implementation verification — tests define the contract.
"""
import pytest
import time
from uuid import uuid4

from app.llm.quota import LLMQuotaManager


@pytest.mark.phase5
class TestCanCallLLM:
    """SPEC: 05_LLM_SPEC.md#7-quota--rate-management — per-step budget"""

    def test_under_quota_returns_true(self):
        """Under 10% ratio → can call LLM."""
        mgr = LLMQuotaManager(tier3_ratio=0.10)
        result = mgr.can_call_llm(
            simulation_id=uuid4(), step=1,
            current_llm_call_count=5, total_agents=100,
        )
        assert result is True

    def test_at_quota_returns_false(self):
        """At exactly 10% ratio → cannot call (>= threshold)."""
        mgr = LLMQuotaManager(tier3_ratio=0.10)
        result = mgr.can_call_llm(
            simulation_id=uuid4(), step=1,
            current_llm_call_count=10, total_agents=100,
        )
        assert result is False

    def test_over_quota_returns_false(self):
        """Over 10% ratio → cannot call."""
        mgr = LLMQuotaManager(tier3_ratio=0.10)
        result = mgr.can_call_llm(
            simulation_id=uuid4(), step=1,
            current_llm_call_count=15, total_agents=100,
        )
        assert result is False

    def test_zero_agents_returns_false(self):
        """Zero total agents → cannot call (avoid division by zero)."""
        mgr = LLMQuotaManager()
        result = mgr.can_call_llm(
            simulation_id=uuid4(), step=1,
            current_llm_call_count=0, total_agents=0,
        )
        assert result is False

    def test_zero_calls_returns_true(self):
        """Zero calls so far → can call."""
        mgr = LLMQuotaManager()
        result = mgr.can_call_llm(
            simulation_id=uuid4(), step=1,
            current_llm_call_count=0, total_agents=100,
        )
        assert result is True

    def test_custom_ratio(self):
        """Custom tier3_ratio = 0.20."""
        mgr = LLMQuotaManager(tier3_ratio=0.20)
        # 15% < 20% → allowed
        assert mgr.can_call_llm(uuid4(), 1, 15, 100) is True
        # 20% >= 20% → blocked
        assert mgr.can_call_llm(uuid4(), 1, 20, 100) is False


@pytest.mark.phase5
class TestHandleRateLimit:
    """SPEC: 05_LLM_SPEC.md#7-quota--rate-management — rate limit handling"""

    @pytest.mark.asyncio
    async def test_handle_rate_limit_disables_provider(self):
        """After rate limit, provider is temporarily disabled."""
        mgr = LLMQuotaManager()
        await mgr.handle_rate_limit("claude", retry_after=2.0)
        assert mgr.is_provider_available("claude") is False

    @pytest.mark.asyncio
    async def test_provider_available_after_cooldown(self):
        """Provider becomes available after retry_after seconds."""
        mgr = LLMQuotaManager()
        await mgr.handle_rate_limit("claude", retry_after=0.01)
        time.sleep(0.02)
        assert mgr.is_provider_available("claude") is True

    def test_unaffected_provider_is_available(self):
        """Provider that was not rate limited is available."""
        mgr = LLMQuotaManager()
        assert mgr.is_provider_available("ollama") is True
