"""Tests for LLM Gateway + Vector Cache + Event Activation.
SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md
"""
import pytest
from app.llm.gateway import InMemoryLLMCache, VectorLLMCache, ModelRouter, LLMGateway
from app.llm.schema import LLMPrompt, LLMResponse
from app.engine.simulation.event_activation import EventDrivenActivation


@pytest.mark.phase8
class TestInMemoryCache:
    def test_set_and_get(self):
        cache = InMemoryLLMCache()
        resp = LLMResponse(provider="test", model="m", content="ok", parsed=None,
                          prompt_tokens=10, completion_tokens=5, latency_ms=100)
        cache.set("abc", resp)
        hit = cache.get("abc")
        assert hit is not None
        assert hit.cached is True
        assert hit.content == "ok"

    def test_miss(self):
        cache = InMemoryLLMCache()
        assert cache.get("missing") is None

    def test_clear(self):
        cache = InMemoryLLMCache()
        cache.set("k", LLMResponse("p", "m", "c", None, 0, 0, 0))
        cache.clear()
        assert cache.size == 0

    def test_lru_eviction(self):
        cache = InMemoryLLMCache()
        cache.MAX_SIZE = 3
        for i in range(5):
            cache.set(f"k{i}", LLMResponse("p", "m", f"c{i}", None, 0, 0, 0))
        assert cache.size == 3


@pytest.mark.phase8
class TestVectorCache:
    @pytest.mark.asyncio
    async def test_store_and_search_hit(self):
        vc = VectorLLMCache()
        resp = LLMResponse("p", "m", "cached", None, 10, 5, 100)
        emb = [0.1] * 768
        await vc.store("test prompt", emb, resp, "cognition")
        hit = await vc.search(emb, "cognition")  # identical embedding = sim 1.0
        assert hit is not None
        assert hit.cached is True

    @pytest.mark.asyncio
    async def test_search_miss_different_task(self):
        vc = VectorLLMCache()
        resp = LLMResponse("p", "m", "cached", None, 10, 5, 100)
        emb = [0.1] * 768
        await vc.store("test", emb, resp, "cognition")
        hit = await vc.search(emb, "expert_analysis")  # wrong task type
        assert hit is None

    @pytest.mark.asyncio
    async def test_search_miss_low_similarity(self):
        vc = VectorLLMCache()
        resp = LLMResponse("p", "m", "cached", None, 10, 5, 100)
        await vc.store("test", [1.0] * 768, resp, "cognition")
        hit = await vc.search([-1.0] * 768, "cognition")  # opposite vector
        assert hit is None

    @pytest.mark.asyncio
    async def test_empty_cache_returns_none(self):
        vc = VectorLLMCache()
        assert await vc.search([0.1] * 768, "cognition") is None


@pytest.mark.phase8
class TestModelRouter:
    def test_tier1_cognition_routes_to_slm(self):
        router = ModelRouter()
        assert router.select_model("cognition", 1) == "slm"

    def test_tier3_cognition_routes_to_elite(self):
        router = ModelRouter()
        assert router.select_model("cognition", 3) == "elite"

    def test_expert_analysis_routes_to_elite(self):
        router = ModelRouter()
        assert router.select_model("expert_analysis", 3) == "elite"

    def test_reflection_routes_to_slm(self):
        router = ModelRouter()
        assert router.select_model("reflection", 1) == "slm"

    def test_unknown_defaults_to_slm(self):
        router = ModelRouter()
        assert router.select_model("unknown_task", 1) == "slm"


@pytest.mark.phase8
class TestLLMGateway:
    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(self):
        gw = LLMGateway()
        prompt = LLMPrompt(system="sys", user="test")
        # First call (cache miss -> LLM call or fallback)
        r1 = await gw.call(prompt, "cognition", 1)
        # Second call (cache hit)
        r2 = await gw.call(prompt, "cognition", 1)
        assert r2.cached is True
        assert gw.stats["inmemory_hits"] >= 1

    @pytest.mark.asyncio
    async def test_flush_clears_inmemory(self):
        gw = LLMGateway()
        prompt = LLMPrompt(system="s", user="u")
        await gw.call(prompt, "cognition", 1)
        await gw.flush_step_cache()
        assert gw._inmemory.size == 0

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        gw = LLMGateway()
        await gw.call(LLMPrompt(system="s", user="u1"), "cognition", 1)
        await gw.call(LLMPrompt(system="s", user="u2"), "cognition", 1)
        assert gw.stats["total"] == 2


@pytest.mark.phase8
class TestEventDrivenActivation:
    def _make_agents(self, n: int) -> list:
        from uuid import uuid4
        from app.engine.agent.schema import (
            AgentState, AgentPersonality, AgentEmotion, AgentAction, AgentType,
        )
        agents = []
        for _ in range(n):
            agents.append(AgentState(
                agent_id=uuid4(), simulation_id=uuid4(),
                agent_type=AgentType.CONSUMER,
                step=0, personality=AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5),
                emotion=AgentEmotion(0.5, 0.5, 0.5, 0.3), belief=0.0,
                action=AgentAction.IGNORE, exposure_count=0, adopted=False,
                community_id=uuid4(), influence_score=0.5, llm_tier_used=None,
            ))
        return agents

    def test_exposed_agents_active(self):
        agents = self._make_agents(10)
        # Only 3 agents have exposure
        exposure = {
            agents[0].agent_id: 0.5,
            agents[1].agent_id: 0.3,
            agents[2].agent_id: 0.1,
        }
        eda = EventDrivenActivation()
        active = eda.get_active_agents(agents, exposure_scores=exposure, seed=42)
        # At least the 3 exposed + some random
        assert len(active) >= 3
        assert len(active) < 10  # not all

    def test_zero_base_rate_only_event_agents(self):
        agents = self._make_agents(10)
        exposure = {agents[0].agent_id: 1.0}
        eda = EventDrivenActivation()
        active = eda.get_active_agents(
            agents, exposure_scores=exposure, base_activation_rate=0.0,
        )
        assert len(active) == 1

    def test_all_agents_active_if_all_exposed(self):
        agents = self._make_agents(5)
        exposure = {a.agent_id: 1.0 for a in agents}
        eda = EventDrivenActivation()
        active = eda.get_active_agents(agents, exposure_scores=exposure)
        assert len(active) == 5
