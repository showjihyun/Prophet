"""widen simulations.random_seed to BIGINT

Revision ID: d1_bigint_seed
Revises: c2_vector_idx
Create Date: 2026-04-11

SPEC: docs/spec/08_DB_SPEC.md#simulations

``SimulationConfig`` auto-generates seeds via ``os.urandom(4)`` which
produces **unsigned** 32-bit values (0 .. 4,294,967,295). The original
INTEGER column (signed int32, max 2,147,483,647) rejected about half
of those seeds with ``OverflowError: value out of int32 range``.

Widening to BIGINT (signed int64, max 9.2e18) accepts any Python int
any caller might supply, so the DB is no longer the bottleneck.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1_bigint_seed'
down_revision: str = 'c2_vector_idx'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'simulations',
        'random_seed',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # WARNING: values exceeding int32 range will be rejected by this cast.
    op.alter_column(
        'simulations',
        'random_seed',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
