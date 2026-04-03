# 05 — LLM Integration SPEC
Version: 0.2.0 | Status: REVIEW

---

## 1. Overview

LLM integration follows the **Adapter Pattern** — all providers expose an identical `LLMAdapter` interface. Provider selection is per-simulation, per-community, or per-agent.

**Tier Architecture (must be honored):**
- **Tier 1** (Mass SLM): Local SLM via Ollama batch inference. ~50ms/agent, ~5ms batched.
- **Tier 2** (Heuristic): No LLM. Weighted formula.
- **Tier 3** (LLM Reasoning): Calls `LLMAdapter`. Max 10% agents per step.

Simulation MUST run to completion even if all external LLM providers fail (graceful degradation to Tier 1 SLM via local Ollama).

---

## 2. LLMAdapter Interface (Abstract)

```python
from abc import ABC, abstractmethod

class LLMAdapter(ABC):
    provider_name: str

    @abstractmethod
    async def complete(
        self,
        prompt: LLMPrompt,
        options: LLMOptions | None = None,
    ) -> LLMResponse:
        """
        Send prompt to LLM and return structured response.
        Raises LLMTimeoutError, LLMQuotaError, LLMAuthError on failures.
        """

    @abstractmethod
    async def embed(
        self,
        text: str,
    ) -> list[float]:
        """
        Generate text embedding vector.
        Used for pgvector memory storage.
        MUST return exactly 768-dim vector (pgvector schema constraint).
        If native model produces different dimensions (e.g. OpenAI 1536-dim),
        the adapter MUST project/truncate to 768-dim before returning.
        Returns None if embedding not supported (e.g. Claude).
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Returns True if provider is reachable."""

@dataclass
class LLMPrompt:
    system: str
    user: str
    context: dict[str, Any]      # structured context merged into prompt
    response_format: Literal["text", "json"] = "json"
    max_tokens: int = 512

@dataclass
class LLMOptions:
    temperature: float = 0.7
    timeout_seconds: float = 10.0
    retry_count: int = 3
    retry_delay_seconds: float = 1.0

@dataclass
class LLMResponse:
    provider: str
    model: str
    content: str
    parsed: dict[str, Any] | None   # populated when response_format == "json"
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cached: bool = False
```

---

## 3. Provider Implementations

### OllamaAdapter (Default)

```python
class OllamaAdapter(LLMAdapter):
    provider_name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.2",
    ): ...

    async def complete(self, prompt: LLMPrompt, options: LLMOptions | None = None) -> LLMResponse:
        """
        POST {base_url}/api/chat
        model: config.default_model (overridable per call)
        stream: False
        format: "json" if prompt.response_format == "json"

        Timeout: options.timeout_seconds (default 10s)
        Retry: up to options.retry_count times on connection error
        """

    async def embed(self, text: str) -> list[float]:
        """
        POST {base_url}/api/embeddings
        model: "nomic-embed-text" (default embedding model)
        Returns 768-dim vector.
        """
```

### SLM Batch Inference (Tier 1)

```python
class SLMBatchInferencer:
    """
    Optimized batch inference for Tier 1 Mass SLM.
    Processes multiple agents in a single Ollama call for throughput.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "phi4",          # or "llama3.2:8b-q4", "gemma2:2b"
        batch_size: int = 32,
    ): ...

    async def batch_complete(
        self,
        prompts: list[LLMPrompt],
        options: LLMOptions | None = None,
    ) -> list[LLMResponse]:
        """
        Sends batch of prompts to Ollama for parallel processing.
        Uses asyncio.gather for concurrent requests.

        SLM prompt is simplified vs Tier 3:
            System: "You are agent {id}, {type}. Personality: {vector}. Respond JSON only."
            User: "Content: {exposure}. Emotion: {current}. Choose action and explain briefly."

        Response format (JSON):
            {"evaluation_score": float, "action": str, "reasoning": str, "confidence": float}

        Performance target: 1000 agents in < 2 seconds (batch_size=32, ~31 batches)
        """

    async def health_check(self) -> dict[str, Any]:
        """Returns model info + GPU/CPU utilization."""
```

