"""LLM Gateway — central LLM call manager with 3-tier cache + smart routing.
SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md
"""
import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field

from app.llm.schema import LLMPrompt, LLMOptions, LLMResponse
from app.llm.registry import LLMAdapterRegistry


class InMemoryLLMCache:
    """Tier 1: Shard-local in-memory cache. TTL = 1 step.

    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#inmemory-cache
    """
    MAX_SIZE = 1000

    def __init__(self) -> None:
        self._cache: OrderedDict[str, LLMResponse] = OrderedDict()

    def get(self, prompt_hash: str) -> LLMResponse | None:
        if prompt_hash in self._cache:
            self._cache.move_to_end(prompt_hash)
            resp = self._cache[prompt_hash]
            return LLMResponse(
                provider=resp.provider, model=resp.model, content=resp.content,
                parsed=resp.parsed, prompt_tokens=resp.prompt_tokens,
                completion_tokens=resp.completion_tokens, latency_ms=0.1, cached=True,
            )
        return None

    def set(self, prompt_hash: str, response: LLMResponse) -> None:
        if len(self._cache) >= self.MAX_SIZE:
            self._cache.popitem(last=False)
        self._cache[prompt_hash] = response

    def clear(self) -> None:
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


class VectorLLMCache:
    """Tier 3: Semantic cache using pgvector-style cosine similarity.
    In-memory implementation for now (production: PostgreSQL pgvector).

    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#vector-cache
    """
    SIMILARITY_THRESHOLD = 0.92

    def __init__(self) -> None:
        self._entries: list[dict] = []  # {embedding, response, task_type, prompt}

    async def search(
        self, prompt_embedding: list[float], task_type: str, top_k: int = 3,
    ) -> LLMResponse | None:
        if not self._entries or not prompt_embedding:
            return None

        best_sim = 0.0
        best_response = None
        for entry in self._entries:
            if entry["task_type"] != task_type:
                continue
            sim = self._cosine_similarity(prompt_embedding, entry["embedding"])
            if sim > best_sim:
                best_sim = sim
                best_response = entry["response"]

        if best_sim >= self.SIMILARITY_THRESHOLD and best_response:
            return LLMResponse(
                provider=best_response.provider, model=best_response.model,
                content=best_response.content, parsed=best_response.parsed,
                prompt_tokens=0, completion_tokens=0, latency_ms=1.0, cached=True,
            )
        return None

    async def store(
        self, prompt: str, prompt_embedding: list[float],
        response: LLMResponse, task_type: str,
    ) -> None:
        self._entries.append({
            "prompt": prompt, "embedding": prompt_embedding,
            "response": response, "task_type": task_type,
        })

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @property
    def size(self) -> int:
        return len(self._entries)


class ModelRouter:
    """Routes LLM calls to appropriate model based on task + tier.

    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#model-router
    """
    ROUTING_TABLE: dict[str, str] = {
        "cognition_tier1": "slm",
        "cognition_tier2": "slm",
        "cognition_tier3": "elite",
        "expert_analysis": "elite",
        "reflection": "slm",
        "embedding": "embed",
    }

    def select_model(self, task_type: str, tier: int = 3) -> str:
        key = f"{task_type}_tier{tier}" if "tier" not in task_type else task_type
        return self.ROUTING_TABLE.get(key, self.ROUTING_TABLE.get(task_type, "slm"))


class LLMGateway:
    """Central LLM call manager. All agent LLM calls go through here.

    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md
    """

    def __init__(
        self,
        registry: LLMAdapterRegistry | None = None,
        inmemory_cache: InMemoryLLMCache | None = None,
        vector_cache: VectorLLMCache | None = None,
    ) -> None:
        self._registry = registry or LLMAdapterRegistry()
        self._inmemory = inmemory_cache or InMemoryLLMCache()
        self._vector = vector_cache or VectorLLMCache()
        self._router = ModelRouter()
        self._stats: dict[str, int] = {
            "total": 0, "inmemory_hits": 0, "vector_hits": 0, "llm_calls": 0,
        }

    async def call(
        self,
        prompt: LLMPrompt,
        task_type: str = "cognition",
        tier: int = 3,
        options: LLMOptions | None = None,
        prompt_embedding: list[float] | None = None,
    ) -> LLMResponse:
        """Execute an LLM call with 3-tier cache chain.

        SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#call-flow
        """
        self._stats["total"] += 1
        prompt_hash = self._hash_prompt(prompt)

        # Tier 1: In-memory
        cached = self._inmemory.get(prompt_hash)
        if cached:
            self._stats["inmemory_hits"] += 1
            return cached

        # Tier 3: Vector cache (skip Tier 2 Valkey in in-memory impl)
        if prompt_embedding:
            vcached = await self._vector.search(prompt_embedding, task_type)
            if vcached:
                self._stats["vector_hits"] += 1
                self._inmemory.set(prompt_hash, vcached)
                return vcached

        # Route to model
        model_type = self._router.select_model(task_type, tier)
        self._stats["llm_calls"] += 1

        # Call adapter (mock-safe)
        try:
            adapter = self._registry.get_default()
            response = await adapter.complete(prompt, options)
        except Exception:
            response = LLMResponse(
                provider="fallback", model="rule-engine", content="{}",
                parsed={}, prompt_tokens=0, completion_tokens=0, latency_ms=0,
            )

        # Store in caches
        self._inmemory.set(prompt_hash, response)
        if prompt_embedding:
            await self._vector.store(prompt.user, prompt_embedding, response, task_type)

        return response

    async def flush_step_cache(self) -> None:
        """Clear in-memory cache at end of simulation step.

        SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#step-lifecycle
        """
        self._inmemory.clear()

    @property
    def stats(self) -> dict[str, int]:
        """Return call statistics."""
        return dict(self._stats)

    @staticmethod
    def _hash_prompt(prompt: LLMPrompt) -> str:
        content = f"{prompt.system}|{prompt.user}"
        return hashlib.sha256(content.encode()).hexdigest()


__all__ = [
    "InMemoryLLMCache",
    "VectorLLMCache",
    "ModelRouter",
    "LLMGateway",
]
