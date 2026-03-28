"""Agent and AgentState models.
SPEC: docs/spec/08_DB_SPEC.md#agents
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, SmallInteger, DateTime, func, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    community_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Personality
    openness: Mapped[float] = mapped_column(Float, nullable=False)
    skepticism: Mapped[float] = mapped_column(Float, nullable=False)
    trend_following: Mapped[float] = mapped_column(Float, nullable=False)
    brand_loyalty: Mapped[float] = mapped_column(Float, nullable=False)
    social_influence: Mapped[float] = mapped_column(Float, nullable=False)
    # Emotion
    emotion_interest: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    emotion_trust: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    emotion_skepticism: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    emotion_excitement: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    # Network
    network_node_id: Mapped[int | None] = mapped_column(Integer)
    influence_score: Mapped[float | None] = mapped_column(Float)
    llm_provider: Mapped[str | None] = mapped_column(String(50))
    activity_vector: Mapped[list[float] | None] = mapped_column(ARRAY(Float, dimensions=1))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentState(Base):
    __tablename__ = "agent_states"

    state_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    # Personality
    openness: Mapped[float] = mapped_column(Float, nullable=False)
    skepticism: Mapped[float] = mapped_column(Float, nullable=False)
    trend_following: Mapped[float] = mapped_column(Float, nullable=False)
    brand_loyalty: Mapped[float] = mapped_column(Float, nullable=False)
    social_influence: Mapped[float] = mapped_column(Float, nullable=False)
    # Emotion
    emotion_interest: Mapped[float] = mapped_column(Float, nullable=False)
    emotion_trust: Mapped[float] = mapped_column(Float, nullable=False)
    emotion_skepticism: Mapped[float] = mapped_column(Float, nullable=False)
    emotion_excitement: Mapped[float] = mapped_column(Float, nullable=False)
    # State
    community_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    belief: Mapped[float] = mapped_column(Float, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    adopted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exposure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_tier_used: Mapped[int | None] = mapped_column(SmallInteger)
    llm_provider: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
