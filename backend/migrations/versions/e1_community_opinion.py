"""community_opinions table for EliteLLM-synthesized narratives

Revision ID: e1_community_opinion
Revises: d1_bigint_seed
Create Date: 2026-04-11

SPEC: docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis

Stores the JSON narrative produced by EliteLLM for a (simulation_id,
community_id, step) snapshot. Lets the frontend render "why did this
community behave this way" without re-calling the LLM on every page load.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = "e1_community_opinion"
down_revision: str = "d1_bigint_seed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "community_opinions",
        sa.Column(
            "opinion_id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "simulation_id", UUID(as_uuid=True),
            sa.ForeignKey("simulations.simulation_id", ondelete="CASCADE"),
            nullable=False,
        ),
        # community_id is a string here because community keys can be
        # short slugs ("S", "M") OR real UUIDs depending on how the user
        # configured the simulation. We don't FK this column.
        sa.Column("community_id", sa.String(64), nullable=False),
        sa.Column("step", sa.Integer, nullable=False),

        # Structured LLM output (anti-hallucination: must cite evidence)
        sa.Column("themes", JSONB, nullable=False),
        sa.Column("divisions", JSONB, nullable=False),
        sa.Column("sentiment_trend", sa.String(32), nullable=False),
        sa.Column("dominant_emotions", JSONB, nullable=False),
        sa.Column("key_quotes", JSONB, nullable=False),
        sa.Column("summary", sa.Text, nullable=False),

        # Provenance — how much input data was sampled
        sa.Column("source_step_count", sa.Integer, nullable=False),
        sa.Column("source_agent_count", sa.Integer, nullable=False),

        # LLM metadata
        sa.Column("llm_provider", sa.String(64), nullable=False),
        sa.Column("llm_model", sa.String(128), nullable=False),
        sa.Column("llm_cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("is_fallback_stub", sa.Boolean, nullable=False, server_default=sa.text("false")),

        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.create_index(
        "idx_community_opinions_sim_comm",
        "community_opinions",
        ["simulation_id", "community_id"],
    )
    op.create_index(
        "idx_community_opinions_sim_step",
        "community_opinions",
        ["simulation_id", "step"],
    )


def downgrade() -> None:
    op.drop_index("idx_community_opinions_sim_step", "community_opinions")
    op.drop_index("idx_community_opinions_sim_comm", "community_opinions")
    op.drop_table("community_opinions")
