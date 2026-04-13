"""LLM Integration layer.
SPEC: docs/spec/05_LLM_SPEC.md
"""
from app.llm.schema import (
    LLMPrompt,
    LLMOptions,
    LLMResponse,
    LLMCallLog,
    TierDistribution,
    EngineImpactReport,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthError,
    LLMProviderError,
    LLMParseError,
    OllamaConnectionError,
    EmbeddingDimensionError,
    LLMTokenLimitError,
)
from app.llm.adapter import LLMAdapter
from app.llm.ollama_client import OllamaAdapter
from app.llm.claude_client import ClaudeAdapter
from app.llm.gemini_client import GeminiAdapter
from app.llm.openai_client import OpenAIAdapter
from app.llm.openai_compat import (
    OpenAICompatibleAdapter,
    DeepSeekAdapter,
    QwenAdapter,
    MoonshotAdapter,
    ZhipuGLMAdapter,
)
from app.llm.vllm_client import VLLMAdapter
from app.llm.slm_batch import SLMBatchInferencer
from app.llm.prompt_builder import PromptBuilder
from app.llm.cache import LLMResponseCache
from app.llm.registry import LLMAdapterRegistry, LLMProviderNotFoundError
from app.llm.quota import LLMQuotaManager
from app.llm.engine_control import EngineController
from app.llm.gateway import InMemoryLLMCache, VectorLLMCache, ModelRouter, LLMGateway

__all__ = [
    # Schema / Data types
    "LLMPrompt",
    "LLMOptions",
    "LLMResponse",
    "LLMCallLog",
    "TierDistribution",
    "EngineImpactReport",
    # Exceptions
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMAuthError",
    "LLMProviderError",
    "LLMParseError",
    "OllamaConnectionError",
    "EmbeddingDimensionError",
    "LLMTokenLimitError",
    "LLMProviderNotFoundError",
    # Adapters
    "LLMAdapter",
    "OllamaAdapter",
    "ClaudeAdapter",
    "GeminiAdapter",
    "OpenAIAdapter",
    "OpenAICompatibleAdapter",
    "DeepSeekAdapter",
    "QwenAdapter",
    "MoonshotAdapter",
    "ZhipuGLMAdapter",
    "VLLMAdapter",
    "SLMBatchInferencer",
    # Services
    "PromptBuilder",
    "LLMResponseCache",
    "LLMAdapterRegistry",
    "LLMQuotaManager",
    "EngineController",
    # Gateway
    "InMemoryLLMCache",
    "VectorLLMCache",
    "ModelRouter",
    "LLMGateway",
]
