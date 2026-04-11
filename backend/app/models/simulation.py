"""Simulation, SimStep, SimulationEvent models.
SPEC: docs/spec/08_DB_SPEC.md#simulations
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, Float, Text, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Simulation(Base):
    __tablename__ = "simulations"
    __table_args__ = (
        Index("idx_simulations_status", "status"),
    )

    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="created")
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    network_metrics: Mapped[dict | None] = mapped_column(JSONB)
    # BigInteger so seeds generated via ``os.urandom(4)`` (unsigned 32-bit,
    # up to 4,294,967,295) fit safely — signed INTEGER tops out at ~2.1B.
    random_seed: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class SimStep(Base):
    __tablename__ = "sim_steps"
    __table_args__ = (
        UniqueConstraint("simulation_id", "step", "replay_id", name="uq_sim_steps_sim_step_replay"),
        Index("idx_steps_simulation_step", "simulation_id", "step"),
    )

    step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.simulation_id", ondelete="CASCADE"), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    total_adoption: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adoption_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    diffusion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    mean_sentiment: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    sentiment_variance: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    action_distribution: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    community_metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    llm_calls_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_tier_distribution: Mapped[dict | None] = mapped_column(JSONB)
    step_duration_ms: Mapped[float | None] = mapped_column(Float)
    replay_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SimulationEvent(Base):
    __tablename__ = "simulation_events"
    __table_args__ = (
        Index("idx_sim_events_simulation", "simulation_id", "created_at"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.simulation_id", ondelete="CASCADE"), nullable=False)
    step: Mapped[int | None] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
