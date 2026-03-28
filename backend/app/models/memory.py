"""AgentMemory model with pgvector embedding.
SPEC: docs/spec/08_DB_SPEC.md#agent_memories
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database import Base


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    memory_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    emotion_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    social_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    embedding = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
