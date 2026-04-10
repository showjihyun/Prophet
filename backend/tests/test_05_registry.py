"""
Auto-generated from SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry
SPEC Version: 0.1.1
Generated BEFORE implementation verification — tests define the contract.
"""
import pytest
import os

from app.llm.registry import LLMAdapterRegistry, LLMProviderNotFoundError
from harness.mocks.mock_environment import MockLLMAdapter, MockSLMAdapter


class _HealthyMockAdapter(MockLLMAdapter):
    def __init__(self, name: str):
        super().__init__()
        self.provider_name = name

    async def health_check(self) -> bool:
        return True


class _UnhealthyMockAdapter(MockLLMAdapter):
    def __init__(self, name: str):
        super().__init__()
        self.provider_name = name

    async def health_check(self) -> bool:
        return False


@pytest.mark.phase5
class TestRegistryRegisterGet:
    """SPEC: 05_LLM_SPEC.md#4-llmadapterregistry — register/get"""

    def test_register_and_get(self):
        registry = LLMAdapterRegistry()
        adapter = _HealthyMockAdapter("test_provider")
        registry.register(adapter)
        result = registry.get("test_provider")
        assert result is adapter

    def test_get_unknown_raises(self):
        registry = LLMAdapterRegistry()
        with pytest.raises(LLMProviderNotFoundError):
            registry.get("nonexistent")

    def test_register_multiple(self):
        registry = LLMAdapterRegistry()
        a1 = _HealthyMockAdapter("p1")
        a2 = _HealthyMockAdapter("p2")
        registry.register(a1)
        registry.register(a2)
        assert registry.get("p1") is a1
        assert registry.get("p2") is a2

    def test_providers_list(self):
        registry = LLMAdapterRegistry()
        registry.register(_HealthyMockAdapter("a"))
        registry.register(_HealthyMockAdapter("b"))
        assert set(registry.providers) == {"a", "b"}


@pytest.mark.phase5
class TestRegistryGetDefault:
    """SPEC: 05_LLM_SPEC.md#4-llmadapterregistry — get_default"""

    def test_get_default_uses_settings(self, monkeypatch):
        """settings.default_llm_provider selects default adapter."""
        from app.config import settings
        registry = LLMAdapterRegistry()
        adapter = _HealthyMockAdapter("claude")
        registry.register(adapter)
        monkeypatch.setattr(settings, "default_llm_provider", "claude")
        result = registry.get_default()
        assert result is adapter

    def test_get_default_falls_back_to_ollama(self, monkeypatch):
        """Default provider is 'ollama'."""
        from app.config import settings
        registry = LLMAdapterRegistry()
        adapter = _HealthyMockAdapter("ollama")
        registry.register(adapter)
        monkeypatch.setattr(settings, "default_llm_provider", "ollama")
        result = registry.get_default()
        assert result is adapter

    def test_get_default_raises_if_not_registered(self, monkeypatch):
        from app.config import settings
        registry = LLMAdapterRegistry()
        monkeypatch.setattr(settings, "default_llm_provider", "ollama")
        with pytest.raises(LLMProviderNotFoundError):
            registry.get_default()


@pytest.mark.phase5
class TestRegistryGetHealthy:
    """SPEC: 05_LLM_SPEC.md#4-llmadapterregistry — get_healthy fallback"""

    @pytest.mark.asyncio
    async def test_returns_first_healthy(self):
        """Priority order: ollama > claude > openai."""
        registry = LLMAdapterRegistry()
        registry.register(_UnhealthyMockAdapter("ollama"))
        healthy_claude = _HealthyMockAdapter("claude")
        registry.register(healthy_claude)
        registry.register(_HealthyMockAdapter("openai"))
        result = await registry.get_healthy()
        assert result is healthy_claude

    @pytest.mark.asyncio
    async def test_returns_ollama_first_when_healthy(self):
        registry = LLMAdapterRegistry()
        ollama = _HealthyMockAdapter("ollama")
        registry.register(ollama)
        registry.register(_HealthyMockAdapter("claude"))
        result = await registry.get_healthy()
        assert result is ollama

    @pytest.mark.asyncio
    async def test_all_unhealthy_raises(self):
        registry = LLMAdapterRegistry()
        registry.register(_UnhealthyMockAdapter("ollama"))
        registry.register(_UnhealthyMockAdapter("claude"))
        with pytest.raises(LLMProviderNotFoundError):
            await registry.get_healthy()

    @pytest.mark.asyncio
    async def test_no_providers_raises(self):
        registry = LLMAdapterRegistry()
        with pytest.raises(LLMProviderNotFoundError):
            await registry.get_healthy()


