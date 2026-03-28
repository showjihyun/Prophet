"""
Auto-generated from SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract
SPEC Version: 0.1.1 (updated: health_check must not make inference calls)
Generated BEFORE implementation verification — tests define the contract.
"""
import pytest

from app.llm.schema import LLMPrompt, LLMOptions, LLMResponse
from app.llm.adapter import LLMAdapter
from harness.mocks.mock_environment import MockLLMAdapter


@pytest.mark.phase5
class TestLLMAdapterInterface:
    """SPEC: 05_LLM_SPEC.md#2-llmadapter-interface-abstract"""

    def test_adapter_has_provider_name(self):
        """LLMAdapter subclass must expose provider_name."""
        adapter = MockLLMAdapter()
        assert hasattr(adapter, "provider_name")
        assert isinstance(adapter.provider_name, str)
        assert len(adapter.provider_name) > 0

    @pytest.mark.asyncio
    async def test_complete_returns_llm_response(self, mock_llm):
        """complete() must return an LLMResponse-like object."""
        prompt = LLMPrompt(system="test", user="hello")
        result = await mock_llm.complete(prompt)
        assert hasattr(result, "provider")
        assert hasattr(result, "model")
        assert hasattr(result, "content")
        assert hasattr(result, "parsed")
        assert hasattr(result, "prompt_tokens")
        assert hasattr(result, "completion_tokens")
        assert hasattr(result, "latency_ms")
        assert hasattr(result, "cached")

    @pytest.mark.asyncio
    async def test_complete_with_options(self, mock_llm):
        """complete() accepts LLMOptions."""
        prompt = LLMPrompt(system="sys", user="usr")
        opts = LLMOptions(temperature=0.5, timeout_seconds=5.0)
        result = await mock_llm.complete(prompt, opts)
        assert result.provider == "mock"

    @pytest.mark.asyncio
    async def test_embed_returns_768_dim_vector(self, mock_llm):
        """embed() must return 768-dim vector or None."""
        result = await mock_llm.embed("test text")
        assert result is None or (isinstance(result, list) and len(result) == 768)

    @pytest.mark.asyncio
    async def test_embed_returns_floats(self, mock_llm):
        """embed() vector elements must be floats."""
        result = await mock_llm.embed("test embedding")
        if result is not None:
            assert all(isinstance(x, float) for x in result)

    @pytest.mark.asyncio
    async def test_health_check_returns_bool(self, mock_llm):
        """health_check() must return bool."""
        result = await mock_llm.health_check()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_complete_tracks_call_count(self, mock_llm):
        """MockLLMAdapter tracks call count for testing."""
        prompt = LLMPrompt(system="s", user="u")
        assert mock_llm.call_count == 0
        await mock_llm.complete(prompt)
        assert mock_llm.call_count == 1
        await mock_llm.complete(prompt)
        assert mock_llm.call_count == 2

    @pytest.mark.asyncio
    async def test_complete_json_response_has_parsed(self, mock_llm):
        """When response_format='json', parsed dict should be populated."""
        prompt = LLMPrompt(system="s", user="u", response_format="json")
        result = await mock_llm.complete(prompt)
        assert result.parsed is not None
        assert isinstance(result.parsed, dict)


@pytest.mark.phase5
class TestLLMAdapterAbstract:
    """SPEC: 05_LLM_SPEC.md#2-llmadapter-interface-abstract — abstract base class"""

    def test_cannot_instantiate_abstract(self):
        """LLMAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMAdapter()

    def test_ollama_adapter_has_provider_name(self):
        """OllamaAdapter.provider_name == 'ollama'."""
        from app.llm.ollama_client import OllamaAdapter
        assert OllamaAdapter.provider_name == "ollama"

    def test_claude_adapter_has_provider_name(self):
        """ClaudeAdapter.provider_name == 'claude'."""
        from app.llm.claude_client import ClaudeAdapter
        assert ClaudeAdapter.provider_name == "claude"

    def test_openai_adapter_has_provider_name(self):
        """OpenAIAdapter.provider_name == 'openai'."""
        from app.llm.openai_client import OpenAIAdapter
        assert OpenAIAdapter.provider_name == "openai"


@pytest.mark.phase5
class TestHealthCheckNoInference:
    """SPEC: 05_LLM_SPEC.md#3-provider-implementations — health_check constraint.

    IMPORTANT: health_check MUST NOT make inference API calls.
    Use lightweight connectivity check only (e.g., HTTP HEAD to API endpoint,
    or client.models.list()). Inference calls consume API quota and budget.
    This applies to ALL adapters, not just Claude.
    """

    @pytest.mark.asyncio
    async def test_mock_health_check_does_not_increment_call_count(self):
        """health_check must not trigger inference (tracked via call_count)."""
        adapter = MockLLMAdapter()
        assert adapter.call_count == 0
        await adapter.health_check()
        # health_check should NOT increment call_count (inference tracker)
        assert adapter.call_count == 0

    @pytest.mark.asyncio
    async def test_health_check_returns_bool_not_response(self):
        """health_check returns bool, not LLMResponse (no inference)."""
        adapter = MockLLMAdapter()
        result = await adapter.health_check()
        assert isinstance(result, bool)
        assert not isinstance(result, LLMResponse)
