"""add llm_vector_cache table and vector indexes

Revision ID: c2_vector_idx
Revises: b55bc066a0f8
Create Date: 2026-04-04

SPEC: docs/spec/05_LLM_SPEC.md#vector-cache
Creates llm_vector_cache table and HNSW vector indexes for
both agent_memories and llm_vector_cache embeddings.
HNSW is used instead of IVFFlat because it works on empty tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'c2_vector_idx'
down_revision: str = 'b55bc066a0f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. Create llm_vector_cache table ---
    op.create_table(
        'llm_vector_cache',
        sa.Column('cache_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('prompt_hash', sa.String(64), nullable=False),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('prompt_text', sa.Text, nullable=False),
        sa.Column('response_json', sa.Text, nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Add vector column via raw SQL (pgvector)
    op.execute('ALTER TABLE llm_vector_cache ADD COLUMN embedding vector(768) NOT NULL')

    # Indexes for llm_vector_cache
    op.create_index('idx_llm_vcache_prompt_hash', 'llm_vector_cache', ['prompt_hash'], unique=True)
    op.create_index('idx_llm_vcache_task_type', 'llm_vector_cache', ['task_type'])

    # --- 2. HNSW vector indexes (work on empty tables, unlike IVFFlat) ---
    # llm_vector_cache: cosine similarity search for semantic cache hits
    op.execute(
        'CREATE INDEX idx_llm_vcache_embedding ON llm_vector_cache '
        'USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)'
    )

    # agent_memories: cosine similarity search for memory retrieval
    op.execute(
        'CREATE INDEX idx_memory_embedding ON agent_memories '
        'USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)'
    )


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS idx_memory_embedding')
    op.execute('DROP INDEX IF EXISTS idx_llm_vcache_embedding')
    op.drop_index('idx_llm_vcache_task_type', 'llm_vector_cache')
    op.drop_index('idx_llm_vcache_prompt_hash', 'llm_vector_cache')
    op.drop_table('llm_vector_cache')
