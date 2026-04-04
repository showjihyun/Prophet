"""Google Gemini LLM adapter.
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

try:
    import google.generativeai as genai  # type: ignore[import]
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore[assignment]
    _GENAI_AVAILABLE = False

# Gemini embedding output dimension
_GEMINI_EMBED_DIM = 768
# Target dimension expected by the platform
_TARGET_EMBED_DIM = 768


class GeminiAdapter(LLMAdapter):
    """Google Gemini adapter.

    SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

    Uses the ``google-generativeai`` Python SDK.
    Supports both text generation and embeddings (768-dim).
    """

    provider_name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
    ) -> None:
        """SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations"""
        self._api_key = api_key
        self._model = model
        if _GENAI_AVAILABLE:
            genai.configure(api_key=api_key)

    async def complete(
        self,
        prompt: LLMPrompt,
        options: LLMOptions | None = None,
    ) -> LLMResponse:
        """Call the Gemini generate_content_async API.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

        Combines system + user into a single prompt string because the
        Gemini SDK treats the first turn as a user message.
        Handles rate limiting: raises LLMRateLimitError with retry_after.
        """
        if not _GENAI_AVAILABLE:
            raise LLMProviderError(
                "google-generativeai is not installed. "
                "Run: uv add google-generativeai"
            )

        opts = options or LLMOptions()
        full_prompt = f"{prompt.system}\n\n{prompt.user}" if prompt.system else prompt.user

        last_error: Exception | None = None
        for attempt in range(opts.retry_count + 1):
            try:
                generative_model = genai.GenerativeModel(self._model)

                start = time.perf_counter()
                response = await asyncio.wait_for(
                    generative_model.generate_content_async(
                        full_prompt,
                        generation_config=genai.GenerationConfig(
                            temperature=opts.temperature,
                            max_output_tokens=prompt.max_tokens,
                        ),
                    ),
                    timeout=opts.timeout_seconds,
                )
                elapsed_ms = (time.perf_counter() - start) * 1000

                content = response.text
                parsed: dict[str, Any] | None = None
                if prompt.response_format == "json":
                    # Strip markdown code fences if present
                    cleaned = content.strip()
                    if cleaned.startswith("```"):
                        lines = cleaned.splitlines()
                        # Drop first and last fence lines
                        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
                    try:
                        parsed = json.loads(cleaned)
                    except json.JSONDecodeError as exc:
                        raise LLMParseError(
                            f"Invalid JSON from Gemini: {exc}"
                        ) from exc

                usage = response.usage_metadata
                return LLMResponse(
                    provider=self.provider_name,
                    model=self._model,
                    content=content,
                    parsed=parsed,
                    prompt_tokens=usage.prompt_token_count if usage else 0,
                    completion_tokens=usage.candidates_token_count if usage else 0,
                    latency_ms=elapsed_ms,
                )

            except asyncio.TimeoutError as exc:
                raise LLMTimeoutError(
                    f"Gemini timeout after {opts.timeout_seconds}s"
                ) from exc
            except LLMParseError:
                raise
            except Exception as exc:
                exc_str = str(exc).lower()
                # Map Google API error messages to typed errors
                if "quota" in exc_str or "rate" in exc_str or "429" in exc_str:
                    last_error = exc
                    if attempt < opts.retry_count:
                        await asyncio.sleep(opts.retry_delay_seconds * (2 ** attempt))
                        continue
                    raise LLMRateLimitError(
                        f"Gemini rate limited: {exc}", retry_after=1.0
                    ) from exc
                if "api_key" in exc_str or "permission" in exc_str or "401" in exc_str or "403" in exc_str:
                    raise LLMAuthError(f"Gemini auth error: {exc}") from exc
                last_error = exc
                if attempt < opts.retry_count:
                    await asyncio.sleep(opts.retry_delay_seconds)
                    continue
                raise LLMProviderError(f"Gemini error: {exc}") from exc

        raise LLMProviderError(f"Gemini request failed after retries: {last_error}")

    async def embed(self, text: str) -> list[float] | None:
        """Generate a 768-dim embedding using Gemini embedding model.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations

        Projects to _TARGET_EMBED_DIM if the raw output differs.
        Returns None if the SDK is unavailable.
        """
        if not _GENAI_AVAILABLE:
            return None

        try:
            result = await asyncio.to_thread(
                genai.embed_content,
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document",
            )
            vector: list[float] = result["embedding"]

            # Project to target dimension if needed
            if len(vector) != _TARGET_EMBED_DIM:
                if len(vector) > _TARGET_EMBED_DIM:
                    vector = vector[:_TARGET_EMBED_DIM]
                else:
                    # Pad with zeros
                    vector = vector + [0.0] * (_TARGET_EMBED_DIM - len(vector))

            return vector
        except Exception as exc:
            logger.warning("Gemini embed failed: %s", exc)
            return None

    async def health_check(self) -> bool:
        """Check if the Gemini API is reachable by listing available models.

        SPEC: docs/spec/05_LLM_SPEC.md#3-provider-implementations
        """
        if not _GENAI_AVAILABLE:
            return False
        try:
            models = await asyncio.to_thread(list, genai.list_models())
            return len(models) > 0
        except Exception:
            return False


__all__ = ["GeminiAdapter"]
