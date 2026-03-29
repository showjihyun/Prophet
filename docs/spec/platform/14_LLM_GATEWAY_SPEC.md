# 14 — LLM Gateway & Vector Cache SPEC
Version: 0.1.0 | Status: DRAFT
Source: docs/spec/bench_mark/Ray Distribution 구조.txt

---

## 1. Overview

LLM Gateway는 모든 LLM 호출을 중앙에서 관리하는 레이어.
Agent 내부에서 직접 LLM을 호출하지 않고, Gateway를 통해 3단 캐시 + 모델 라우팅 + 배치 처리를 수행.

핵심 원칙: **"LLM을 호출하기 전에 3번 막고, 마지막에만 호출한다"**

```
Agent → LLM Gateway
         ├── 1. In-memory cache (shard-local, <1ms)
         ├── 2. Valkey cache (distributed, ~5ms)
         ├── 3. Vector cache (pgvector semantic, ~10ms)
         ├── 4. Smart model routing (cheap vs expensive)
         ├── 5. Batch queue (BATCH_SIZE=32)
         └── 6. Actual LLM call (last resort)
```

---

## 2. 3-Tier Cache Architecture

### Tier 1: In-Memory Cache (per-CommunityOrchestrator)

```python
class InMemoryLLMCache:
    """Shard-local cache within a community orchestrator.
    Ultra-fast, no network round-trip. TTL = 1 step (invalidated each step).
    """
    _cache: dict[str, LLMResponse]  # SHA256(prompt) → response
    MAX_SIZE: int = 1000            # LRU eviction

    def get(self, prompt_hash: str) -> LLMResponse | None: ...
    def set(self, prompt_hash: str, response: LLMResponse) -> None: ...
    def clear(self) -> None: ...    # called at step start
```

### Tier 2: Valkey Cache (distributed, existing)

Already implemented in `app/llm/cache.py`. TTL = `LLM_CACHE_TTL` (default 3600s).

### Tier 3: Vector Cache (pgvector semantic similarity)

```python
class VectorLLMCache:
    """Semantic cache using pgvector for similar-but-not-identical prompts.
    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#vector-cache

    If a new prompt is semantically similar (cosine > threshold) to a cached prompt,
    reuse the cached response instead of calling LLM.
    """
    SIMILARITY_THRESHOLD: float = 0.92  # cosine similarity threshold

    async def search(
        self,
        prompt_embedding: list[float],  # 768-dim
        task_type: str,                 # filter: same task type required
        top_k: int = 3,
    ) -> LLMResponse | None:
        """
        Search pgvector for semantically similar prompts.
        Returns cached response if similarity > threshold AND same task_type.
        Returns None if no match (proceed to actual LLM call).

        SQL:
            SELECT response, 1 - (embedding <=> $1) AS similarity
            FROM llm_vector_cache
            WHERE task_type = $2
            ORDER BY embedding <=> $1
            LIMIT $3
        """

    async def store(
        self,
        prompt: str,
        prompt_embedding: list[float],
        response: LLMResponse,
        task_type: str,
    ) -> None:
        """Store prompt+response with embedding for future semantic matching."""
```

---

## 3. LLM Gateway

```python
class LLMGateway:
    """Central LLM call manager with 3-tier cache + smart routing.
    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md

    All LLM calls from Agent engine go through this gateway.
    Agent layers NEVER call LLMAdapter directly.
    """

    def __init__(
        self,
        registry: LLMAdapterRegistry,
        inmemory_cache: InMemoryLLMCache,
        valkey_cache: LLMResponseCache,
        vector_cache: VectorLLMCache,
    ): ...

    async def call(
        self,
        prompt: LLMPrompt,
        task_type: str,           # "cognition" | "expert_analysis" | "reflection" | "embedding"
        tier: int = 3,            # requested tier (1=SLM, 2=heuristic, 3=LLM)
        options: LLMOptions | None = None,
    ) -> LLMResponse:
        """
        Smart LLM call with 3-tier cache chain.

        Flow:
            1. Hash prompt → check in-memory cache → HIT: return (0 cost)
            2. Hash prompt → check Valkey cache → HIT: return (0 cost)
            3. Embed prompt → search vector cache → HIT (sim > 0.92): return (0 cost)
            4. Route to model:
               - task_type "cognition" + tier 1 → SLM (cheap)
               - task_type "expert_analysis" → Elite LLM (expensive)
               - task_type "reflection" → SLM (cheap)
            5. Enqueue in batch queue → wait for batch execution
            6. Store result in all 3 cache tiers
            7. Return response

        Returns LLMResponse with `cached: bool` indicating cache hit.
        """

    async def flush_step_cache(self) -> None:
        """Clear in-memory cache at step start."""
```

