"""OpenAI LLM adapter.
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
    LLMRateLimitError,
    LLMAuthError,
    LLMProviderError,
    LLMParseError,
)

logger = logging.getLogger(__name__)


class OpenAIAdapter(LLMAdapter):
    """OpenAI adapter using the async client.

    SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

    Supports chat completions and text embeddings.
    Embeddings are projected from 1536-dim to 768-dim for pgvector compatibility.
    """

    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-4o",
        embed_model: str = "text-embedding-3-small",
    ) -> None:
        """SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations"""
        self._api_key = api_key
        self._default_model = default_model
        self._embed_model = embed_model

    async def complete(
        self,
        prompt: LLMPrompt,
        options: LLMOptions | None = None,
    ) -> LLMResponse:
        """Call the OpenAI chat completions API.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

        response_format={"type": "json_object"} when prompt.response_format == "json".
        """
        import openai

        opts = options or LLMOptions()
        client = openai.AsyncOpenAI(api_key=self._api_key)

        last_error: Exception | None = None
        for attempt in range(opts.retry_count + 1):
            try:
                start = time.perf_counter()

                kwargs: dict[str, Any] = {
                    "model": self._default_model,
                    "messages": [
                        {"role": "system", "content": prompt.system},
                        {"role": "user", "content": prompt.user},
                    ],
                    "max_tokens": prompt.max_tokens,
                    "temperature": opts.temperature,
                }
                if prompt.response_format == "json":
                    kwargs["response_format"] = {"type": "json_object"}

                response = await asyncio.wait_for(
                    client.chat.completions.create(**kwargs),
                    timeout=opts.timeout_seconds,
                )
                elapsed_ms = (time.perf_counter() - start) * 1000

                content = response.choices[0].message.content or ""
                parsed: dict[str, Any] | None = None
                if prompt.response_format == "json":
                    try:
                        parsed = json.loads(content)
                    except json.JSONDecodeError as exc:
                        raise LLMParseError(
                            f"Invalid JSON from OpenAI: {exc}"
                        ) from exc

                usage = response.usage
                return LLMResponse(
                    provider=self.provider_name,
                    model=self._default_model,
                    content=content,
                    parsed=parsed,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=elapsed_ms,
                )

            except asyncio.TimeoutError as exc:
                raise LLMTimeoutError(
                    f"OpenAI timeout after {opts.timeout_seconds}s"
                ) from exc
            except LLMParseError:
                raise
            except openai.RateLimitError as exc:
                retry_after = 1.0 * (2 ** attempt)
                last_error = exc
                if attempt < opts.retry_count:
                    await asyncio.sleep(retry_after)
                    continue
                raise LLMRateLimitError(
                    f"OpenAI rate limited: {exc}", retry_after=retry_after
                ) from exc
            except openai.AuthenticationError as exc:
                raise LLMAuthError(f"OpenAI auth error: {exc}") from exc
            except Exception as exc:
                last_error = exc
                if attempt < opts.retry_count:
                    await asyncio.sleep(opts.retry_delay_seconds)
                    continue
                raise LLMProviderError(f"OpenAI error: {exc}") from exc

        raise LLMProviderError(f"OpenAI request failed after retries: {last_error}")

    async def embed(self, text: str) -> list[float] | None:
        """text-embedding-3-small (native 1536-dim) projected to 768-dim.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

        All providers MUST return 768-dim embeddings for pgvector compatibility.
        """
        import openai

        try:
            client = openai.AsyncOpenAI(api_key=self._api_key)
            response = await client.embeddings.create(
                model=self._embed_model,
                input=text,
            )
            embedding = response.data[0].embedding
            # Truncate from 1536-dim to 768-dim for pgvector schema
            return embedding[:768]
        except Exception as exc:
            raise LLMProviderError(f"OpenAI embedding failed: {exc}") from exc

    async def health_check(self) -> bool:
        """Check if the OpenAI API is reachable.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations
        """
        import openai

        try:
            client = openai.AsyncOpenAI(api_key=self._api_key)
            await client.models.list()
            return True
        except Exception:
            return False


__all__ = ["OpenAIAdapter"]
