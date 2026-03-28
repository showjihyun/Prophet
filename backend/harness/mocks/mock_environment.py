"""Mock environment for harness testing.
SPEC: docs/spec/09_HARNESS_SPEC.md#f19-mock-environment
"""
import json
import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class LLMResponse:
    """Simplified LLM response for mocks."""
    provider: str
    model: str
    content: str
    parsed: dict[str, Any] | None
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cached: bool = False


@dataclass
class LLMPrompt:
    """Simplified LLM prompt for mocks."""
    system: str = ""
    user: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    response_format: str = "json"
    max_tokens: int = 512


class MockLLMAdapter:
    """
    Returns deterministic responses for testing.
    SPEC: docs/spec/09_HARNESS_SPEC.md#f19-mock-environment
    """
    provider_name = "mock"

    def __init__(self, response_template: dict[str, Any] | None = None):
        self.response_template = response_template or {
            "evaluation_score": 0.5,
            "recommended_action": "like",
            "reasoning": "Mock reasoning for test",
            "confidence": 0.8,
        }
        self.call_count = 0
        self.call_log: list[LLMPrompt] = []

    async def complete(self, prompt: LLMPrompt, options: Any = None) -> LLMResponse:
        self.call_count += 1
        self.call_log.append(prompt)
        return LLMResponse(
            provider="mock",
            model="mock-1.0",
            content=json.dumps(self.response_template),
            parsed=self.response_template,
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=1.0,
        )

    async def embed(self, text: str) -> list[float]:
        """Returns deterministic 768-dim vector (hash-based)."""
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        return rng.uniform(-1, 1, 768).tolist()

    async def health_check(self) -> bool:
        return True


class MockSLMAdapter:
    """
    Mock SLM for Tier 1 testing.
    SPEC: docs/spec/09_HARNESS_SPEC.md#f19-mock-environment
    """

    def __init__(self, response_template: dict[str, Any] | None = None):
        self.response_template = response_template or {
            "evaluation_score": 0.3,
            "action": "like",
            "reasoning": "Mock SLM reasoning",
            "confidence": 0.6,
        }
        self.call_count = 0
        self.batch_log: list[int] = []

    async def batch_complete(self, prompts: list[LLMPrompt], options: Any = None) -> list[LLMResponse]:
        self.call_count += len(prompts)
        self.batch_log.append(len(prompts))
        return [
            LLMResponse(
                provider="mock-slm",
                model="mock-phi4",
                content=json.dumps(self.response_template),
                parsed=self.response_template,
                prompt_tokens=50,
                completion_tokens=30,
                latency_ms=5.0,
            )
            for _ in prompts
        ]

    async def health_check(self) -> dict[str, Any]:
        return {"model": "mock-phi4", "status": "ok"}


class MockDatabase:
    """
    In-memory SQLite database for harness tests.
    SPEC: docs/spec/09_HARNESS_SPEC.md#f19-mock-environment
    """

    def __init__(self):
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self._session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.session: AsyncSession | None = None

    async def setup(self) -> None:
        from app.database import Base
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session = self._session_factory()

    async def teardown(self) -> None:
        if self.session:
            await self.session.close()
        await self.engine.dispose()
