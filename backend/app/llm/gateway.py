"""LLM Gateway — central LLM call manager with 3-tier cache + smart routing.
SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.config import settings as _settings
from app.llm.schema import LLMPrompt, LLMOptions, LLMResponse
from app.llm.registry import LLMAdapterRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tier 1: In-Memory LRU Cache (per-CommunityOrchestrator, TTL = 1 step)
# ---------------------------------------------------------------------------

class InMemoryLLMCache:
    """Shard-local in-memory cache. TTL = 1 step.

    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#inmemory-cache
    """

    MAX_SIZE = _settings.llm_inmemory_cache_max_size

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


# ---------------------------------------------------------------------------
# Tier 3: Vector Cache (pgvector semantic similarity)
# ---------------------------------------------------------------------------

class VectorLLMCache:
    """Semantic cache using pgvector cosine similarity.

    Uses PostgreSQL pgvector when a DB session factory is provided.
    Falls back to in-memory brute-force when no DB is available.

    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#vector-cache
    """
    SIMILARITY_THRESHOLD = _settings.llm_vector_similarity_threshold

    def __init__(self, session_factory: Any | None = None) -> None:
        self._session_factory = session_factory
        # In-memory fallback for tests / no-DB environments
        self._entries: list[dict] = []

    async def search(
        self, prompt_embedding: list[float], task_type: str, top_k: int = 3,
    ) -> LLMResponse | None:
        if not prompt_embedding:
            return None

        # Try pgvector path
        if self._session_factory is not None:
            return await self._search_pgvector(prompt_embedding, task_type, top_k)

        # Fallback: in-memory brute-force
        return self._search_inmemory(prompt_embedding, task_type)

    async def store(
        self, prompt: str, prompt_hash: str, prompt_embedding: list[float],
        response: LLMResponse, task_type: str,
    ) -> None:
        if not prompt_embedding:
            return

        # Try pgvector path
        if self._session_factory is not None:
            await self._store_pgvector(prompt, prompt_hash, prompt_embedding, response, task_type)
            return

        # Fallback: in-memory
        self._entries.append({
            "prompt": prompt, "embedding": prompt_embedding,
            "response": response, "task_type": task_type,
        })

    async def _search_pgvector(
        self, embedding: list[float], task_type: str, top_k: int,
    ) -> LLMResponse | None:
        try:
            async with self._session_factory() as session:
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                result = await session.execute(
                    text("""
                        SELECT response_json, provider, model,
                               1 - (embedding <=> :emb::vector) AS similarity
                        FROM llm_vector_cache
                        WHERE task_type = :task_type
                        ORDER BY embedding <=> :emb::vector
                        LIMIT :top_k
                    """),
                    {"emb": embedding_str, "task_type": task_type, "top_k": top_k},
                )
                row = result.first()
                if row and row.similarity >= self.SIMILARITY_THRESHOLD:
                    parsed = json.loads(row.response_json)
                    return LLMResponse(
                        provider=row.provider, model=row.model,
                        content=parsed.get("content", ""),
                        parsed=parsed.get("parsed"),
                        prompt_tokens=0, completion_tokens=0,
                        latency_ms=1.0, cached=True,
                    )
        except Exception as exc:
            logger.warning("VectorLLMCache pgvector search failed: %s", exc)
        return None

    async def _store_pgvector(
        self, prompt: str, prompt_hash: str, embedding: list[float],
        response: LLMResponse, task_type: str,
    ) -> None:
        try:
            async with self._session_factory() as session:
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                response_json = json.dumps({
                    "content": response.content,
                    "parsed": response.parsed,
                })
                await session.execute(
                    text("""
                        INSERT INTO llm_vector_cache
                            (prompt_hash, task_type, prompt_text, response_json,
                             provider, model, embedding)
                        VALUES (:hash, :task_type, :prompt, :response,
                                :provider, :model, :emb::vector)
                        ON CONFLICT (prompt_hash) DO UPDATE
                            SET response_json = EXCLUDED.response_json,
                                embedding = EXCLUDED.embedding
                    """),
                    {
                        "hash": prompt_hash, "task_type": task_type,
                        "prompt": prompt[:2000], "response": response_json,
                        "provider": response.provider, "model": response.model,
                        "emb": embedding_str,
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.warning("VectorLLMCache pgvector store failed: %s", exc)

    def _search_inmemory(
        self, prompt_embedding: list[float], task_type: str,
    ) -> LLMResponse | None:
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


# ---------------------------------------------------------------------------
# Model Router
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# LLM Gateway (3-tier cache chain)
# ---------------------------------------------------------------------------

class _BatchEntry:
    """A single item waiting in the batch queue."""

    def __init__(self, prompt: LLMPrompt, options: LLMOptions | None) -> None:
        self.prompt = prompt
        self.options = options
        self.future: asyncio.Future[LLMResponse] = asyncio.get_running_loop().create_future()


class LLMGateway:
    """Central LLM call manager. All agent LLM calls go through here.

    Cache chain: L1 InMemory → L2 Valkey → L3 pgvector → actual LLM call.
    Includes batch queue (BATCH_SIZE=32, MAX_WAIT_MS=100) and budget-aware
    model routing with fallback chain.

    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md
    """

    BATCH_SIZE: int = _settings.llm_gateway_batch_size
    MAX_WAIT_MS: int = _settings.llm_gateway_max_wait_ms
    VECTOR_SIMILARITY_THRESHOLD: float = _settings.llm_vector_similarity_threshold

    # Model tier downgrade order for budget-aware routing
    _TIER_DOWNGRADE: dict[int, int] = {3: 2, 2: 1, 1: 1}
    # Budget threshold — downgrade if remaining < this fraction of initial
    _BUDGET_DOWNGRADE_THRESHOLD: float = _settings.llm_budget_downgrade_threshold

    def __init__(
        self,
        registry: LLMAdapterRegistry | None = None,
        inmemory_cache: InMemoryLLMCache | None = None,
        valkey_cache: Any | None = None,
        vector_cache: VectorLLMCache | None = None,
        initial_budget_usd: float | None = None,
    ) -> None:
        self._registry = registry or LLMAdapterRegistry()
        self._inmemory = inmemory_cache or InMemoryLLMCache()
        self._valkey = valkey_cache  # LLMResponseCache instance (from cache.py)
        self._vector = vector_cache or VectorLLMCache()
        self._router = ModelRouter()
        self._initial_budget = initial_budget_usd
        self._stats: dict[str, int] = {
            "total": 0, "inmemory_hits": 0, "valkey_hits": 0,
            "vector_hits": 0, "llm_calls": 0, "batched_calls": 0,
            "budget_downgrades": 0,
        }
        # Batch queue
        self._batch_queue: list[_BatchEntry] = []
        self._batch_flush_task: asyncio.Task | None = None
        self._batch_lock = asyncio.Lock()

    async def call(
        self,
        prompt: LLMPrompt,
        task_type: str = "cognition",
        tier: int = 3,
        options: LLMOptions | None = None,
        prompt_embedding: list[float] | None = None,
        budget_remaining: float | None = None,
    ) -> LLMResponse:
        """Execute an LLM call with 3-tier cache chain.

        Flow:
            1. Hash prompt → L1 in-memory → HIT: return
            2. Hash prompt → L2 Valkey    → HIT: backfill L1, return
            3. Embed prompt → L3 pgvector → HIT: backfill L1, return
            4. Budget check → downgrade tier if budget low
            5. Route to model (with fallback chain)
            6. Enqueue in batch queue → wait for execution
            7. Store result in L1 + L2 + L3
            8. Return response

        SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#call-flow
        """
        self._stats["total"] += 1
        prompt_hash = self._hash_prompt(prompt)

        # --- Tier 1: In-memory (< 1ms) ---
        cached = self._inmemory.get(prompt_hash)
        if cached:
            self._stats["inmemory_hits"] += 1
            logger.debug("Gateway: L1 in-memory hit (hash=%s)", prompt_hash[:8])
            return cached

        # --- Tier 2: Valkey (~ 5ms) ---
        if self._valkey is not None:
            try:
                valkey_hit = await self._valkey.get(prompt_hash)
                if valkey_hit:
                    self._stats["valkey_hits"] += 1
                    self._inmemory.set(prompt_hash, valkey_hit)
                    logger.debug("Gateway: L2 Valkey hit (hash=%s)", prompt_hash[:8])
                    return LLMResponse(
                        provider=valkey_hit.provider, model=valkey_hit.model,
                        content=valkey_hit.content, parsed=valkey_hit.parsed,
                        prompt_tokens=valkey_hit.prompt_tokens,
                        completion_tokens=valkey_hit.completion_tokens,
                        latency_ms=5.0, cached=True,
                    )
            except Exception as exc:
                logger.warning("Valkey cache lookup failed: %s", exc)

        # --- Tier 3: Vector cache / pgvector (~ 10ms) ---
        if prompt_embedding:
            vcached = await self._vector.search(prompt_embedding, task_type)
            if vcached:
                self._stats["vector_hits"] += 1
                self._inmemory.set(prompt_hash, vcached)
                logger.debug("Gateway: L3 vector hit (hash=%s)", prompt_hash[:8])
                return vcached

        # --- Budget-aware tier downgrade ---
        effective_tier = self._apply_budget_downgrade(tier, budget_remaining)

        # --- No cache hit — route to model and call LLM ---
        model_type = self._router.select_model(task_type, effective_tier)
        self._stats["llm_calls"] += 1
        logger.debug(
            "Gateway: LLM call (hash=%s, task=%s, tier=%d, model=%s)",
            prompt_hash[:8], task_type, effective_tier, model_type,
        )

        response = await self._call_with_fallback(prompt, options, effective_tier)

        # --- Store in all cache tiers ---
        self._inmemory.set(prompt_hash, response)
        if self._valkey is not None:
            try:
                await self._valkey.set(prompt_hash, response)
            except Exception as exc:
                logger.warning("Valkey cache store failed: %s", exc)
        if prompt_embedding:
            await self._vector.store(
                prompt.user, prompt_hash, prompt_embedding, response, task_type,
            )

        return response

    async def call_batched(
        self,
        prompt: LLMPrompt,
        options: LLMOptions | None = None,
    ) -> LLMResponse:
        """Enqueue prompt in batch queue and await execution.

        Batch is flushed when BATCH_SIZE is reached OR after MAX_WAIT_MS.
        Used for Tier 1 SLM mass-agent processing.

        SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#batch-queue
        """
        entry = _BatchEntry(prompt, options)

        async with self._batch_lock:
            self._batch_queue.append(entry)
            queue_len = len(self._batch_queue)

            # Start the timer flush task if not already running
            if self._batch_flush_task is None or self._batch_flush_task.done():
                self._batch_flush_task = asyncio.create_task(
                    self._schedule_flush()
                )

            should_flush_now = queue_len >= self.BATCH_SIZE

        if should_flush_now:
            await self._flush_batch()

        # Wait for the future to be resolved by the flush
        return await entry.future

    async def _schedule_flush(self) -> None:
        """Wait MAX_WAIT_MS then flush remaining batch."""
        await asyncio.sleep(self.MAX_WAIT_MS / 1000.0)
        await self._flush_batch()

    async def _flush_batch(self) -> None:
        """Drain current batch queue and execute all pending prompts."""
        async with self._batch_lock:
            if not self._batch_queue:
                return
            batch = self._batch_queue[:self.BATCH_SIZE]
            self._batch_queue = self._batch_queue[self.BATCH_SIZE:]

        if not batch:
            return

        self._stats["batched_calls"] += len(batch)
        logger.debug("Gateway: flushing batch of %d prompts", len(batch))

        # Try SLM batch inferencer first
        slm_responses: list[LLMResponse] | None = None
        try:
            slm = self._registry.get_slm()
            slm_responses = await slm.batch_complete(
                [e.prompt for e in batch],
                batch[0].options,
            )
        except Exception as exc:
            logger.warning("SLM batch_complete failed, falling back: %s", exc)

        for i, entry in enumerate(batch):
            try:
                if slm_responses and i < len(slm_responses):
                    result = slm_responses[i]
                else:
                    result = await self._call_with_fallback(entry.prompt, entry.options, tier=1)
                if not entry.future.done():
                    entry.future.set_result(result)
            except Exception as exc:
                if not entry.future.done():
                    entry.future.set_exception(exc)

    async def _call_with_fallback(
        self,
        prompt: LLMPrompt,
        options: LLMOptions | None,
        tier: int = 3,
    ) -> LLMResponse:
        """Call LLM with automatic fallback to cheaper model on failure.

        Fallback chain: primary adapter → next cheaper adapter → rule-engine.

        SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#fallback-chain
        """
        # Try primary adapter (use SLM batch inferencer for tier 1/2)
        try:
            if tier <= 2:
                slm = self._registry.get_slm()
                responses = await slm.batch_complete([prompt])
                return responses[0]
            adapter = self._registry.get_default()
            return await adapter.complete(prompt, options)
        except Exception as primary_exc:
            logger.warning("Primary LLM adapter failed: %s — trying fallback", primary_exc)

        # Try healthy fallback adapter
        try:
            adapter = await self._registry.get_healthy()
            return await adapter.complete(prompt, options)
        except Exception as fallback_exc:
            logger.warning("Fallback LLM adapter failed: %s — using rule-engine", fallback_exc)

        # Last resort: rule-engine stub
        return LLMResponse(
            provider="fallback",
            model="rule-engine",
            content="{}",
            parsed={},
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=0,
        )

    def _apply_budget_downgrade(
        self, tier: int, budget_remaining: float | None,
    ) -> int:
        """Downgrade tier if budget is running low.

        If budget_remaining < 20% of initial_budget, downgrade tier by 1.

        SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#budget-routing
        """
        if budget_remaining is None or self._initial_budget is None:
            return tier
        if self._initial_budget <= 0:
            return tier
        fraction_remaining = budget_remaining / self._initial_budget
        if fraction_remaining < self._BUDGET_DOWNGRADE_THRESHOLD and tier > 1:
            new_tier = self._TIER_DOWNGRADE.get(tier, 1)
            self._stats["budget_downgrades"] += 1
            logger.info(
                "Gateway: budget %.1f%% remaining — downgrading tier %d → %d",
                fraction_remaining * 100, tier, new_tier,
            )
            return new_tier
        return tier

    async def flush_step_cache(self) -> None:
        """Clear in-memory cache at end of simulation step.

        SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#step-lifecycle
        """
        self._inmemory.clear()

    def get_stats(self) -> dict[str, int]:
        """Return cache hit/miss statistics.

        SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#stats
        """
        return dict(self._stats)

    def clear_cache(self, simulation_id: UUID | None = None) -> None:
        """Clear in-memory and (optionally) vector caches.

        When simulation_id is provided, clears only entries related to that
        simulation (Valkey invalidation is async — schedule separately).

        SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#cache-lifecycle
        """
        self._inmemory.clear()
        if simulation_id is None:
            # Clear full vector in-memory fallback store
            self._vector._entries.clear()
            logger.debug("Gateway: full cache cleared")
        else:
            logger.debug("Gateway: cache cleared for simulation %s", simulation_id)

    @property
    def stats(self) -> dict[str, int]:
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
