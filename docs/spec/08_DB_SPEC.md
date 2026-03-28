# 08 — Database SPEC (PostgreSQL 16 + pgvector)
Version: 0.1.1 | Status: DRAFT

---

## 1. Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- for text search on memory content
```

---

## 2. Schema

### simulations

```sql
CREATE TABLE simulations (
    simulation_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    status          VARCHAR(50) NOT NULL DEFAULT 'created',
                    -- created | configured | running | paused | completed | failed
    current_step    INTEGER NOT NULL DEFAULT 0,
    max_steps       INTEGER NOT NULL DEFAULT 50,
    config          JSONB NOT NULL,         -- full SimulationConfig as JSON
    network_metrics JSONB,                  -- NetworkMetrics snapshot at creation
    random_seed     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT
);

CREATE INDEX idx_simulations_status ON simulations(status);
```

---

### communities

```sql
CREATE TABLE communities (
    community_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    community_key   VARCHAR(10) NOT NULL,   -- 'A', 'B', 'C', 'D', 'E'
    agent_type      VARCHAR(50) NOT NULL,
    size            INTEGER NOT NULL,
    config          JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_communities_simulation ON communities(simulation_id);
```

---

### agents

```sql
CREATE TABLE agents (
    agent_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    community_id    UUID NOT NULL REFERENCES communities(community_id),
    agent_type      VARCHAR(50) NOT NULL,
    -- Initial personality (reference values; current state in agent_states)
    openness            FLOAT NOT NULL CHECK (openness BETWEEN 0 AND 1),
    skepticism          FLOAT NOT NULL CHECK (skepticism BETWEEN 0 AND 1),
    trend_following     FLOAT NOT NULL CHECK (trend_following BETWEEN 0 AND 1),
    brand_loyalty       FLOAT NOT NULL CHECK (brand_loyalty BETWEEN 0 AND 1),
    social_influence    FLOAT NOT NULL CHECK (social_influence BETWEEN 0 AND 1),
    -- Initial emotion
    emotion_interest    FLOAT NOT NULL DEFAULT 0.5,
    emotion_trust       FLOAT NOT NULL DEFAULT 0.5,
    emotion_skepticism  FLOAT NOT NULL DEFAULT 0.5,
    emotion_excitement  FLOAT NOT NULL DEFAULT 0.3,
    -- Network position
    network_node_id     INTEGER,            -- NetworkX node ID
    influence_score     FLOAT,
    llm_provider        VARCHAR(50),        -- overrides simulation default if set
    activity_vector     FLOAT[24],          -- 24-dim hourly activity probability (OASIS-inspired)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agents_simulation ON agents(simulation_id);
CREATE INDEX idx_agents_community ON agents(community_id);
```

---

### network_edges

```sql
CREATE TABLE network_edges (
    edge_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    source_node_id  INTEGER NOT NULL,
    target_node_id  INTEGER NOT NULL,
    weight          FLOAT NOT NULL CHECK (weight BETWEEN 0 AND 1),
    is_bridge       BOOLEAN NOT NULL DEFAULT FALSE,  -- cross-community edge
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(simulation_id, source_node_id, target_node_id)
);

CREATE INDEX idx_edges_simulation ON network_edges(simulation_id);
CREATE INDEX idx_edges_source ON network_edges(simulation_id, source_node_id);
```

---

### sim_steps

```sql
CREATE TABLE sim_steps (
    step_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id       UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    step                INTEGER NOT NULL,
    total_adoption      INTEGER NOT NULL DEFAULT 0,
    adoption_rate       FLOAT NOT NULL DEFAULT 0,
    diffusion_rate      FLOAT NOT NULL DEFAULT 0,
    mean_sentiment      FLOAT NOT NULL DEFAULT 0,
    sentiment_variance  FLOAT NOT NULL DEFAULT 0,
    action_distribution JSONB NOT NULL DEFAULT '{}',  -- {action: count}
    community_metrics   JSONB NOT NULL DEFAULT '{}',  -- {community_id: CommunityStepMetrics}
    llm_calls_count     INTEGER NOT NULL DEFAULT 0,
    llm_tier_distribution JSONB,
    step_duration_ms    FLOAT,
    replay_id           UUID,           -- NULL for original, UUID for replay branches
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(simulation_id, step, replay_id)
);

CREATE INDEX idx_steps_simulation_step ON sim_steps(simulation_id, step);
```

---

### agent_states

```sql
-- Stores agent state snapshot per step (only for changed agents by default)
CREATE TABLE agent_states (
    state_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    agent_id        UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    step            INTEGER NOT NULL,
    -- Current personality
    openness            FLOAT NOT NULL,
    skepticism          FLOAT NOT NULL,
    trend_following     FLOAT NOT NULL,
    brand_loyalty       FLOAT NOT NULL,
    social_influence    FLOAT NOT NULL,
    -- Current emotion
    emotion_interest    FLOAT NOT NULL,
    emotion_trust       FLOAT NOT NULL,
    emotion_skepticism  FLOAT NOT NULL,
    emotion_excitement  FLOAT NOT NULL,
    -- State
    community_id    UUID NOT NULL REFERENCES communities(community_id), -- tracks community migration
    belief          FLOAT NOT NULL,
    action          VARCHAR(20) NOT NULL,   -- 12 actions: ignore|view|search|like|save|comment|share|repost|follow|unfollow|adopt|mute
    adopted         BOOLEAN NOT NULL DEFAULT FALSE,
    exposure_count  INTEGER NOT NULL DEFAULT 0,
    llm_tier_used   SMALLINT,
    llm_provider    VARCHAR(50),            -- per-agent LLM provider override (nullable = use default)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(simulation_id, agent_id, step)
);

CREATE INDEX idx_agent_states_sim_step ON agent_states(simulation_id, step);
CREATE INDEX idx_agent_states_agent ON agent_states(agent_id, step);
```

---

### campaigns

```sql
CREATE TABLE campaigns (
    campaign_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    budget          NUMERIC(15, 2),
    channels        TEXT[] NOT NULL DEFAULT '{}',
    message         TEXT NOT NULL,
    controversy     FLOAT NOT NULL DEFAULT 0 CHECK (controversy BETWEEN 0 AND 1),
    novelty         FLOAT NOT NULL DEFAULT 0.5 CHECK (novelty BETWEEN 0 AND 1),
    utility         FLOAT NOT NULL DEFAULT 0.5 CHECK (utility BETWEEN 0 AND 1),
    start_step      INTEGER NOT NULL DEFAULT 0,
    end_step        INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### emergent_events

```sql
CREATE TABLE emergent_events (
    event_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    step            INTEGER NOT NULL,
    event_type      VARCHAR(50) NOT NULL,
                    -- viral_cascade | slow_adoption | polarization | collapse | echo_chamber
    community_id    UUID REFERENCES communities(community_id),
    severity        FLOAT NOT NULL CHECK (severity BETWEEN 0 AND 1),
    description     TEXT,
    affected_agent_count INTEGER,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_emergent_simulation ON emergent_events(simulation_id, step);
```

---

### agent_memories (pgvector)

```sql
CREATE TABLE agent_memories (
    memory_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    agent_id        UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    memory_type     VARCHAR(20) NOT NULL,   -- episodic | semantic | social
    content         TEXT NOT NULL,
    emotion_weight  FLOAT NOT NULL DEFAULT 0.5,
    step            INTEGER NOT NULL,
    social_weight   FLOAT NOT NULL DEFAULT 0.0,  -- social importance of this memory
    embedding       vector(768),            -- pgvector: normalized to 768-dim
                                            -- NULL if embedding not available
                                            -- NOTE: if LLM returns other dim (e.g. OpenAI 1536),
                                            -- embedding must be projected to 768-dim before storage
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- pgvector IVFFlat index for fast approximate nearest neighbor
CREATE INDEX idx_memory_embedding
    ON agent_memories
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Also index by agent for non-vector retrieval
CREATE INDEX idx_memory_agent ON agent_memories(agent_id, step DESC);
CREATE INDEX idx_memory_simulation ON agent_memories(simulation_id);
```

**Memory retrieval query:**
```sql
-- Top-K memories by composite score (α=0.3, β=0.4, γ=0.2, δ=0.1)
-- step_age = current_step - agent_memories.step
SELECT *,
    (0.3 * (1.0 / (1 + ($1 - step))))  AS recency_score,    -- $1 = current_step
    (0.4 * (1 - (embedding <=> $2)))    AS relevance_score,  -- $2 = query embedding
    (0.2 * emotion_weight)              AS emotion_score,
    (0.1 * social_weight)               AS social_score      -- social_weight column
FROM agent_memories
WHERE agent_id = $3
  AND embedding IS NOT NULL
ORDER BY (recency_score + relevance_score + emotion_score + social_score) DESC
LIMIT $4;

-- Fallback (no embedding available): recency + emotion only
SELECT *,
    (0.6 * (1.0 / (1 + ($1 - step))))  AS recency_score,
    (0.3 * emotion_weight)              AS emotion_score,
    (0.1 * social_weight)               AS social_score
FROM agent_memories
WHERE agent_id = $2
ORDER BY (recency_score + emotion_score + social_score) DESC
LIMIT $3;
```

---

### llm_calls

```sql
CREATE TABLE llm_calls (
    call_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    agent_id        UUID REFERENCES agents(agent_id),
    step            INTEGER NOT NULL,
    provider        VARCHAR(50) NOT NULL,
    model           VARCHAR(100) NOT NULL,
    prompt_hash     VARCHAR(64) NOT NULL,  -- SHA256 for dedup/cache tracking
    prompt_tokens   INTEGER,
    completion_tokens INTEGER,
    latency_ms      FLOAT,
    cached          BOOLEAN NOT NULL DEFAULT FALSE,
    tier            SMALLINT NOT NULL DEFAULT 3,
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_llm_calls_simulation ON llm_calls(simulation_id, step);
CREATE INDEX idx_llm_calls_agent ON llm_calls(agent_id);
```

---

### simulation_events (audit / intervention log)

```sql
CREATE TABLE simulation_events (
    event_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    step            INTEGER,
    event_type      VARCHAR(50) NOT NULL,
                    -- status_change | agent_modified | event_injected | step_completed | replay_created
    payload         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sim_events_simulation ON simulation_events(simulation_id, created_at DESC);
```

---

### expert_opinions

```sql
CREATE TABLE expert_opinions (
    opinion_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    expert_agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    step            INTEGER NOT NULL,
    score           FLOAT NOT NULL CHECK (score BETWEEN -1 AND 1),
    reasoning       TEXT,
    confidence      FLOAT NOT NULL DEFAULT 0.5 CHECK (confidence BETWEEN 0 AND 1),
    affects_communities UUID[] NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_expert_opinions_sim ON expert_opinions(simulation_id, step);
```

---

### propagation_events

```sql
CREATE TABLE propagation_events (
    propagation_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    step            INTEGER NOT NULL,
    source_agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    target_agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    action_type     VARCHAR(20) NOT NULL,   -- share | comment | repost | adopt (passive)
    sentiment_polarity FLOAT,               -- -1.0 to 1.0 from source agent's ContextualPacket
    source_summary  TEXT,                   -- SLM-generated reasoning summary (from ContextualPacket)
    probability     FLOAT NOT NULL,
    message_id      UUID,                   -- campaign message reference
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_propagation_sim_step ON propagation_events(simulation_id, step);
CREATE INDEX idx_propagation_source ON propagation_events(source_agent_id);
CREATE INDEX idx_propagation_target ON propagation_events(target_agent_id);
```

---

### monte_carlo_runs

```sql
CREATE TABLE monte_carlo_runs (
    job_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    status          VARCHAR(20) NOT NULL DEFAULT 'queued',
                    -- queued | running | completed | failed
    n_runs          INTEGER NOT NULL,
    llm_enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    -- Results (populated on completion)
    viral_probability   FLOAT,
    expected_reach      FLOAT,
    p5_reach            FLOAT,
    p50_reach           FLOAT,
    p95_reach           FLOAT,
    community_adoption  JSONB,              -- {community_id: adoption_rate}
    run_summaries       JSONB,              -- [{run_index, final_adoption, viral, steps}]
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_monte_carlo_sim ON monte_carlo_runs(simulation_id);
```

---

## 3. Key Queries

### Get simulation dashboard data
```sql
-- Latest step metrics
SELECT * FROM sim_steps
WHERE simulation_id = $1
ORDER BY step DESC LIMIT 1;

-- Community metrics are stored as JSONB in sim_steps.community_metrics
SELECT step, community_metrics
FROM sim_steps
WHERE simulation_id = $1 AND step = $2;
```

### Agent state at step (with fallback to last known state)
```sql
SELECT DISTINCT ON (agent_id) *
FROM agent_states
WHERE simulation_id = $1 AND step <= $2
ORDER BY agent_id, step DESC;
```

### Network graph for visualization
```sql
SELECT
    a.agent_id, a.agent_type, c.community_key,
    ast.action, ast.adopted, ast.belief,
    ast.emotion_excitement, ast.emotion_trust,
    a.influence_score
FROM agents a
JOIN communities c USING (community_id)
LEFT JOIN agent_states ast
    ON ast.agent_id = a.agent_id
    AND ast.simulation_id = $1
    AND ast.step = $2
WHERE a.simulation_id = $1;
```

---

## 4. Migrations

Using **Alembic** (async). Migration files in `backend/migrations/versions/`.

```
backend/migrations/
    env.py
    script.py.mako
    versions/
        001_initial_schema.py
        002_add_pgvector_memory.py
        003_add_llm_calls.py
```

---

## 5. Error Specification

| Situation | Exception Type | Recovery | Logging |
|-----------|---------------|----------|---------|
| UNIQUE constraint violation on INSERT | `IntegrityError` | Return existing record (idempotent upsert) or reject with 409 | WARN |
| Foreign key violation (orphan reference) | `IntegrityError` | Reject operation, return descriptive error | ERROR |
| CASCADE DELETE exceeds safety limit (>10K rows) | — (guard) | Require explicit `force=True` flag; reject without it | WARN |
| pgvector extension not installed | `PgVectorUnavailableError` | Fallback to recency-only memory retrieval (no cosine similarity) | ERROR (once at startup) |
| pgvector IVFFlat index not built | — (degraded) | Use sequential scan (slower); log performance warning | WARN (once per query batch) |
| Connection pool exhausted | `ConnectionPoolExhaustedError` | Queue request with 5s timeout; if timeout → 503 | ERROR |
| Alembic migration conflict (dual heads) | `MigrationConflictError` | Reject startup — manual merge required | CRITICAL |
| Concurrent write deadlock | — (retry) | Auto-retry with exponential backoff (max 3 retries) | WARN |
| `agent_states` INSERT with NULL `community_id` | `IntegrityError` | Reject — `community_id` is NOT NULL | ERROR |
| Embedding dimension mismatch on INSERT | `ValueError` | Reject INSERT — must match configured dim (768) | ERROR |
| Query timeout (>10s) | — (cancel) | Cancel query, return 504 timeout | WARN |
| Disk space critical (<1GB) | — (alert) | Log alert, reject non-essential writes (e.g., LLM cache) | CRITICAL |

---

## 6. Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| DB-01 | INSERT simulation + SELECT back | All fields match |
| DB-02 | pgvector nearest-neighbor query on agent_memories | Returns top-K ordered by cosine similarity |
| DB-03 | agent_states DISTINCT ON query returns last state per agent | Correct step fallback |
| DB-04 | CASCADE DELETE simulation removes all child records | 0 orphaned records |
| DB-05 | IVFFlat index query within 10ms for 100K memories | Performance benchmark |
| DB-06 | Alembic migrations apply cleanly on fresh DB | No errors |
| DB-07 | Concurrent writes from asyncio tasks don't deadlock | 100 concurrent inserts succeed |
| DB-08 | INSERT propagation_event + SELECT by step | Correct source/target pairs |
| DB-09 | INSERT expert_opinion + SELECT by simulation | Score in [-1, 1] |
| DB-10 | INSERT monte_carlo_run + UPDATE status/results | Status transitions work |
| DB-11 | agent_states.community_id tracks community migration | Correct after PATCH agent |
| DB-12 | Memory fallback query (no embedding) returns by recency | Correct ordering |
