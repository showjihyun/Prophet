"""Layer 2: Memory — agent memory storage and retrieval using GraphRAG-style scoring.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer
"""
from dataclasses import dataclass
from typing import Literal
from uuid import UUID, uuid4


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

    MAX_MEMORIES_PER_AGENT: int = 1000

    def __init__(self, config: MemoryConfig | None = None):
        """SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer"""
        if config is None:
            # Use fallback weights since we have no pgvector in Phase 2
            self._alpha = 0.6
            self._beta = 0.0
            self._gamma = 0.3
            self._delta = 0.1
        else:
            self._alpha = config.alpha
            self._beta = config.beta
            self._gamma = config.gamma
            self._delta = config.delta
        self._store: dict[UUID, list[MemoryRecord]] = {}

    def retrieve(
        self,
        agent_id: UUID,
        query_context: str,
        top_k: int = 10,
        current_step: int = 0,
    ) -> list[MemoryRecord]:
        """Retrieves top-K relevant memories for the given agent.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer

        Algorithm:
            For each memory m of agent_id:
              recency_score   = 1.0 / (1 + (current_step - m.timestamp))
              relevance_score = 0.0 (no embedding in Phase 2)
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
            relevance_score = 0.0  # No embedding support in Phase 2

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
        if embedding is not None and len(embedding) != 768:
            raise ValueError(f"embedding length must be 768, got {len(embedding)}")

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


__all__ = ["MemoryLayer", "MemoryRecord", "MemoryConfig"]
