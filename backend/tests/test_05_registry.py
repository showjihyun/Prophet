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

    def test_get_default_uses_env_var(self, monkeypatch):
        """DEFAULT_LLM_PROVIDER env var selects default adapter."""
        registry = LLMAdapterRegistry()
        adapter = _HealthyMockAdapter("claude")
        registry.register(adapter)
        monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "claude")
        result = registry.get_default()
        assert result is adapter

    def test_get_default_falls_back_to_ollama(self, monkeypatch):
        """Without env var, default is 'ollama'."""
        registry = LLMAdapterRegistry()
        adapter = _HealthyMockAdapter("ollama")
        registry.register(adapter)
        monkeypatch.delenv("DEFAULT_LLM_PROVIDER", raising=False)
        result = registry.get_default()
        assert result is adapter

    def test_get_default_raises_if_not_registered(self, monkeypatch):
        registry = LLMAdapterRegistry()
        monkeypatch.delenv("DEFAULT_LLM_PROVIDER", raising=False)
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
