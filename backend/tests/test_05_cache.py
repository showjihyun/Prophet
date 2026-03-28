"""
Auto-generated from SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
SPEC Version: 0.1.1
Generated BEFORE implementation verification — tests define the contract.
"""
import pytest
import time
from uuid import uuid4

from app.llm.cache import LLMResponseCache
from app.llm.schema import LLMPrompt, LLMResponse


def _make_prompt(user: str = "hello") -> LLMPrompt:
    return LLMPrompt(system="sys", user=user)


def _make_response(content: str = '{"score": 0.5}', cached: bool = False) -> LLMResponse:
    return LLMResponse(
        provider="mock",
        model="mock-1.0",
        content=content,
        parsed={"score": 0.5},
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=10.0,
        cached=cached,
    )


@pytest.mark.phase5
class TestCacheKey:
    """SPEC: 05_LLM_SPEC.md#6-llm-response-cache-valkey — cache key generation"""

    def test_cache_key_is_sha256(self):
        cache = LLMResponseCache()
        key = cache.cache_key(_make_prompt(), "mock", "mock-1.0")
        assert isinstance(key, str)
        assert len(key) == 64  # SHA256 hex digest length

    def test_same_prompt_same_key(self):
        cache = LLMResponseCache()
        p = _make_prompt("same content")
        k1 = cache.cache_key(p, "mock", "mock-1.0")
        k2 = cache.cache_key(p, "mock", "mock-1.0")
        assert k1 == k2

    def test_different_prompt_different_key(self):
        cache = LLMResponseCache()
        k1 = cache.cache_key(_make_prompt("content A"), "mock", "mock-1.0")
        k2 = cache.cache_key(_make_prompt("content B"), "mock", "mock-1.0")
        assert k1 != k2

    def test_different_provider_different_key(self):
        cache = LLMResponseCache()
        p = _make_prompt()
        k1 = cache.cache_key(p, "ollama", "llama3.2")
        k2 = cache.cache_key(p, "claude", "sonnet")
        assert k1 != k2


@pytest.mark.phase5
class TestCacheGetSet:
    """SPEC: 05_LLM_SPEC.md#6-llm-response-cache-valkey — get/set operations"""

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self):
        cache = LLMResponseCache()
        result = await cache.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_then_get(self):
        cache = LLMResponseCache()
        response = _make_response()
        await cache.set("key1", response)
        result = await cache.get("key1")
        assert result is not None
        assert result.content == response.content

    @pytest.mark.asyncio
    async def test_set_with_ttl_expires(self):
        cache = LLMResponseCache()
        response = _make_response()
        await cache.set("key_ttl", response, ttl=0)  # expires immediately
        # Allow time for expiry
        time.sleep(0.01)
        result = await cache.get("key_ttl")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_overwrites_existing(self):
        cache = LLMResponseCache()
        r1 = _make_response(content="first")
        r2 = _make_response(content="second")
        await cache.set("key_ow", r1)
        await cache.set("key_ow", r2)
        result = await cache.get("key_ow")
        assert result is not None
        assert result.content == "second"


@pytest.mark.phase5
class TestCacheInvalidation:
    """SPEC: 05_LLM_SPEC.md#6-llm-response-cache-valkey — simulation invalidation"""

    @pytest.mark.asyncio
    async def test_invalidate_simulation_clears_entries(self):
        cache = LLMResponseCache()
        sim_id = uuid4()
        response = _make_response()
        await cache.set("sim_key_1", response, simulation_id=str(sim_id))
        await cache.set("sim_key_2", response, simulation_id=str(sim_id))

        await cache.invalidate_simulation(sim_id)

        assert await cache.get("sim_key_1") is None
        assert await cache.get("sim_key_2") is None

    @pytest.mark.asyncio
    async def test_invalidate_does_not_affect_other_simulations(self):
        cache = LLMResponseCache()
        sim_a = uuid4()
        sim_b = uuid4()
        response = _make_response()
        await cache.set("key_a", response, simulation_id=str(sim_a))
        await cache.set("key_b", response, simulation_id=str(sim_b))

        await cache.invalidate_simulation(sim_a)

        assert await cache.get("key_a") is None
        assert await cache.get("key_b") is not None

    @pytest.mark.asyncio
    async def test_invalidate_nonexistent_simulation_is_noop(self):
        cache = LLMResponseCache()
        await cache.invalidate_simulation(uuid4())  # should not raise
