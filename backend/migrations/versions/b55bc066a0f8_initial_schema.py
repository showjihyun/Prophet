"""initial_schema

Revision ID: b55bc066a0f8
Revises:
Create Date: 2026-03-31 00:32:48.022694

SPEC: docs/spec/08_DB_SPEC.md
Creates all 16 tables with FK, indexes, UNIQUE, CHECK constraints.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'b55bc066a0f8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Extensions ---
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    # --- 1. simulations (root table, no FKs) ---
    op.create_table(
        'simulations',
        sa.Column('simulation_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(50), nullable=False, server_default='created'),
        sa.Column('current_step', sa.Integer, nullable=False, server_default='0'),
        sa.Column('max_steps', sa.Integer, nullable=False, server_default='50'),
        sa.Column('config', JSONB, nullable=False),
        sa.Column('network_metrics', JSONB),
        sa.Column('random_seed', sa.Integer),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('error_message', sa.Text),
    )
    op.create_index('idx_simulations_status', 'simulations', ['status'])

    # --- 2. projects (root table, no FKs) ---
    op.create_table(
        'projects',
        sa.Column('project_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- 3. communities (FK → simulations) ---
    op.create_table(
        'communities',
        sa.Column('community_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('community_key', sa.String(10), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('size', sa.Integer, nullable=False),
        sa.Column('config', JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_communities_simulation', 'communities', ['simulation_id'])

    # --- 4. agents (FK → simulations, communities) ---
    op.create_table(
        'agents',
        sa.Column('agent_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('community_id', UUID(as_uuid=True), sa.ForeignKey('communities.community_id'), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('openness', sa.Float, nullable=False),
        sa.Column('skepticism', sa.Float, nullable=False),
        sa.Column('trend_following', sa.Float, nullable=False),
        sa.Column('brand_loyalty', sa.Float, nullable=False),
        sa.Column('social_influence', sa.Float, nullable=False),
        sa.Column('emotion_interest', sa.Float, nullable=False, server_default='0.5'),
        sa.Column('emotion_trust', sa.Float, nullable=False, server_default='0.5'),
        sa.Column('emotion_skepticism', sa.Float, nullable=False, server_default='0.5'),
        sa.Column('emotion_excitement', sa.Float, nullable=False, server_default='0.3'),
        sa.Column('network_node_id', sa.Integer),
        sa.Column('influence_score', sa.Float),
        sa.Column('llm_provider', sa.String(50)),
        sa.Column('activity_vector', sa.ARRAY(sa.Float, dimensions=1)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('openness BETWEEN 0 AND 1', name='ck_agents_openness'),
        sa.CheckConstraint('skepticism BETWEEN 0 AND 1', name='ck_agents_skepticism'),
        sa.CheckConstraint('trend_following BETWEEN 0 AND 1', name='ck_agents_trend_following'),
        sa.CheckConstraint('brand_loyalty BETWEEN 0 AND 1', name='ck_agents_brand_loyalty'),
        sa.CheckConstraint('social_influence BETWEEN 0 AND 1', name='ck_agents_social_influence'),
    )
    op.create_index('idx_agents_simulation', 'agents', ['simulation_id'])
    op.create_index('idx_agents_community', 'agents', ['community_id'])

    # --- 5. scenarios (FK → projects, simulations) ---
    op.create_table(
        'scenarios',
        sa.Column('scenario_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.project_id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id')),
        sa.Column('config', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- 6. network_edges (FK → simulations) ---
    op.create_table(
        'network_edges',
        sa.Column('edge_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_node_id', sa.Integer, nullable=False),
        sa.Column('target_node_id', sa.Integer, nullable=False),
        sa.Column('weight', sa.Float, nullable=False),
        sa.Column('is_bridge', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('simulation_id', 'source_node_id', 'target_node_id', name='uq_network_edges_sim_src_tgt'),
        sa.CheckConstraint('weight BETWEEN 0 AND 1', name='ck_network_edges_weight'),
    )
    op.create_index('idx_edges_simulation', 'network_edges', ['simulation_id'])
    op.create_index('idx_edges_source', 'network_edges', ['simulation_id', 'source_node_id'])

    # --- 7. sim_steps (FK → simulations) ---
    op.create_table(
        'sim_steps',
        sa.Column('step_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('step', sa.Integer, nullable=False),
        sa.Column('total_adoption', sa.Integer, nullable=False, server_default='0'),
        sa.Column('adoption_rate', sa.Float, nullable=False, server_default='0'),
        sa.Column('diffusion_rate', sa.Float, nullable=False, server_default='0'),
        sa.Column('mean_sentiment', sa.Float, nullable=False, server_default='0'),
        sa.Column('sentiment_variance', sa.Float, nullable=False, server_default='0'),
        sa.Column('action_distribution', JSONB, nullable=False, server_default='{}'),
        sa.Column('community_metrics', JSONB, nullable=False, server_default='{}'),
        sa.Column('llm_calls_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('llm_tier_distribution', JSONB),
        sa.Column('step_duration_ms', sa.Float),
        sa.Column('replay_id', UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('simulation_id', 'step', 'replay_id', name='uq_sim_steps_sim_step_replay'),
    )
    op.create_index('idx_steps_simulation_step', 'sim_steps', ['simulation_id', 'step'])

    # --- 8. agent_states (FK → simulations, agents, communities) ---
    op.create_table(
        'agent_states',
        sa.Column('state_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.agent_id', ondelete='CASCADE'), nullable=False),
        sa.Column('step', sa.Integer, nullable=False),
        sa.Column('openness', sa.Float, nullable=False),
        sa.Column('skepticism', sa.Float, nullable=False),
        sa.Column('trend_following', sa.Float, nullable=False),
        sa.Column('brand_loyalty', sa.Float, nullable=False),
        sa.Column('social_influence', sa.Float, nullable=False),
        sa.Column('emotion_interest', sa.Float, nullable=False),
        sa.Column('emotion_trust', sa.Float, nullable=False),
        sa.Column('emotion_skepticism', sa.Float, nullable=False),
        sa.Column('emotion_excitement', sa.Float, nullable=False),
        sa.Column('community_id', UUID(as_uuid=True), sa.ForeignKey('communities.community_id'), nullable=False),
        sa.Column('belief', sa.Float, nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('adopted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('exposure_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('llm_tier_used', sa.SmallInteger),
        sa.Column('llm_provider', sa.String(50)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('simulation_id', 'agent_id', 'step', name='uq_agent_states_sim_agent_step'),
    )
    op.create_index('idx_agent_states_sim_step', 'agent_states', ['simulation_id', 'step'])
    op.create_index('idx_agent_states_agent', 'agent_states', ['agent_id', 'step'])

    # --- 9. campaigns (FK → simulations) ---
    op.create_table(
        'campaigns',
        sa.Column('campaign_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('budget', sa.Numeric(15, 2)),
        sa.Column('channels', sa.ARRAY(sa.String), nullable=False, server_default='{}'),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('controversy', sa.Float, nullable=False, server_default='0'),
        sa.Column('novelty', sa.Float, nullable=False, server_default='0.5'),
        sa.Column('utility', sa.Float, nullable=False, server_default='0.5'),
        sa.Column('start_step', sa.Integer, nullable=False, server_default='0'),
        sa.Column('end_step', sa.Integer),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('controversy BETWEEN 0 AND 1', name='ck_campaigns_controversy'),
        sa.CheckConstraint('novelty BETWEEN 0 AND 1', name='ck_campaigns_novelty'),
        sa.CheckConstraint('utility BETWEEN 0 AND 1', name='ck_campaigns_utility'),
    )

    # --- 10. emergent_events (FK → simulations, communities) ---
    op.create_table(
        'emergent_events',
        sa.Column('event_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('step', sa.Integer, nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('community_id', UUID(as_uuid=True), sa.ForeignKey('communities.community_id')),
        sa.Column('severity', sa.Float, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('affected_agent_count', sa.Integer),
        sa.Column('metadata', JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('severity BETWEEN 0 AND 1', name='ck_emergent_events_severity'),
    )
    op.create_index('idx_emergent_simulation', 'emergent_events', ['simulation_id', 'step'])

    # --- 11. agent_memories with pgvector (FK → simulations, agents) ---
    op.create_table(
        'agent_memories',
        sa.Column('memory_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.agent_id', ondelete='CASCADE'), nullable=False),
        sa.Column('memory_type', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('emotion_weight', sa.Float, nullable=False, server_default='0.5'),
        sa.Column('step', sa.Integer, nullable=False),
        sa.Column('social_weight', sa.Float, nullable=False, server_default='0.0'),
        # pgvector column - created via raw SQL
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Add vector column via raw SQL (pgvector)
    op.execute('ALTER TABLE agent_memories ADD COLUMN embedding vector(768)')
    op.create_index('idx_memory_agent', 'agent_memories', ['agent_id', 'step'])
    op.create_index('idx_memory_simulation', 'agent_memories', ['simulation_id'])
    # IVFFlat index requires data to exist; create after initial data load
    # op.execute('CREATE INDEX idx_memory_embedding ON agent_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)')

    # --- 12. llm_calls (FK → simulations, agents) ---
    op.create_table(
        'llm_calls',
        sa.Column('call_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.agent_id')),
        sa.Column('step', sa.Integer, nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('prompt_hash', sa.String(64), nullable=False),
        sa.Column('prompt_tokens', sa.Integer),
        sa.Column('completion_tokens', sa.Integer),
        sa.Column('latency_ms', sa.Float),
        sa.Column('cached', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('tier', sa.SmallInteger, nullable=False, server_default='3'),
        sa.Column('error', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_llm_calls_simulation', 'llm_calls', ['simulation_id', 'step'])
    op.create_index('idx_llm_calls_agent', 'llm_calls', ['agent_id'])

    # --- 13. simulation_events (FK → simulations) ---
    op.create_table(
        'simulation_events',
        sa.Column('event_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('step', sa.Integer),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('payload', JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sim_events_simulation', 'simulation_events', ['simulation_id', 'created_at'])

    # --- 14. expert_opinions (FK → simulations, agents) ---
    op.create_table(
        'expert_opinions',
        sa.Column('opinion_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('expert_agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.agent_id', ondelete='CASCADE'), nullable=False),
        sa.Column('step', sa.Integer, nullable=False),
        sa.Column('score', sa.Float, nullable=False),
        sa.Column('reasoning', sa.Text),
        sa.Column('confidence', sa.Float, nullable=False, server_default='0.5'),
        sa.Column('affects_communities', sa.ARRAY(UUID(as_uuid=True)), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('score BETWEEN -1 AND 1', name='ck_expert_opinions_score'),
        sa.CheckConstraint('confidence BETWEEN 0 AND 1', name='ck_expert_opinions_confidence'),
    )
    op.create_index('idx_expert_opinions_sim', 'expert_opinions', ['simulation_id', 'step'])

    # --- 15. propagation_events (FK → simulations, agents x2) ---
    op.create_table(
        'propagation_events',
        sa.Column('propagation_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('step', sa.Integer, nullable=False),
        sa.Column('source_agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.agent_id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.agent_id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_type', sa.String(20), nullable=False),
        sa.Column('sentiment_polarity', sa.Float),
        sa.Column('source_summary', sa.Text),
        sa.Column('probability', sa.Float, nullable=False),
        sa.Column('message_id', UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_propagation_sim_step', 'propagation_events', ['simulation_id', 'step'])
    op.create_index('idx_propagation_source', 'propagation_events', ['source_agent_id'])
    op.create_index('idx_propagation_target', 'propagation_events', ['target_agent_id'])

    # --- 16. monte_carlo_runs (FK → simulations) ---
    op.create_table(
        'monte_carlo_runs',
        sa.Column('job_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.simulation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),
        sa.Column('n_runs', sa.Integer, nullable=False),
        sa.Column('llm_enabled', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('viral_probability', sa.Float),
        sa.Column('expected_reach', sa.Float),
        sa.Column('p5_reach', sa.Float),
        sa.Column('p50_reach', sa.Float),
        sa.Column('p95_reach', sa.Float),
        sa.Column('community_adoption', JSONB),
        sa.Column('run_summaries', JSONB),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_monte_carlo_sim', 'monte_carlo_runs', ['simulation_id'])

    # --- 17. users (RBAC — no FK dependencies) ---
    op.create_table(
        'users',
        sa.Column('user_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='viewer'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_users_username', 'users', ['username'], unique=True)


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table('users')
    op.drop_table('monte_carlo_runs')
    op.drop_table('propagation_events')
    op.drop_table('expert_opinions')
    op.drop_table('simulation_events')
    op.drop_table('llm_calls')
    op.drop_table('agent_memories')
    op.drop_table('emergent_events')
    op.drop_table('campaigns')
    op.drop_table('agent_states')
    op.drop_table('scenarios')
    op.drop_table('network_edges')
    op.drop_table('sim_steps')
    op.drop_table('agents')
    op.drop_table('communities')
    op.drop_table('projects')
    op.drop_table('simulations')
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')
    op.execute('DROP EXTENSION IF EXISTS vector')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