---

## 4. Smart Model Router

```python
class ModelRouter:
    """Routes LLM calls to appropriate model based on task complexity.
    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#smart-model-router
    """

    ROUTING_TABLE = {
        "cognition_tier1": "slm",         # SLM: like/ignore/view decisions
        "cognition_tier2": "slm",         # SLM: heuristic with personality
        "cognition_tier3": "elite",       # Elite LLM: complex reasoning
        "expert_analysis": "elite",       # Always elite for expert agents
        "reflection": "slm",             # SLM: memory consolidation
        "embedding": "embed",            # Embedding model
    }

    def select_model(self, task_type: str, tier: int) -> str:
        key = f"{task_type}_tier{tier}" if tier else task_type
        return self.ROUTING_TABLE.get(key, "slm")
```

---

## 5. Event-Driven Agent Activation

```python
class EventDrivenActivation:
    """Only activate agents that have pending events.
    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#event-driven-activation

    Instead of ticking ALL agents every step, only tick agents that:
    1. Received new exposure (from RecSys feed)
    2. Received propagation event from neighbor
    3. Have pending group chat messages
    4. Are flagged for intervention

    Inactive agents are skipped entirely (0 cost, 0 latency).
    """

    def get_active_agents(
        self,
        all_agents: list[AgentState],
        exposure_results: dict[UUID, ExposureResult],
        propagation_events: list[PropagationEvent],
        interventions: list[UUID],
        base_activation_rate: float = 0.10,  # minimum 10% random activation
    ) -> list[AgentState]:
        """
        Returns only agents that should tick this step.

        Active if ANY of:
        - Has exposure_score > 0 from ExposureModel
        - Is target of a PropagationEvent
        - Has pending intervention
        - Random activation (base_activation_rate of remaining)

        Typical activation: 20-40% of total agents per step.
        """
```

---

## 6. Ray Actor Enhancement

```python
@ray.remote
class CommunityActor:
    """Ray Actor version of CommunityOrchestrator.
    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#ray-actor

    Unlike remote functions (stateless), Actors maintain state:
    - Agent states persist between steps (no serialization per step)
    - In-memory LLM cache persists within actor
    - Network subgraph loaded once, updated incrementally

    This is 3-5x faster than remote functions for multi-step simulations.
    """

    def __init__(self, community_id, config, agents, subgraph): ...

    def tick(self, step, events) -> CommunityTickResult:
        """Stateful tick — agents already loaded in actor memory."""

    def get_agents(self) -> list[AgentState]:
        """Return current agent states (for global aggregation)."""

    def apply_cross_community_events(self, events: list[PropagationEvent]) -> None:
        """Apply bridge propagation results from other communities."""
```

---

## 7. Cost Reduction Pipeline (full chain)

```
전체 요청 100%
  │
  ├── Activity vector skip (24h 비활성): -20%
  ├── Event-driven skip (이벤트 없음): -40%
  │   Active: ~40%
  │
  ├── In-memory cache hit: -10%
  ├── Valkey cache hit: -8%
  ├── Vector cache hit: -5%
  │   Need LLM: ~17%
  │
  ├── SLM routing (80% of LLM calls): ~14% → SLM (free)
  │   Elite LLM: ~3%
  │
  └── Batch processing: latency reduction only

  Final LLM cost: ~3% of naive approach (97% reduction)
```

---

## 8. Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| GW-01 | LLM Gateway 3-tier cache chain | In-memory → Valkey → Vector → LLM |
| GW-02 | Vector cache hit at similarity 0.93 | Returns cached response |
| GW-03 | Vector cache miss at similarity 0.85 | Calls actual LLM |
| GW-04 | Model router selects SLM for tier 1 | provider == "slm" |
| GW-05 | Model router selects elite for expert_analysis | provider == "elite" |
| GW-06 | Event-driven activation skips inactive agents | Active count < total |
| GW-07 | In-memory cache cleared between steps | Size == 0 after flush |
| GW-08 | Batch processing groups 32 prompts | Single batch call |
