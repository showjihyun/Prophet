"""UNIQUE constraint on community_opinions (sim_id, community_id, step)

Revision ID: e2_community_opinion_unique
Revises: e1_community_opinion
Create Date: 2026-04-11

SPEC: docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis

Without a UNIQUE constraint on ``(simulation_id, community_id, step)``,
two concurrent requests hitting :meth:`CommunityOpinionService.get_or_synthesize`
at the same step can BOTH miss the ``_find_cached`` lookup and BOTH pay
for a real Tier-3 LLM call. The service's cache contract ("one LLM call
per sim/community/step") is undermined by the race window.

This migration adds the missing constraint. The service upgrades to
catch the resulting ``unique_violation`` (sqlstate ``23505``) and
re-fetch the winner's row instead of inserting a duplicate.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e2_community_opinion_unique"
down_revision: str = "e1_community_opinion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clean out any existing duplicates before adding the constraint —
    # there shouldn't be any in practice (the cache was idempotent in
    # the sequential case) but a defensive DELETE keeps the migration
    # from failing on databases that happened to catch a race.
    op.execute(
        """
        DELETE FROM community_opinions a
        USING community_opinions b
        WHERE a.created_at < b.created_at
          AND a.simulation_id = b.simulation_id
          AND a.community_id = b.community_id
          AND a.step = b.step
        """
    )
    op.create_unique_constraint(
        "uq_community_opinions_sim_comm_step",
        "community_opinions",
        ["simulation_id", "community_id", "step"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_community_opinions_sim_comm_step",
        "community_opinions",
        type_="unique",
    )
