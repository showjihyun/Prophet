"""vLLM distributed inference adapter.
SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#scale-targets
SPEC: docs/spec/05_LLM_SPEC.md

Assumes vLLM server is running at VLLM_BASE_URL with an OpenAI-compatible API.
Start vLLM: python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-3.1-8B
"""
import asyncio
import json
import time
from dataclasses import dataclass

import httpx

from app.llm.adapter import LLMAdapter
from app.llm.schema import (
    LLMPrompt,
    LLMOptions,
    LLMResponse,
    LLMTimeoutError,
    LLMProviderError,
)


class VLLMAdapter(LLMAdapter):
    """vLLM OpenAI-compatible API adapter for distributed inference.

    SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract

    vLLM provides:
    - Continuous batching (higher throughput than Ollama)
    - Tensor parallelism (multi-GPU)
    - PagedAttention (efficient KV cache)
    - OpenAI-compatible API (drop-in replacement)
    """
    provider_name = "vllm"

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        default_model: str = "meta-llama/Llama-3.1-8B-Instruct",
        max_concurrent: int = 64,
    ):
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def complete(
        self,
        prompt: LLMPrompt,
        options: LLMOptions | None = None,
    ) -> LLMResponse:
        """Call vLLM's OpenAI-compatible /v1/chat/completions endpoint.

        SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract
        """
        async with self._semaphore:
            return await self._complete_inner(prompt, options)

    async def _complete_inner(
        self,
        prompt: LLMPrompt,
        options: LLMOptions | None = None,
    ) -> LLMResponse:
        opts = options or LLMOptions()
        timeout = opts.timeout_seconds

        messages: list[dict[str, str]] = []
        if prompt.system:
            messages.append({"role": "system", "content": prompt.system})
        messages.append({"role": "user", "content": prompt.user})

        body: dict = {
            "model": self._default_model,
            "messages": messages,
            "max_tokens": prompt.max_tokens,
            "temperature": opts.temperature,
        }
        if prompt.response_format == "json":
            body["response_format"] = {"type": "json_object"}

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    json=body,
                    timeout=timeout,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            raise LLMTimeoutError(f"vLLM timeout after {timeout}s")
        except Exception as e:
            raise LLMProviderError(f"vLLM error: {e}")

        latency_ms = (time.perf_counter() - start) * 1000
        choice = data["choices"][0]
        content = choice["message"]["content"]
        usage = data.get("usage", {})

        parsed = None
        if prompt.response_format == "json":
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = None

        return LLMResponse(
            provider="vllm",
            model=self._default_model,
            content=content,
            parsed=parsed,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=round(latency_ms, 1),
        )

    async def embed(self, text: str) -> list[float] | None:
        """Call vLLM's /v1/embeddings endpoint.

        SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/v1/embeddings",
                    json={"model": self._default_model, "input": text},
                    timeout=10.0,
                )
                resp.raise_for_status()
                data = resp.json()
                embedding = data["data"][0]["embedding"]
                return embedding[:768] if len(embedding) > 768 else embedding
        except Exception:
            return None

    async def health_check(self) -> bool:
        """Check vLLM server health via /health endpoint.

        SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._base_url}/health", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False

    async def batch_complete(
        self,
        prompts: list[LLMPrompt],
        options: LLMOptions | None = None,
    ) -> list[LLMResponse]:
        """Batch inference via concurrent requests.

        vLLM's continuous batching handles server-side optimization.
        """
        tasks = [self.complete(p, options) for p in prompts]
        return await asyncio.gather(*tasks)


__all__ = ["VLLMAdapter"]
