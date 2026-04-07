"""LLM Vector Cache model for semantic similarity caching.
SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#vector-cache
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database import Base


class LLMVectorCache(Base):
    __tablename__ = "llm_vector_cache"
    __table_args__ = (
        Index("idx_llm_vcache_task_type", "task_type"),
        # HNSW vector index created via Alembic migration c2_vector_idx:
        # CREATE INDEX idx_llm_vcache_embedding ON llm_vector_cache
        #     USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
    )

    cache_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding = mapped_column(Vector(768), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