**Supported SLM models (Tier 1):**

| Model | Size | Quantization | Speed (tokens/s) | Use Case |
|-------|------|-------------|-------------------|----------|
| Phi-4 | 14B | Q4_K_M | ~30 t/s | Best quality, needs GPU |
| Llama-3-8B | 8B | Q4_K_M | ~50 t/s | Good balance |
| Gemma-2B | 2B | FP16 | ~100 t/s | Fastest, CPU-friendly |

### ClaudeAdapter

```python
class ClaudeAdapter(LLMAdapter):
    provider_name = "claude"

    def __init__(
        self,
        api_key: str,                    # from ANTHROPIC_API_KEY env
        default_model: str = "claude-sonnet-4-6",
    ): ...

    async def complete(self, prompt: LLMPrompt, options: LLMOptions | None = None) -> LLMResponse:
        """
        Uses anthropic Python SDK.
        messages=[{"role": "user", "content": prompt.user}]
        system=prompt.system
        max_tokens=prompt.max_tokens
        Handles rate limiting: raises LLMQuotaError with retry_after.
        """

    async def embed(self, text: str) -> list[float]:
        """
        Claude does not provide embedding API.
        Returns None — caller falls back to Ollama embed or skips vector indexing.
        """

    # IMPORTANT: health_check MUST NOT make inference API calls.
    # Use lightweight connectivity check only (e.g., HTTP HEAD to API endpoint,
    # or client.models.list()). Inference calls consume API quota and budget.
    # This applies to ALL adapters, not just Claude.
```

### OpenAIAdapter

```python
class OpenAIAdapter(LLMAdapter):
    provider_name = "openai"

    def __init__(
        self,
        api_key: str,                    # from OPENAI_API_KEY env
        default_model: str = "gpt-4o",
    ): ...

    async def complete(self, prompt: LLMPrompt, options: LLMOptions | None = None) -> LLMResponse:
        """
        Uses openai Python SDK (async client).
        response_format={"type": "json_object"} when prompt.response_format == "json"
        """

    async def embed(self, text: str) -> list[float]:
        """
        model: text-embedding-3-small (native: 1536-dim)
        Returns 768-dim vector (projected via PCA/truncation to match pgvector schema).
        All providers MUST return 768-dim embeddings for pgvector compatibility.
        """
```

---

## 4. LLMAdapterRegistry

```python
class LLMAdapterRegistry:
    """
    Manages available providers. Simulation config specifies default.
    Individual agents can override via agent.llm_provider.
    """

    def register(self, adapter: LLMAdapter) -> None: ...

    def get(self, provider_name: str) -> LLMAdapter:
        """Raises LLMProviderNotFoundError if not registered."""

    def get_default(self) -> LLMAdapter:
        """Returns adapter for DEFAULT_LLM_PROVIDER env var."""

    async def get_healthy(self) -> LLMAdapter:
        """
        Returns first healthy provider from priority list:
        [ollama, vllm, claude, openai]
        Used for fallback when primary is unavailable.
        """

    def get_slm(self) -> SLMBatchInferencer:
        """Returns the Tier 1 SLM batch inferencer (always local Ollama)."""

    def register_adapter(self, adapter: LLMAdapter) -> None:
        """Register a new adapter instance by its provider_name."""

    async def evaluate(self, prompt: LLMPrompt, options: LLMOptions) -> LLMResponse:
        """Full tier-fallback chain convenience method."""

    async def embed(self, text: str) -> list[float]:
        """Embedding via registry (delegates to default adapter)."""
```

### Provider Fallback Priority

```python
_PROVIDER_PRIORITY = ["ollama", "vllm", "claude", "openai"]
```

