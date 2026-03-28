"""Ollama LLM adapter (default local provider).
SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from app.llm.adapter import LLMAdapter
from app.llm.schema import (
    LLMPrompt,
    LLMOptions,
    LLMResponse,
    LLMTimeoutError,
    LLMProviderError,
    LLMParseError,
    OllamaConnectionError,
)

logger = logging.getLogger(__name__)


class OllamaAdapter(LLMAdapter):
    """Ollama local LLM adapter.

    SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

    Uses the ``ollama`` Python package for chat and embeddings.
    Default provider for Tier 1 (SLM) and Tier 3 (LLM) when running locally.
    """

    provider_name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.2",
        embed_model: str = "nomic-embed-text",
    ) -> None:
        """SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations"""
        self._base_url = base_url
        self._default_model = default_model
        self._embed_model = embed_model

    async def complete(
        self,
        prompt: LLMPrompt,
        options: LLMOptions | None = None,
    ) -> LLMResponse:
        """POST {base_url}/api/chat.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

        Timeout: options.timeout_seconds (default 10s).
        Retry: up to options.retry_count times on connection error.
        """
        import ollama as _ollama

        opts = options or LLMOptions()
        last_error: Exception | None = None

        for attempt in range(opts.retry_count + 1):
            try:
                start = time.perf_counter()
                client = _ollama.AsyncClient(host=self._base_url)

                kwargs: dict[str, Any] = {
                    "model": self._default_model,
                    "messages": [
                        {"role": "system", "content": prompt.system},
                        {"role": "user", "content": prompt.user},
                    ],
                    "stream": False,
                    "options": {"temperature": opts.temperature},
                }
                if prompt.response_format == "json":
                    kwargs["format"] = "json"

                response = await asyncio.wait_for(
                    client.chat(**kwargs),
                    timeout=opts.timeout_seconds,
                )
                elapsed_ms = (time.perf_counter() - start) * 1000

                content = response["message"]["content"]
                parsed: dict[str, Any] | None = None
                if prompt.response_format == "json":
                    try:
                        parsed = json.loads(content)
                    except json.JSONDecodeError as exc:
                        raise LLMParseError(f"Invalid JSON from Ollama: {exc}") from exc

                return LLMResponse(
                    provider=self.provider_name,
                    model=self._default_model,
                    content=content,
                    parsed=parsed,
                    prompt_tokens=response.get("prompt_eval_count", 0),
                    completion_tokens=response.get("eval_count", 0),
                    latency_ms=elapsed_ms,
                )

            except asyncio.TimeoutError as exc:
                raise LLMTimeoutError(
                    f"Ollama timeout after {opts.timeout_seconds}s"
                ) from exc
            except LLMParseError:
                raise
            except ConnectionError as exc:
                last_error = exc
                if attempt < opts.retry_count:
                    await asyncio.sleep(opts.retry_delay_seconds)
                    continue
                raise OllamaConnectionError(
                    f"Ollama unreachable at {self._base_url}: {exc}"
                ) from exc
            except Exception as exc:
                last_error = exc
                if attempt < opts.retry_count:
                    await asyncio.sleep(opts.retry_delay_seconds)
                    continue
                raise LLMProviderError(
                    f"Ollama error: {exc}"
                ) from exc

        # Should never reach here, but just in case
        raise LLMProviderError(f"Ollama request failed after retries: {last_error}")

    async def embed(self, text: str) -> list[float] | None:
        """POST {base_url}/api/embeddings — returns 768-dim vector.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations
        """
        import ollama as _ollama

        try:
            client = _ollama.AsyncClient(host=self._base_url)
            response = await client.embeddings(
                model=self._embed_model,
                prompt=text,
            )
            embedding = response["embedding"]
            return embedding[:768] if len(embedding) > 768 else embedding
        except Exception as exc:
            raise OllamaConnectionError(
                f"Ollama embedding failed: {exc}"
            ) from exc

    async def health_check(self) -> bool:
        """Check if Ollama server is reachable.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations
        """
        import ollama as _ollama

        try:
            client = _ollama.AsyncClient(host=self._base_url)
            await client.list()
            return True
        except Exception:
            return False


__all__ = ["OllamaAdapter"]
