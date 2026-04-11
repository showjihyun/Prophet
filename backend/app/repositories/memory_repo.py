"""Repository helpers for ``MemoryLayer`` (Layer-2 Agent Memory).

SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#2.4
SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§3 MP-03

**Round 6 move**: the raw SQL + pgvector queries used to live inside
``app/engine/agent/memory.py`` which violated CA-01 (engine/ must not
import SQLAlchemy). The SQL is moved here — MemoryLayer now delegates
to ``find_nearest_memories`` / ``insert_memory`` from the repositories
layer and no longer imports sqlalchemy at runtime.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# --------------------------------------------------------------------------- #
# Row shapes — plain dicts so the domain layer never touches ORM objects.    #
# --------------------------------------------------------------------------- #


async def find_nearest_memories(
    session: AsyncSession,
    *,
    simulation_id: UUID | None,
    agent_id: UUID,
    query_embedding: list[float],
    limit: int,
) -> list[dict[str, Any]]:
    """Return the ``limit`` nearest memories for an agent via pgvector.

    Distance metric: cosine (``<=>`` operator on the ``embedding`` column).
    Returned rows are plain dicts so ``MemoryLayer`` never has to know
    about ORM types.

    :param simulation_id: scopes the query to one simulation
    :param agent_id: the owning agent
    :param query_embedding: 768-dim query vector
    :param limit: top-K fetch count (usually ``3 * top_k`` to allow
        downstream composite rescoring to re-rank)
    """
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    result = await session.execute(
        text(
            """
            SELECT memory_id, agent_id, memory_type, content, step,
                   emotion_weight, social_weight,
                   1 - (embedding <=> :emb::vector) AS cosine_sim
            FROM agent_memories
            WHERE agent_id = :aid
              AND simulation_id = :sid
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :emb::vector
            LIMIT :fetch_k
            """
        ),
        {
            "emb": embedding_str,
            "aid": agent_id,
            "sid": simulation_id,
            "fetch_k": limit,
        },
    )
    rows: list[dict[str, Any]] = []
    for row in result.fetchall():
        rows.append({
            "memory_id": row.memory_id,
            "agent_id": row.agent_id,
            "memory_type": row.memory_type,
            "content": row.content,
            "step": row.step,
            "emotion_weight": row.emotion_weight,
            "social_weight": row.social_weight,
            "cosine_sim": float(row.cosine_sim),
        })
    return rows


async def insert_memory(
    session: AsyncSession,
    *,
    memory_id: UUID,
    simulation_id: UUID | None,
    agent_id: UUID,
    memory_type: str,
    content: str,
    emotion_weight: float,
    step: int,
    social_weight: float,
    embedding: list[float] | None,
) -> None:
    """Insert a single agent memory row into ``agent_memories``.

    The embedding is serialized as ``"[f1,f2,...]"`` and cast to the
    pgvector ``vector`` type via ``::vector``. NULL embeddings are
    allowed (semantic-search retrieval will ignore them).
    """
    embedding_str: str | None = None
    if embedding is not None:
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    await session.execute(
        text(
            """
            INSERT INTO agent_memories
                (memory_id, simulation_id, agent_id, memory_type,
                 content, emotion_weight, step, social_weight, embedding)
            VALUES (:mid, :sid, :aid, :mtype, :content, :ew, :step, :sw,
                    :emb::vector)
            """
        ),
        {
            "mid": memory_id,
            "sid": simulation_id,
            "aid": agent_id,
            "mtype": memory_type,
            "content": content,
            "ew": emotion_weight,
            "step": step,
            "sw": social_weight,
            "emb": embedding_str,
        },
    )
    await session.commit()


__all__ = ["find_nearest_memories", "insert_memory"]
