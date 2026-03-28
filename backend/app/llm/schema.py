"""LLM integration data types and exceptions.
SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import UUID


@dataclass
class LLMPrompt:
    """Prompt payload sent to an LLM provider.

    SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract
    """
    system: str
    user: str
    context: dict[str, Any] = field(default_factory=dict)
    response_format: Literal["text", "json"] = "json"
    max_tokens: int = 512


@dataclass
class LLMOptions:
    """Per-call options for LLM invocation.

    SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract
    """
    temperature: float = 0.7
    timeout_seconds: float = 10.0
    retry_count: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class LLMResponse:
    """Structured response from an LLM provider.

    SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract
    """
    provider: str
    model: str
    content: str
    parsed: dict[str, Any] | None
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cached: bool = False


@dataclass
class LLMCallLog:
    """Log entry for a Tier 3 LLM call, persisted to PostgreSQL.

    SPEC: docs/spec/05_LLM_SPEC.md#8-llm-call-logging
    """
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
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TierDistribution:
    """Concrete tier assignment for a simulation step.

    SPEC: docs/spec/05_LLM_SPEC.md#71-user-engine-control-slmllm-ratio
    """
    tier1_count: int   # Mass SLM
    tier2_count: int   # Semantic Router
    tier3_count: int   # Elite LLM
    tier1_model: str
    tier3_model: str
    estimated_cost_per_step: float
    estimated_latency_ms: float


@dataclass
class EngineImpactReport:
    """4 indicators for the user dashboard.

    SPEC: docs/spec/05_LLM_SPEC.md#71-user-engine-control-slmllm-ratio
    """
    cost_efficiency: str
    reasoning_depth: str
    simulation_velocity: str
    prediction_type: str


# ---------------------------------------------------------------------------
# Custom exceptions
# SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
# ---------------------------------------------------------------------------

class LLMTimeoutError(Exception):
    """LLM provider timeout (>10s default).

    SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
    """


class LLMRateLimitError(Exception):
    """LLM provider HTTP 429 (rate limit).

    SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
    """
    def __init__(self, message: str = "Rate limit exceeded", retry_after: float = 1.0):
        super().__init__(message)
        self.retry_after = retry_after


class LLMAuthError(Exception):
    """LLM provider HTTP 401/403 (auth failure).

    SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
    """


class LLMProviderError(Exception):
    """LLM provider HTTP 5xx (server error).

    SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
    """


class LLMParseError(Exception):
    """LLM provider returned invalid JSON.

    SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
    """


class OllamaConnectionError(Exception):
    """Ollama local server unreachable — fatal for simulation.

    SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
    """


class EmbeddingDimensionError(Exception):
    """Embedding vector dimension mismatch (expected 768).

    SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
    """


class LLMTokenLimitError(Exception):
    """Prompt token count exceeds model limit.

    SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
    """


__all__ = [
    "LLMPrompt",
    "LLMOptions",
    "LLMResponse",
    "LLMCallLog",
    "TierDistribution",
    "EngineImpactReport",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMAuthError",
    "LLMProviderError",
    "LLMParseError",
    "OllamaConnectionError",
    "EmbeddingDimensionError",
    "LLMTokenLimitError",
]
