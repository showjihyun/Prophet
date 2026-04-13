"""OpenAI-compatible adapter for third-party providers (DeepSeek, Qwen, Moonshot).

SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

Many modern providers ship an OpenAI-compatible HTTP surface. Rather than
duplicate the full OpenAI client for each, we parameterize a single adapter
by ``provider_name``, ``base_url``, and ``default_model``. Subclasses pin the
defaults so registration in ``deps.py`` stays symmetric with the first-party
adapters (Claude / OpenAI / Gemini).

Providers wired in ``deps.py``:
  - DeepSeek     (https://api.deepseek.com)
  - Qwen         (https://dashscope-intl.aliyuncs.com/compatible-mode/v1)
  - Moonshot Kimi (https://api.moonshot.ai/v1)

Embeddings are intentionally not implemented — these providers either don't
expose an embedding endpoint in their OpenAI-compatible surface, or the
dimensions don't match our 768-dim pgvector schema. Ollama/OpenAI/Gemini
remain the embedding providers.
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


class OpenAICompatibleAdapter(LLMAdapter):
    """Generic adapter for OpenAI-compatible chat completions APIs.

    SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations
    """

    # Subclasses override these four class attributes.
    provider_name: str = "openai-compatible"
    default_base_url: str = ""
    default_model: str = ""
    display_name: str = "OpenAI-Compatible"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        default_model: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url or self.default_base_url
        self._default_model = default_model or self.default_model

    async def complete(
        self,
        prompt: LLMPrompt,
        options: LLMOptions | None = None,
    ) -> LLMResponse:
        """Call the provider's OpenAI-compatible chat completions endpoint."""
        import openai

        opts = options or LLMOptions()
        client = openai.AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)

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
                            f"Invalid JSON from {self.provider_name}: {exc}"
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
                    f"{self.provider_name} timeout after {opts.timeout_seconds}s"
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
                    f"{self.provider_name} rate limited: {exc}",
                    retry_after=retry_after,
                ) from exc
            except openai.AuthenticationError as exc:
                raise LLMAuthError(f"{self.provider_name} auth error: {exc}") from exc
            except Exception as exc:
                last_error = exc
                if attempt < opts.retry_count:
                    await asyncio.sleep(opts.retry_delay_seconds)
                    continue
                raise LLMProviderError(
                    f"{self.provider_name} error: {exc}"
                ) from exc

        raise LLMProviderError(
            f"{self.provider_name} request failed after retries: {last_error}"
        )

    async def embed(self, text: str) -> list[float] | None:
        """Not supported — these providers don't expose a compatible 768-dim embed endpoint."""
        return None

    async def health_check(self) -> bool:
        """Check reachability via models.list()."""
        import openai

        try:
            client = openai.AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
            await client.models.list()
            return True
        except Exception:
            return False


class DeepSeekAdapter(OpenAICompatibleAdapter):
    """DeepSeek (api.deepseek.com) — OpenAI-compatible chat API.

    Models: deepseek-chat (V3 series), deepseek-reasoner (R1-style reasoning).
    """

    provider_name = "deepseek"
    default_base_url = "https://api.deepseek.com"
    default_model = "deepseek-chat"
    display_name = "DeepSeek"


class QwenAdapter(OpenAICompatibleAdapter):
    """Alibaba Qwen (DashScope) — OpenAI-compatible mode.

    International endpoint is used by default; swap to
    ``https://dashscope.aliyuncs.com/compatible-mode/v1`` for mainland access.
    Models (2026-04): qwen3-max (flagship), qwen3.5-plus, qwen3.5-flash.
    """

    provider_name = "qwen"
    default_base_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    default_model = "qwen3-max"
    display_name = "Qwen (Alibaba)"


class MoonshotAdapter(OpenAICompatibleAdapter):
    """Moonshot AI Kimi — OpenAI-compatible chat API.

    Models (2026-04): kimi-k2.5 (flagship, 256K ctx, Agent Swarm),
    moonshot-v1-8k / 32k / 128k (legacy).
    ``.cn`` endpoint for mainland; ``.ai`` for international.
    """

    provider_name = "moonshot"
    default_base_url = "https://api.moonshot.ai/v1"
    default_model = "kimi-k2.5"
    display_name = "Moonshot (Kimi)"


class ZhipuGLMAdapter(OpenAICompatibleAdapter):
    """Zhipu AI GLM (BigModel / Z.ai) — OpenAI-compatible chat API.

    Models (2026-04): glm-5.1 (flagship, agentic coding, 200K ctx),
    glm-5, glm-4.6, glm-4-flash.
    Mainland endpoint: ``https://open.bigmodel.cn/api/paas/v4/``
    International: ``https://api.z.ai/api/paas/v4/``
    """

    provider_name = "glm"
    default_base_url = "https://open.bigmodel.cn/api/paas/v4/"
    default_model = "glm-5.1"
    display_name = "Zhipu GLM"


__all__ = [
    "OpenAICompatibleAdapter",
    "DeepSeekAdapter",
    "QwenAdapter",
    "MoonshotAdapter",
    "ZhipuGLMAdapter",
]
