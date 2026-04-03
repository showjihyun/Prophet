"""Propagation, Expert, Emergent, MonteCarlo, LLMCall models.
SPEC: docs/spec/08_DB_SPEC.md
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, SmallInteger, Text, DateTime, ForeignKey, Index, CheckConstraint, func, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PropagationEvent(Base):
    __tablename__ = "propagation_events"
    __table_args__ = (
        Index("idx_propagation_sim_step", "simulation_id", "step"),
        Index("idx_propagation_source", "source_agent_id"),
        Index("idx_propagation_target", "target_agent_id"),
    )

    propagation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.simulation_id", ondelete="CASCADE"), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    source_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False)
    target_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)
    sentiment_polarity: Mapped[float | None] = mapped_column(Float)
    source_summary: Mapped[str | None] = mapped_column(Text)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ExpertOpinion(Base):
    __tablename__ = "expert_opinions"
    __table_args__ = (
        CheckConstraint("score BETWEEN -1 AND 1", name="ck_expert_opinions_score"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_expert_opinions_confidence"),
        Index("idx_expert_opinions_sim", "simulation_id", "step"),
    )

    opinion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.simulation_id", ondelete="CASCADE"), nullable=False)
    expert_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    affects_communities: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmergentEvent(Base):
    __tablename__ = "emergent_events"
    __table_args__ = (
        CheckConstraint("severity BETWEEN 0 AND 1", name="ck_emergent_events_severity"),
        Index("idx_emergent_simulation", "simulation_id", "step"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.simulation_id", ondelete="CASCADE"), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    community_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("communities.community_id"))
    severity: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    affected_agent_count: Mapped[int | None] = mapped_column(Integer)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MonteCarloRun(Base):
    __tablename__ = "monte_carlo_runs"
    __table_args__ = (
        Index("idx_monte_carlo_sim", "simulation_id"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.simulation_id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    n_runs: Mapped[int] = mapped_column(Integer, nullable=False)
    llm_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Results (populated on completion)
    viral_probability: Mapped[float | None] = mapped_column(Float)
    expected_reach: Mapped[float | None] = mapped_column(Float)
    p5_reach: Mapped[float | None] = mapped_column(Float)
    p50_reach: Mapped[float | None] = mapped_column(Float)
    p95_reach: Mapped[float | None] = mapped_column(Float)
    community_adoption: Mapped[dict | None] = mapped_column(JSONB)
    run_summaries: Mapped[dict | None] = mapped_column(JSONB)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LLMCall(Base):
    __tablename__ = "llm_calls"
    __table_args__ = (
        Index("idx_llm_calls_simulation", "simulation_id", "step"),
        Index("idx_llm_calls_agent", "agent_id"),
    )

    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.simulation_id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.agent_id"))
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    cached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
