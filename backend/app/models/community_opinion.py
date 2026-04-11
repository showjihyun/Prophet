"""ORM model for EliteLLM-synthesized community opinion snapshots.

SPEC: docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CommunityOpinion(Base):
    """LLM-synthesized opinion snapshot for a community at a step.

    Built from a (simulation_id, community_id, step) input by
    ``CommunityOpinionService.synthesize()``. The frontend renders this
    as a narrative panel under each community.
    """

    __tablename__ = "community_opinions"
    __table_args__ = (
        Index("idx_community_opinions_sim_comm", "simulation_id", "community_id"),
        Index("idx_community_opinions_sim_step", "simulation_id", "step"),
    )

    opinion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulations.simulation_id", ondelete="CASCADE"),
        nullable=False,
    )
    community_id: Mapped[str] = mapped_column(String(64), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)

    themes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    divisions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    sentiment_trend: Mapped[str] = mapped_column(String(32), nullable=False)
    dominant_emotions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    key_quotes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    source_step_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_agent_count: Mapped[int] = mapped_column(Integer, nullable=False)

    llm_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(128), nullable=False)
    llm_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_fallback_stub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
