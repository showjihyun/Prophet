"""SLM Batch Inferencer for Tier 1 mass agent processing.
SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from app.llm.schema import (
    LLMPrompt,
    LLMOptions,
    LLMResponse,
    LLMParseError,
    OllamaConnectionError,
)

logger = logging.getLogger(__name__)


class SLMBatchInferencer:
    """Optimized batch inference for Tier 1 Mass SLM.

    SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

    Processes multiple agents in concurrent Ollama calls for throughput.
    Uses asyncio.gather for concurrent requests.

    Performance target: 1000 agents in < 2 seconds (batch_size=32, ~31 batches).
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        """SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations"""
        import ollama as _ollama
        from app.config import settings
        self._base_url = base_url or settings.ollama_base_url
        self._model = model or settings.slm_model
        self._batch_size = batch_size if batch_size is not None else settings.slm_batch_size
        self._client = _ollama.AsyncClient(host=self._base_url)

    async def _single_complete(
        self,
        prompt: LLMPrompt,
        opts: LLMOptions,
    ) -> LLMResponse:
        """Complete a single prompt against Ollama."""
        try:
            start = time.perf_counter()
            client = self._client

            kwargs: dict[str, Any] = {
                "model": self._model,
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
                except json.JSONDecodeError:
                    parsed = None

            return LLMResponse(
                provider="ollama-slm",
                model=self._model,
                content=content,
                parsed=parsed,
                prompt_tokens=response.get("prompt_eval_count", 0),
                completion_tokens=response.get("eval_count", 0),
                latency_ms=elapsed_ms,
            )
        except asyncio.TimeoutError:
            # Return a fallback response on timeout
            return LLMResponse(
                provider="ollama-slm",
                model=self._model,
                content=json.dumps({
                    "evaluation_score": 0.0,
                    "action": "ignore",
                    "reasoning": "SLM timeout",
                    "confidence": 0.0,
                }),
                parsed={
                    "evaluation_score": 0.0,
                    "action": "ignore",
                    "reasoning": "SLM timeout",
                    "confidence": 0.0,
                },
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=opts.timeout_seconds * 1000,
            )
        except Exception as exc:
            raise OllamaConnectionError(
                f"SLM batch inference failed: {exc}"
            ) from exc

    async def batch_complete(
        self,
        prompts: list[LLMPrompt],
        options: LLMOptions | None = None,
    ) -> list[LLMResponse]:
        """Send batch of prompts to Ollama for parallel processing.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

        Uses asyncio.gather for concurrent requests.
        Processes in chunks of batch_size.
        """
        opts = options or LLMOptions()
        results: list[LLMResponse] = []

        for i in range(0, len(prompts), self._batch_size):
            batch = prompts[i : i + self._batch_size]
            batch_results = await asyncio.gather(
                *(self._single_complete(p, opts) for p in batch),
                return_exceptions=False,
            )
            results.extend(batch_results)

        return results

    async def health_check(self) -> dict[str, Any]:
        """Returns model info + status.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations
        """
        try:
            models = await self._client.list()
            return {
                "model": self._model,
                "status": "ok",
                "available_models": [m.get("name", "") for m in models.get("models", [])],
            }
        except Exception as exc:
            return {
                "model": self._model,
                "status": "error",
                "error": str(exc),
            }


__all__ = ["SLMBatchInferencer"]
