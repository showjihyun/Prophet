"""Campaign model.
SPEC: docs/spec/08_DB_SPEC.md#campaigns
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Numeric, Text, DateTime, func, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal

from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    channels: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    controversy: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    novelty: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    utility: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    start_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_step: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
