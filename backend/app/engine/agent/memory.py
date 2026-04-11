"""Layer 2: Memory — agent memory storage and retrieval using GraphRAG-style scoring.

SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer
SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§3 MP-01~04
SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#2.4

**Round 6**: raw SQL + sqlalchemy imports moved to
``app/repositories/memory_repo.py`` so this file — part of the engine
layer — no longer violates CA-01 ("engine/ must not import SQLAlchemy").
MemoryLayer retains its ``session_factory`` injection (infrastructure
handle from deps.py) but delegates all SQL execution to the repository
helper functions.
"""
from __future__ import annotations

import logging
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Literal
from uuid import UUID, uuid4

# Domain defaults — injected from infrastructure via constructor at runtime.
# We avoid a module-level ``from app.config import settings`` import so the
# engine layer can be imported without triggering any infrastructure load.
_DEFAULTS = {
    "agent_max_memories": 1000,
    "memory_fallback_alpha": 0.6,
    "memory_fallback_beta": 0.25,
    "memory_fallback_gamma": 0.3,
    "memory_fallback_delta": 0.1,
    "embedding_dim": 768,
}


def _get_setting(key: str) -> float | int:
    """Get config value: try app.config.settings at runtime, fall back to domain default.

    The lazy import is intentional — if settings is unavailable (e.g.
    during pure-unit tests or tools that never load .env), we fall back
    to the hardcoded domain defaults and keep engine code runnable.
    """
    try:
        from app.config import settings as _s  # noqa: PLC0415 — lazy DI fallback
        return getattr(_s, key, _DEFAULTS[key])
    except Exception:
        return _DEFAULTS[key]


if TYPE_CHECKING:
    # Type-only — never imported at runtime, so no CA-01 violation.
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = Callable[[], AbstractAsyncContextManager["AsyncSession"]]
"""Structural type for the session factory injected into MemoryLayer.

We don't import ``async_sessionmaker`` at runtime — only the stdlib
``AbstractAsyncContextManager`` + ``Callable`` types. The ``AsyncSession``
type is a ``TYPE_CHECKING``-only forward reference."""

logger = logging.getLogger(__name__)


@dataclass
class MemoryRecord:
    """A single memory entry.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer

    Invariants:
      - emotion_weight in [0.0, 1.0]
      - social_importance in [0.0, 1.0]
      - embedding is None or len == 768
      - relevance_score is None (not yet queried) or float
    """
    memory_id: UUID
    agent_id: UUID
    memory_type: Literal["episodic", "semantic", "social"]
    content: str
    timestamp: int
    emotion_weight: float
    social_importance: float
    embedding: list[float] | None
    relevance_score: float | None