---

## 5. Prompt Builder

```python
class PromptBuilder:
    def build_agent_cognition_prompt(
        self,
        agent: AgentState,
        perception: PerceptionResult,
        memories: list[MemoryRecord],
        campaign: Campaign,
    ) -> LLMPrompt:
        """
        System:
            "You are simulating agent {agent_id}, a {agent_type} in community {community_name}.
             Your personality: openness={openness}, skepticism={skepticism}, ...
             Respond ONLY in JSON with keys: evaluation_score, recommended_action, reasoning, confidence"

        User:
            "You have been exposed to: {campaign.message}
             Your recent memories: {top_3_memories}
             Your current emotion: interest={interest}, trust={trust}, ...
             Your neighbors' actions: {neighbor_action_summary}

             Evaluate this content and decide your action.
             Actions available: {AgentAction values}
             evaluation_score: float from -2.0 to 2.0
             confidence: float from 0.0 to 1.0"
        """

    def build_expert_analysis_prompt(
        self,
        expert: AgentState,
        campaign: Campaign,
        sentiment: CommunitySentiment,
        memories: list[MemoryRecord],
    ) -> LLMPrompt:
        """
        System:
            "You are an expert analyst (role: {expert_role}).
             Analyze the following product/campaign objectively.
             Respond in JSON: score (float -1 to 1), reasoning (str), confidence (float)"

        User:
            "Campaign: {campaign.name} - {campaign.message}
             Current community sentiment: {sentiment.mean_belief}
             Adoption rate: {sentiment.adoption_rate}
             Key community feedback: {top_memories_summary}"
        """

    def build_memory_reflection_prompt(
        self,
        agent: AgentState,
        recent_events: list[MemoryRecord],
    ) -> LLMPrompt:
        """
        Triggered when repeated_event_count > threshold (default: 5 similar memories).
        Generates high-level belief update.

        User:
            "You have experienced these events multiple times: {events_summary}
             What conclusion do you draw? Update your belief on the product/campaign.
             Respond in JSON: belief_delta (float -0.5 to 0.5), insight (str)"
        """
```

---

## 6. LLM Response Cache (Valkey)

```python
class LLMResponseCache:
    """
    Caches LLM responses in Valkey to reduce cost in Monte Carlo runs
    and repeated scenarios.
    """

    def cache_key(
        self,
        prompt: LLMPrompt,
        provider: str,
        model: str,
    ) -> str:
        """SHA256 hash of (provider + model + system + user content)"""

    async def get(self, key: str) -> LLMResponse | None: ...

    async def set(
        self,
        key: str,
        response: LLMResponse,
        ttl: int = 3600,
    ) -> None: ...

    async def invalidate_simulation(self, simulation_id: UUID) -> None:
        """Clear all cache entries for a simulation (e.g., on agent modification)."""
```

### 6.2 Multi-tier Cache (LLMGateway)

```python
# backend/app/llm/gateway.py
class LLMGateway:
    """Central LLM call manager with 3-tier cache + smart routing.
    @spec docs/spec/platform/14_LLM_GATEWAY_SPEC.md
    """

class InMemoryLLMCache:
    """L1 cache: in-memory LRU. Fastest, volatile."""

class VectorLLMCache:
    """L2 cache: pgvector semantic similarity. Matches similar (not identical) prompts."""
```

Cache lookup order: L1 (InMemoryLLMCache) → L2 (VectorLLMCache) → L3 (LLMResponseCache/Valkey)

---

### 6.3 vLLM Adapter

```python
# backend/app/llm/vllm_client.py
class VLLMAdapter(LLMAdapter):
    """vLLM distributed inference adapter.
    provider_name = "vllm"
    Used for high-throughput inference with GPU clusters.
    @spec docs/spec/platform/13_SCALE_VALIDATION_SPEC.md
    """
```

---

### 6.4 File Layout

