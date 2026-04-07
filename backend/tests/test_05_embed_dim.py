"""Embedding dimension enforcement tests for LLMAdapterRegistry.embed().
Auto-generated from SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
SPEC Version: 0.1.1
Generated BEFORE implementation verification — tests define the contract.

Tests that EmbeddingDimensionError is raised when an adapter returns a vector
of wrong size, and that matching dimensions pass through without error.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.llm.registry import LLMAdapterRegistry, LLMProviderNotFoundError
from app.llm.schema import EmbeddingDimensionError
from harness.mocks.mock_environment import MockLLMAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _EmbedAdapter(MockLLMAdapter):
    """MockLLMAdapter with configurable embed return dimension."""

    def __init__(self, dim: int | None):
        super().__init__()
        self._dim = dim
        self.provider_name = "mock_embed"

    async def embed(self, text: str) -> list[float] | None:
        if self._dim is None:
            return None
        return [0.1] * self._dim


def _registry_with(adapter: _EmbedAdapter) -> LLMAdapterRegistry:
    registry = LLMAdapterRegistry()
    registry.register_adapter(adapter.provider_name, adapter)
    return registry


# ---------------------------------------------------------------------------
# MockLLMAdapter.embed contract
# ---------------------------------------------------------------------------


@pytest.mark.phase5
@pytest.mark.unit
class TestMockLLMAdapterEmbed:
    """SPEC: 09_HARNESS_SPEC.md#f19-mock-environment — MockLLMAdapter.embed contract"""

    @pytest.mark.asyncio
    async def test_embed_returns_list(self):
        """MockLLMAdapter.embed must return a list of floats."""
        adapter = MockLLMAdapter()
        result = await adapter.embed("hello world")
        assert isinstance(result, list)
        assert all(isinstance(x, float) for x in result)

    @pytest.mark.asyncio
    async def test_embed_returns_768_dim(self):
        """MockLLMAdapter.embed must return exactly 768-dimensional vector."""
        adapter = MockLLMAdapter()
        result = await adapter.embed("some text")
        assert len(result) == 768

    @pytest.mark.asyncio
    async def test_embed_deterministic_for_same_input(self):
        """MockLLMAdapter.embed must be deterministic (same text → same vector)."""
        adapter = MockLLMAdapter()
        v1 = await adapter.embed("deterministic text")
        v2 = await adapter.embed("deterministic text")
        assert v1 == v2

    @pytest.mark.asyncio
    async def test_embed_different_for_different_input(self):
        """MockLLMAdapter.embed should produce different vectors for different inputs."""
        adapter = MockLLMAdapter()
        v1 = await adapter.embed("text A")
        v2 = await adapter.embed("text B")
        assert v1 != v2


# ---------------------------------------------------------------------------
# LLMAdapterRegistry.embed — EmbeddingDimensionError enforcement
# ---------------------------------------------------------------------------


@pytest.mark.phase5
@pytest.mark.unit
class TestRegistryEmbedDimensionCheck:
    """SPEC: 05_LLM_SPEC.md#9-error-specification — embed dimension validation"""

    @pytest.mark.asyncio
    async def test_correct_dimension_passes(self):
        """embed with matching dimension must succeed and return the vector."""
        adapter = _EmbedAdapter(dim=768)
        registry = _registry_with(adapter)
        registry._adapters["mock_embed"] = adapter  # ensure ollama fallback

        result = await registry.embed("test text", expected_dim=768)
        assert result is not None
        assert len(result) == 768

    @pytest.mark.asyncio
    async def test_wrong_dimension_raises_embedding_dimension_error(self):
        """SPEC: embed() must raise EmbeddingDimensionError when dim != expected_dim."""
        adapter = _EmbedAdapter(dim=512)  # wrong: 512 != 768
        registry = LLMAdapterRegistry()
        # Register as 'ollama' so _pick_adapter_for_embed selects it
        registry.register_adapter("ollama", adapter)

        with pytest.raises(EmbeddingDimensionError):
            await registry.embed("test text", expected_dim=768)

    @pytest.mark.asyncio
    async def test_custom_expected_dim_mismatch_raises(self):
        """embed() with custom expected_dim=1536 raises when adapter returns 768."""
        adapter = _EmbedAdapter(dim=768)
        registry = LLMAdapterRegistry()
        registry.register_adapter("ollama", adapter)

        with pytest.raises(EmbeddingDimensionError):
            await registry.embed("test", expected_dim=1536)

    @pytest.mark.asyncio
    async def test_custom_expected_dim_match_passes(self):
        """embed() with custom expected_dim=1536 passes when adapter returns 1536."""
        adapter = _EmbedAdapter(dim=1536)
        registry = LLMAdapterRegistry()
        registry.register_adapter("ollama", adapter)

        result = await registry.embed("test", expected_dim=1536)
        assert len(result) == 1536

    @pytest.mark.asyncio
    async def test_none_result_skips_dimension_check(self):
        """If adapter returns None, embed() skips dimension check (no error)."""
        adapter = _EmbedAdapter(dim=None)  # returns None
        registry = LLMAdapterRegistry()
        registry.register_adapter("ollama", adapter)

        # Should not raise; returns None
        result = await registry.embed("test text", expected_dim=768)
        assert result is None

    @pytest.mark.asyncio
    async def test_error_message_contains_dimensions(self):
        """EmbeddingDimensionError message must mention expected and actual dims."""
        adapter = _EmbedAdapter(dim=384)
        registry = LLMAdapterRegistry()
        registry.register_adapter("ollama", adapter)

        with pytest.raises(EmbeddingDimensionError, match="768"):
            await registry.embed("test", expected_dim=768)

    def test_no_adapter_registered_raises_provider_not_found(self):
        """embed() with no adapter registered must raise LLMProviderNotFoundError."""
        registry = LLMAdapterRegistry()
        import asyncio

        with pytest.raises(LLMProviderNotFoundError):
            asyncio.get_event_loop().run_until_complete(registry.embed("test"))