@pytest.mark.phase5
class TestRegistrySLM:
    """SPEC: 05_LLM_SPEC.md#4-llmadapterregistry — get_slm"""

    def test_register_and_get_slm(self):
        registry = LLMAdapterRegistry()
        slm = MockSLMAdapter()
        registry.register_slm(slm)
        result = registry.get_slm()
        assert result is slm

    def test_get_slm_without_registration_raises(self):
        registry = LLMAdapterRegistry()
        with pytest.raises(LLMProviderNotFoundError):
            registry.get_slm()


@pytest.mark.phase5
class TestRegistryTierRouting:
    """SPEC: 05_LLM_SPEC.md#4 — _pick_adapter tier-aware routing."""

    def test_tier1_prefers_ollama(self):
        """Tier 1 picks Ollama even when elite providers are available."""
        registry = LLMAdapterRegistry()
        ollama = _HealthyMockAdapter("ollama")
        claude = _HealthyMockAdapter("claude")
        registry.register(ollama)
        registry.register(claude)
        result = registry._pick_adapter(tier=1)
        assert result is ollama

    def test_tier2_prefers_ollama(self):
        """Tier 2 picks Ollama (default/SLM path)."""
        registry = LLMAdapterRegistry()
        ollama = _HealthyMockAdapter("ollama")
        claude = _HealthyMockAdapter("claude")
        registry.register(ollama)
        registry.register(claude)
        result = registry._pick_adapter(tier=2)
        assert result is ollama

    def test_tier3_prefers_elite_claude(self):
        """Tier 3 picks Claude over Ollama when available."""
        registry = LLMAdapterRegistry()
        ollama = _HealthyMockAdapter("ollama")
        claude = _HealthyMockAdapter("claude")
        registry.register(ollama)
        registry.register(claude)
        result = registry._pick_adapter(tier=3)
        assert result is claude

    def test_tier3_prefers_claude_over_openai(self):
        """Tier 3 elite priority: Claude > OpenAI > Gemini."""
        registry = LLMAdapterRegistry()
        openai = _HealthyMockAdapter("openai")
        claude = _HealthyMockAdapter("claude")
        registry.register(openai)
        registry.register(claude)
        result = registry._pick_adapter(tier=3)
        assert result is claude

    def test_tier3_falls_back_to_openai(self):
        """Tier 3 falls back to OpenAI if Claude not available."""
        registry = LLMAdapterRegistry()
        ollama = _HealthyMockAdapter("ollama")
        openai = _HealthyMockAdapter("openai")
        registry.register(ollama)
        registry.register(openai)
        result = registry._pick_adapter(tier=3)
        assert result is openai

    def test_tier3_falls_back_to_ollama_if_no_elite(self):
        """Tier 3 falls back to Ollama if no elite providers registered."""
        registry = LLMAdapterRegistry()
        ollama = _HealthyMockAdapter("ollama")
        registry.register(ollama)
        result = registry._pick_adapter(tier=3)
        assert result is ollama

    def test_preferred_overrides_tier(self):
        """Explicit preferred adapter overrides tier-based selection."""
        registry = LLMAdapterRegistry()
        ollama = _HealthyMockAdapter("ollama")
        claude = _HealthyMockAdapter("claude")
        registry.register(ollama)
        registry.register(claude)
        result = registry._pick_adapter(tier=1, preferred="claude")
        assert result is claude

    def test_empty_registry_returns_none(self):
        """No adapters registered returns None."""
        registry = LLMAdapterRegistry()
        result = registry._pick_adapter(tier=3)
        assert result is None