| File | Class | Purpose |
|------|-------|---------|
| `adapter.py` | `LLMAdapter` (ABC) | Base interface |
| `ollama_client.py` | `OllamaAdapter` | Local Ollama |
| `claude_client.py` | `ClaudeAdapter` | Anthropic Claude API |
| `openai_client.py` | `OpenAIAdapter` | OpenAI API |
| `vllm_client.py` | `VLLMAdapter` | vLLM distributed inference |
| `gateway.py` | `LLMGateway`, `InMemoryLLMCache`, `VectorLLMCache` | Central call manager |
| `registry.py` | `LLMAdapterRegistry` | Provider registry + fallback |
| `cache.py` | `LLMResponseCache` | Valkey-backed L3 cache |
| `prompt_builder.py` | `PromptBuilder` | Agent cognition prompts |
| `slm_batch.py` | `SLMBatchInferencer` | Tier 1 batch inference |
| `engine_control.py` | `EngineController` | Tier distribution + impact assessment |
| `quota.py` | `LLMQuotaManager` | Rate limiting + budget enforcement |
| `schema.py` | Various dataclasses | `LLMPrompt`, `LLMOptions`, `LLMResponse`, `TierDistribution`, `EngineImpactReport` |

---

## 7. Quota & Rate Management

```python
class LLMQuotaManager:
    def can_call_llm(
        self,
        simulation_id: UUID,
        step: int,
        current_llm_call_count: int,
        total_agents: int,
    ) -> bool:
        """
        Returns False if current_llm_call_count / total_agents > LLM_TIER3_RATIO.
        Enforces per-step LLM budget.
        """

    async def handle_rate_limit(
        self,
        provider: str,
        retry_after: float,
    ) -> None:
        """
        Logs rate limit event.
        Temporarily disables provider for retry_after seconds.
        Falls back to next healthy provider via registry.
        """
```

---

## 7.1 User Engine Control (SLM/LLM Ratio)

```python
class EngineController:
    """
    Prophet-unique feature: user adjusts SLM/LLM ratio at runtime.
    Not available in OASIS.
    """

    def compute_tier_distribution(
        self,
        total_agents: int,
        slm_llm_ratio: float,    # 0.0 = all SLM, 1.0 = all LLM
        budget_usd: float | None = None,
    ) -> TierDistribution:
        """
        Maps user preference to concrete tier assignment:
            ratio=0.0  → Tier1=95%, Tier2=4%, Tier3=1%  (최저 비용)
            ratio=0.5  → Tier1=80%, Tier2=10%, Tier3=10% (권장 기본값)
            ratio=1.0  → Tier1=50%, Tier2=20%, Tier3=30% (최고 품질)

        If budget_usd provided, auto-calculates max feasible ratio:
            estimated_cost = tier3_count * avg_cost_per_call
            if estimated_cost > budget_usd: reduce ratio until within budget
        """

    def get_impact_assessment(
        self,
        distribution: TierDistribution,
    ) -> EngineImpactReport:
        """
        Returns 4 indicators for user dashboard:
            1. cost_efficiency: str     ("$0.12 per step" / "$4.50 per step")
            2. reasoning_depth: str     ("양적 분석" / "균형" / "질적 분석")
            3. simulation_velocity: str ("~2s per step" / "~30s per step")
            4. prediction_type: str     ("Quantitative" / "Hybrid" / "Qualitative")
        """

@dataclass
class TierDistribution:
    tier1_count: int   # Mass SLM
    tier2_count: int   # Semantic Router
    tier3_count: int   # Elite LLM
    tier1_model: str
    tier3_model: str
    estimated_cost_per_step: float
    estimated_latency_ms: float

@dataclass
class EngineImpactReport:
    cost_efficiency: str
    reasoning_depth: str
    simulation_velocity: str
    prediction_type: str
```

**Engine Selection Guide:**

