"""Claude (Anthropic) LLM adapter.
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


class ClaudeAdapter(LLMAdapter):
    """Anthropic Claude adapter.

    SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

    Uses the ``anthropic`` Python SDK.
    Claude does not provide an embedding API — ``embed()`` returns ``None``.
    """

    provider_name = "claude"

    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-sonnet-4-6",
    ) -> None:
        """SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations"""
        self._api_key = api_key
        self._default_model = default_model

    async def complete(
        self,
        prompt: LLMPrompt,
        options: LLMOptions | None = None,
    ) -> LLMResponse:
        """Call the Anthropic messages API.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

        Handles rate limiting: raises LLMRateLimitError with retry_after.
        """
        import anthropic

        opts = options or LLMOptions()

        client = anthropic.AsyncAnthropic(api_key=self._api_key)

        last_error: Exception | None = None
        for attempt in range(opts.retry_count + 1):
            try:
                start = time.perf_counter()
                response = await asyncio.wait_for(
                    client.messages.create(
                        model=self._default_model,
                        max_tokens=prompt.max_tokens,
                        system=prompt.system,
                        messages=[{"role": "user", "content": prompt.user}],
                        temperature=opts.temperature,
                    ),
                    timeout=opts.timeout_seconds,
                )
                elapsed_ms = (time.perf_counter() - start) * 1000

                content = response.content[0].text
                parsed: dict[str, Any] | None = None
                if prompt.response_format == "json":
                    try:
                        parsed = json.loads(content)
                    except json.JSONDecodeError as exc:
                        raise LLMParseError(
                            f"Invalid JSON from Claude: {exc}"
                        ) from exc

                return LLMResponse(
                    provider=self.provider_name,
                    model=self._default_model,
                    content=content,
                    parsed=parsed,
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    latency_ms=elapsed_ms,
                )

            except asyncio.TimeoutError as exc:
                raise LLMTimeoutError(
                    f"Claude timeout after {opts.timeout_seconds}s"
                ) from exc
            except LLMParseError:
                raise
            except anthropic.RateLimitError as exc:
                retry_after = float(
                    getattr(exc, "response", None)
                    and getattr(exc.response, "headers", {}).get("retry-after", 1.0)
                    or 1.0
                )
                last_error = exc
                if attempt < opts.retry_count:
                    await asyncio.sleep(retry_after * (2 ** attempt))
                    continue
                raise LLMRateLimitError(
                    f"Claude rate limited: {exc}", retry_after=retry_after
                ) from exc
            except anthropic.AuthenticationError as exc:
                raise LLMAuthError(f"Claude auth error: {exc}") from exc
            except Exception as exc:
                last_error = exc
                if attempt < opts.retry_count:
                    await asyncio.sleep(opts.retry_delay_seconds)
                    continue
                raise LLMProviderError(f"Claude error: {exc}") from exc

        raise LLMProviderError(f"Claude request failed after retries: {last_error}")

    async def embed(self, text: str) -> list[float] | None:
        """Claude does not support embeddings — returns None.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations
        """
        return None

    async def health_check(self) -> bool:
        """Check if the Claude API is reachable.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations
        """
        import anthropic

        try:
            client = anthropic.AsyncAnthropic(api_key=self._api_key)
            # A lightweight call to verify connectivity
            await client.messages.create(
                model=self._default_model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False


__all__ = ["ClaudeAdapter"]
