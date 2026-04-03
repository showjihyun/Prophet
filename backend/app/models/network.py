"""NetworkEdge model.
SPEC: docs/spec/08_DB_SPEC.md#network_edges
"""
import uuid
from datetime import datetime
from sqlalchemy import Integer, Float, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NetworkEdge(Base):
    __tablename__ = "network_edges"
    __table_args__ = (
        UniqueConstraint("simulation_id", "source_node_id", "target_node_id", name="uq_network_edges_sim_src_tgt"),
        CheckConstraint("weight BETWEEN 0 AND 1", name="ck_network_edges_weight"),
        Index("idx_edges_simulation", "simulation_id"),
        Index("idx_edges_source", "simulation_id", "source_node_id"),
    )

    edge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.simulation_id", ondelete="CASCADE"), nullable=False)
    source_node_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_node_id: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    is_bridge: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