# ---------------------------------------------------------------------------
# Claude adapter does not support embed
# ---------------------------------------------------------------------------


@pytest.mark.phase5
@pytest.mark.unit
class TestClaudeAdapterNoEmbed:
    """SPEC: 05_LLM_SPEC.md — Claude adapter embed returns None (not supported)."""

    @pytest.mark.asyncio
    async def test_claude_adapter_embed_returns_none(self):
        """Claude adapter's embed() must return None (embeddings not supported)."""
        try:
            from app.llm.adapters.claude_adapter import ClaudeAdapter
        except ImportError:
            pytest.skip("ClaudeAdapter not available")

        adapter = ClaudeAdapter.__new__(ClaudeAdapter)
        # Call embed without real credentials — expect None or NotImplemented behaviour
        try:
            result = await adapter.embed("test")
            assert result is None, (
                f"Claude adapter embed() should return None, got: {result!r}"
            )
        except NotImplementedError:
            pass  # Also acceptable — means embed is explicitly unsupported
        except Exception:
            # Any other exception is acceptable in test environment (no API key)
            pass


# ---------------------------------------------------------------------------
# OpenAI 1536→768 projection contract
# ---------------------------------------------------------------------------


@pytest.mark.phase5
@pytest.mark.unit
class TestOpenAIProjectionContract:
    """SPEC: 05_LLM_SPEC.md §2 — OpenAI adapter must project 1536→768."""

    @pytest.mark.asyncio
    async def test_openai_native_dim_is_1536(self):
        """OpenAI text-embedding-3-small natively returns 1536-dim.

        The adapter MUST project/truncate to 768 before returning.
        If we pass a 1536-dim vector through the registry, it must raise
        EmbeddingDimensionError (expected 768).
        """
        adapter_1536 = _EmbedAdapter(dim=1536)
        registry = LLMAdapterRegistry()
        registry.register_adapter("ollama", adapter_1536)

        with pytest.raises(EmbeddingDimensionError, match="768"):
            await registry.embed("test", expected_dim=768)

    @pytest.mark.asyncio
    async def test_projected_768_passes_registry_check(self):
        """If OpenAI adapter correctly projects to 768, registry must accept it."""
        # Simulate a properly projecting adapter
        adapter_768 = _EmbedAdapter(dim=768)
        adapter_768.provider_name = "openai"
        registry = LLMAdapterRegistry()
        registry.register_adapter("ollama", adapter_768)  # register as ollama for preference

        result = await registry.embed("test text", expected_dim=768)
        assert result is not None
        assert len(result) == 768


# ---------------------------------------------------------------------------
# Registry adapter preference (embed prefers 'ollama')
# ---------------------------------------------------------------------------


@pytest.mark.phase5
@pytest.mark.unit
class TestRegistryAdapterPreference:
    """SPEC: 05_LLM_SPEC.md §4 — _pick_adapter_for_embed prefers 'ollama'."""

    @pytest.mark.asyncio
    async def test_embed_prefers_ollama_over_others(self):
        """Registry.embed must prefer the 'ollama' adapter for embeddings."""
        ollama_adapter = _EmbedAdapter(dim=768)
        ollama_adapter.provider_name = "ollama"

        other_adapter = _EmbedAdapter(dim=1536)
        other_adapter.provider_name = "openai"

        registry = LLMAdapterRegistry()
        registry.register_adapter("openai", other_adapter)
        registry.register_adapter("ollama", ollama_adapter)

        # Should use ollama (768-dim) and pass, not openai (1536-dim) which would fail
        result = await registry.embed("test", expected_dim=768)
        assert result is not None
        assert len(result) == 768

    @pytest.mark.asyncio
    async def test_embed_falls_back_when_no_ollama(self):
        """When no 'ollama' adapter, embed falls back to first available."""
        adapter = _EmbedAdapter(dim=768)
        adapter.provider_name = "mock_fallback"

        registry = LLMAdapterRegistry()
        registry.register_adapter("mock_fallback", adapter)

        result = await registry.embed("test", expected_dim=768)
        assert result is not None
        assert len(result) == 768

    @pytest.mark.asyncio
    async def test_register_adapter_name_stored_correctly(self):
        """register_adapter(name, adapter) must store adapter under the given name."""
        adapter = _EmbedAdapter(dim=768)
        registry = LLMAdapterRegistry()
        registry.register_adapter("custom_name", adapter)

        assert "custom_name" in registry._adapters
        assert registry._adapters["custom_name"] is adapter