| Mode | SLM/LLM Ratio | Agent Scale | Use Case | Accuracy |
|------|---------------|-------------|----------|----------|
| **SLM 모드** | 0.0–0.2 | 10K–1M | 마케팅 도달 범위, 바이럴 루프 테스트 | 흐름 위주 (~75%) |
| **Hybrid 모드 (권장)** | 0.3–0.6 | 1K–100K | 여론 형성 분석, 정책 반응 시뮬레이션 | 균형 (~90%) |
| **LLM 모드** | 0.7–1.0 | ≤1K | 위기 관리, 핵심 이해관계자 전략 | 매우 정교 (~98%) |

---

## 8. LLM Call Logging

All Tier 3 calls are logged to PostgreSQL:

```python
@dataclass
class LLMCallLog:
    call_id: UUID
    simulation_id: UUID
    agent_id: UUID
    step: int
    provider: str
    model: str
    prompt_hash: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cached: bool
    tier: int = 3
    error: str | None = None
    created_at: datetime
```

---

## 9. Error Specification

| Situation | Exception Type | Recovery | Logging |
|-----------|---------------|----------|---------|
| LLM provider timeout (>10s default) | `LLMTimeoutError` | Tier 3 → fallback to Tier 2; Tier 2 → fallback to Tier 1 | WARN + log to `llm_calls` |
| LLM provider returns invalid JSON | `LLMParseError` | Retry once with stricter prompt; if 2nd fail → fallback to lower tier | WARN + log raw response |
| LLM provider HTTP 429 (rate limit) | `LLMRateLimitError` | Exponential backoff (1s, 2s, 4s), max 3 retries; then fallback tier | WARN |
| LLM provider HTTP 401/403 (auth) | `LLMAuthError` | Immediate fallback to next provider or Tier 1 (no retry) | ERROR |
| LLM provider HTTP 5xx (server error) | `LLMProviderError` | Retry once; then fallback to next provider or lower tier | ERROR |
| All external LLM providers unavailable | — (graceful degradation) | Degrade ALL agents to Tier 1 SLM via local Ollama | ERROR (once per simulation) |
| Ollama local server down | `OllamaConnectionError` | Fatal for simulation — cannot proceed without Tier 1 | CRITICAL → status FAILED |
| Quota manager blocks call (>10% ratio) | — (expected) | Skip LLM call, use Tier 2 evaluation | INFO |
| LLM response score outside expected range | — (clamp) | Clamp to valid range [-1, 1] or [0, 1] per context | WARN |
| Embedding dimension mismatch | `EmbeddingDimensionError` | Reject embedding, skip memory store | ERROR |
| Cache eviction under memory pressure | — (LRU eviction) | Evict least-recently-used entries, continue | INFO |
| Prompt token count exceeds model limit | `LLMTokenLimitError` | Truncate context (oldest memories first), retry | WARN |

---

## 10. Acceptance Criteria (Harness Tests)

| ID | Test | Expected |
|----|------|----------|
| LLM-01 | Ollama adapter health check with server up | Returns True |
| LLM-02 | Ollama adapter with server down → fallback to Claude | Uses Claude adapter |
| LLM-03 | Agent cognition prompt builds valid JSON response | Parsed response has all required keys |
| LLM-04 | Expert analysis prompt returns score in [-1, 1] | Valid range |
| LLM-05 | LLM cache returns cached response on duplicate prompt | `cached == True` |
| LLM-06 | Quota manager blocks LLM calls above 10% ratio | `can_call_llm() == False` |
| LLM-07 | LLM timeout (mock 30s delay) falls back to Tier 2 | `llm_tier_used == 2` |
| LLM-08 | All call logs persisted to DB | `SELECT COUNT(*) FROM llm_calls` matches |
| LLM-09 | Embed via Ollama returns 768-dim vector | `len(embedding) == 768` |
| LLM-10 | Claude adapter rate limit → retry after delay | Retries with exponential backoff |
