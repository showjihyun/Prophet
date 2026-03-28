"""Abstract LLM Adapter interface.
SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract
"""
from abc import ABC, abstractmethod

from app.llm.schema import LLMPrompt, LLMOptions, LLMResponse


class LLMAdapter(ABC):
    """Abstract base class for all LLM provider adapters.

    SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract

    All providers expose an identical interface.  Provider selection is
    per-simulation, per-community, or per-agent.
    """

    provider_name: str

    @abstractmethod
    async def complete(
        self,
        prompt: LLMPrompt,
        options: LLMOptions | None = None,
    ) -> LLMResponse:
        """Send prompt to LLM and return structured response.

        SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract

        Raises:
            LLMTimeoutError: Provider timeout.
            LLMRateLimitError: HTTP 429.
            LLMAuthError: HTTP 401/403.
            LLMProviderError: HTTP 5xx.
        """

    @abstractmethod
    async def embed(self, text: str) -> list[float] | None:
        """Generate 768-dim text embedding vector.

        SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract

        Returns None if embedding not supported (e.g. Claude).
        MUST return exactly 768-dim vector when supported.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Returns True if provider is reachable.

        SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract
        """


__all__ = ["LLMAdapter"]