@dataclass
class MemoryConfig:
    """Configurable weights for memory retrieval scoring.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer
    """
    alpha: float = 0.3    # recency weight
    beta: float = 0.4     # relevance weight (pgvector cosine)
    gamma: float = 0.2    # emotion weight
    delta: float = 0.1    # social importance weight

    def __post_init__(self):
        total = self.alpha + self.beta + self.gamma + self.delta
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"MemoryConfig weights must sum to 1.0, got {total}")


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer
    """
    import numpy as np
    a_arr = np.asarray(a, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


class MemoryLayer:
    """Agent memory storage and retrieval using GraphRAG-style scoring.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer

    Phase 2: in-memory list storage (no DB). DB integration in Phase 6.

    Scoring weights (configurable via MemoryConfig):
        alpha (recency):          0.3
        beta  (relevance):        0.4  (pgvector cosine similarity)
        gamma (emotion_weight):   0.2
        delta (social_importance): 0.1

    Fallback weights (when pgvector unavailable — Phase 2 default):
        alpha: 0.6, gamma: 0.3, delta: 0.1
    """

    MAX_MEMORIES_PER_AGENT: int = _DEFAULTS["agent_max_memories"]

    def __init__(
        self,
        config: MemoryConfig | None = None,
        llm_adapter: Any = None,
        session_factory: SessionFactory | None = None,
        simulation_id: UUID | None = None,
    ):
        """SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer
        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§3 MP-02

        Args:
            config: Optional MemoryConfig with scoring weights.
            llm_adapter: Optional LLMAdapter for embedding-based retrieval.
            session_factory: Optional async_sessionmaker for pgvector persistence.
            simulation_id: Required when session_factory is set — scopes DB queries.
        """
        self._session_factory = session_factory
        self._simulation_id = simulation_id

        if config is not None:
            self._alpha = config.alpha
            self._beta = config.beta
            self._gamma = config.gamma
            self._delta = config.delta
        elif session_factory is not None:
            # Full weights: pgvector cosine is active
            self._alpha = 0.3
            self._beta = 0.4
            self._gamma = 0.2
            self._delta = 0.1
        else:
            # Fallback weights: no pgvector — beta is dead weight
            self._alpha = _get_setting("memory_fallback_alpha")
            self._beta = _get_setting("memory_fallback_beta")
            self._gamma = _get_setting("memory_fallback_gamma")
            self._delta = _get_setting("memory_fallback_delta")
        self._store: dict[UUID, list[MemoryRecord]] = {}
        self._llm_adapter = llm_adapter

    async def embed_text(self, text: str) -> list[float] | None:
        """Generate embedding for text using the configured LLM adapter.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer

        Returns None if no adapter is configured or embedding fails.
        """
        if self._llm_adapter is None:
            return None
        try:
            return await self._llm_adapter.embed(text)
        except Exception:
            return None

    def retrieve(
        self,
        agent_id: UUID,
        query_context: str,
        top_k: int = 10,
        current_step: int = 0,
        query_embedding: list[float] | None = None,
    ) -> list[MemoryRecord]:
        """Retrieves top-K relevant memories for the given agent.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer

        Algorithm:
            For each memory m of agent_id:
              recency_score   = 1.0 / (1 + (current_step - m.timestamp))
              relevance_score = cosine_similarity(query_embedding, m.embedding)
                                if both are available, else 0.0
              score = alpha * recency_score
                    + beta  * relevance_score
                    + gamma * m.emotion_weight
                    + delta * m.social_importance
            Sort by score DESC, return top_k.

        Determinism: Deterministic for same state + inputs.
        """
        if top_k <= 0:
            raise ValueError(f"top_k must be > 0, got {top_k}")

        memories = self._store.get(agent_id, [])
        if not memories:
            return []

        scored: list[tuple[float, int, MemoryRecord]] = []
        for idx, m in enumerate(memories):
            recency_score = 1.0 / (1 + abs(current_step - m.timestamp))

            # Use cosine similarity when both query and memory embeddings are available
            if query_embedding is not None and m.embedding is not None:
                relevance_score = _cosine_similarity(query_embedding, m.embedding)
            else:
                relevance_score = 0.0

            score = (
                self._alpha * recency_score
                + self._beta * relevance_score
                + self._gamma * m.emotion_weight
                + self._delta * m.social_importance
            )
            scored.append((score, idx, m))

        # Sort by score DESC, stable via idx
        scored.sort(key=lambda x: (-x[0], x[1]))
        scored = scored[:top_k]

        result = []
        for score, _, m in scored:
            result.append(MemoryRecord(
                memory_id=m.memory_id,
                agent_id=m.agent_id,
                memory_type=m.memory_type,
                content=m.content,
                timestamp=m.timestamp,
                emotion_weight=m.emotion_weight,
                social_importance=m.social_importance,
                embedding=m.embedding,
                relevance_score=score,
            ))
        return result

    async def retrieve_async(
        self,
        agent_id: UUID,
        query_context: str,
        top_k: int = 10,
        current_step: int = 0,
        query_text: str | None = None,
    ) -> list[MemoryRecord]:
        """Async retrieval — pgvector path when DB is available, else in-memory.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer
        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§3 MP-03/04

        Args:
            agent_id: Agent to retrieve memories for.
            query_context: Text context for retrieval (fallback if no embedding).
            top_k: Maximum number of memories to return.
            current_step: Current simulation step for recency scoring.
            query_text: Optional text to embed for similarity scoring.
        """
        query_embedding = None
        if query_text and self._llm_adapter:
            query_embedding = await self.embed_text(query_text)

        # pgvector path: DB + embedding available
        if self._session_factory is not None and query_embedding is not None:
            return await self._retrieve_pgvector(
                agent_id, query_embedding, top_k, current_step,
            )

        # Fallback: in-memory only (Tier 1/2, no DB, or no embedding)
        return self.retrieve(
            agent_id, query_context, top_k=top_k,
            current_step=current_step, query_embedding=query_embedding,
        )

    async def _retrieve_pgvector(
        self,
        agent_id: UUID,
        query_embedding: list[float],
        top_k: int,
        current_step: int,
    ) -> list[MemoryRecord]:
        """Retrieve memories using pgvector cosine similarity + composite scoring.

        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§3 MP-03/04

        Strategy:
        1. Ask pgvector for top 3*top_k by cosine similarity
        2. Merge with in-memory records (not yet flushed)
        3. Composite score: alpha*recency + beta*cosine + gamma*emotion + delta*social
        4. Return top_k by score DESC

        SQL lives in ``app/repositories/memory_repo.py`` — this method
        delegates so the engine layer doesn't touch SQLAlchemy directly.
        """
        # Lazy import so the engine layer has no module-level sqlalchemy
        # dependency. This is the only cross-layer call from memory.py.
        from app.repositories.memory_repo import find_nearest_memories  # noqa: PLC0415

        candidates: list[tuple[MemoryRecord, float]] = []  # (record, cosine_sim)

        try:
            assert self._session_factory is not None
            async with self._session_factory() as session:
                rows = await find_nearest_memories(
                    session,
                    simulation_id=self._simulation_id,
                    agent_id=agent_id,
                    query_embedding=query_embedding,
                    limit=top_k * 3,
                )
                for row in rows:
                    rec = MemoryRecord(
                        memory_id=row["memory_id"],
                        agent_id=row["agent_id"],
                        memory_type=row["memory_type"],
                        content=row["content"],
                        timestamp=row["step"],
                        emotion_weight=row["emotion_weight"],
                        social_importance=row["social_weight"],
                        embedding=None,  # don't load full vectors into memory
                        relevance_score=None,
                    )
                    candidates.append((rec, row["cosine_sim"]))
        except Exception:
            logger.warning("pgvector retrieval failed, falling back to in-memory")
            return self.retrieve(
                agent_id, "", top_k=top_k, current_step=current_step,
                query_embedding=query_embedding,
            )

        # Merge in-memory records (may not be flushed to DB yet)
        seen_ids: set[UUID] = {c[0].memory_id for c in candidates}
        for m in self._store.get(agent_id, []):
            if m.memory_id in seen_ids:
                continue
            if m.embedding is not None:
                sim = _cosine_similarity(query_embedding, m.embedding)
            else:
                sim = 0.0
            candidates.append((m, sim))

        # Composite scoring
        scored: list[tuple[float, int, MemoryRecord]] = []
        for idx, (rec, cosine_sim) in enumerate(candidates):
            recency = 1.0 / (1 + abs(current_step - rec.timestamp))
            score = (
                self._alpha * recency
                + self._beta * cosine_sim
                + self._gamma * rec.emotion_weight
                + self._delta * rec.social_importance
            )
            scored.append((score, idx, rec))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [
            MemoryRecord(
                memory_id=rec.memory_id,
                agent_id=rec.agent_id,
                memory_type=rec.memory_type,
                content=rec.content,
                timestamp=rec.timestamp,
                emotion_weight=rec.emotion_weight,
                social_importance=rec.social_importance,
                embedding=rec.embedding,
                relevance_score=score,
            )
            for score, _, rec in scored[:top_k]
        ]

    async def store_async(
        self,
        agent_id: UUID,
        memory_type: Literal["episodic", "semantic", "social"],
        content: str,
        emotion_weight: float,
        social_importance: float = 0.0,
        embedding: list[float] | None = None,
        step: int = 0,
    ) -> MemoryRecord:
        """Store memory in-memory AND persist to pgvector asynchronously.

        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§3 MP-03

        Write-through: in-memory first (fast), then async DB write (fire-and-forget).
        """
        record = self.store(
            agent_id, memory_type, content, emotion_weight,
            social_importance, embedding, step,
        )
        if self._session_factory is not None:
            await self._persist_to_db(record)
        return record

    async def _persist_to_db(self, record: MemoryRecord) -> None:
        """Fire-and-forget persist a MemoryRecord to agent_memories table.

        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§3 MP-03

        SQL lives in ``app/repositories/memory_repo.py`` — this method
        delegates so the engine layer doesn't touch SQLAlchemy directly.
        """
        # Lazy import: only triggered when DB persistence is actually used.
        from app.repositories.memory_repo import insert_memory  # noqa: PLC0415

        try:
            assert self._session_factory is not None
            async with self._session_factory() as session:
                await insert_memory(
                    session,
                    memory_id=record.memory_id,
                    simulation_id=self._simulation_id,
                    agent_id=record.agent_id,
                    memory_type=record.memory_type,
                    content=record.content,
                    emotion_weight=record.emotion_weight,
                    step=record.timestamp,
                    social_weight=record.social_importance,
                    embedding=record.embedding,
                )
        except Exception:
            logger.warning("Failed to persist memory %s to DB", record.memory_id)

    def store(
        self,
        agent_id: UUID,
        memory_type: Literal["episodic", "semantic", "social"],
        content: str,
        emotion_weight: float,
        social_importance: float = 0.0,
        embedding: list[float] | None = None,
        step: int = 0,
    ) -> MemoryRecord:
        """Stores a new memory record for the agent.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer

        Side Effects: Inserts into in-memory store.
        """
        if not content:
            raise ValueError("content must not be empty")
        _dim = _get_setting("embedding_dim")
        if embedding is not None and len(embedding) != _dim:
            raise ValueError(f"embedding length must be {_dim}, got {len(embedding)}")

        # Clamp emotion_weight and social_importance
        emotion_weight = max(0.0, min(1.0, emotion_weight))
        social_importance = max(0.0, min(1.0, social_importance))

        record = MemoryRecord(
            memory_id=uuid4(),
            agent_id=agent_id,
            memory_type=memory_type,
            content=content,
            timestamp=step,
            emotion_weight=emotion_weight,
            social_importance=social_importance,
            embedding=embedding,
            relevance_score=None,
        )

        if agent_id not in self._store:
            self._store[agent_id] = []
        self._store[agent_id].append(record)

        # Eviction check
        agent_memories = self._store.get(agent_id, [])
        if len(agent_memories) > self.MAX_MEMORIES_PER_AGENT:
            # Evict lowest emotion_weight memories
            agent_memories.sort(key=lambda m: m.emotion_weight)
            self._store[agent_id] = agent_memories[-self.MAX_MEMORIES_PER_AGENT:]

        return record


__all__ = ["MemoryLayer", "MemoryRecord", "MemoryConfig", "_cosine_similarity"]
