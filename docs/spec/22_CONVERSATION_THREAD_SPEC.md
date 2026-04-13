# SPEC 22 — Conversation Thread Persistence

> Version: 0.1.0
> Updated: 2026-04-10
> Status: CURRENT

---

## Overview

Replace synthetic hardcoded conversation threads with real agent-generated
content captured during simulation execution.

| ID | Feature | Target Module |
|----|---------|---------------|
| CT-01~03 | **Thread Capture** | `app.engine.agent.tick`, `app.engine.simulation.community_orchestrator` |
| CT-04~05 | **Thread Storage** | `app.db.models.thread`, `app.engine.simulation.persistence` |
| CT-06~08 | **Thread API** | `app.api.communities` |

---

## Motivation

The `/communities/{id}/threads` endpoint currently returns synthetic messages
from hardcoded template arrays (`_PROGRESSIVE_MSGS`, `_CONSERVATIVE_MSGS`,
etc.). This provides no insight into actual agent behavior during simulation.

Real conversation threads capture what agents "said" during propagation events,
making simulation results more interpretable and enabling qualitative analysis
of information diffusion.

---

## Design Principle

Thread messages are derived from **PropagationEvent + agent content generation**
(SPEC 20 CG-01~04). Each propagation event where the agent takes a visible
action (COMMENT, SHARE, REPOST, ADOPT) produces a thread message. Tier 3
agents use `generated_content` from LLM; Tier 1/2 agents use the campaign
message or a stance-derived template.

---

## `1 CT: Thread Capture

### `1.1 Data Types

**CT-01** -- Thread message captured during simulation:

```python
@dataclass
class ThreadMessage:
    message_id: UUID
    simulation_id: UUID
    community_id: UUID
    agent_id: UUID
    step: int
    action: str              # AgentAction value
    content: str             # generated or template-derived content
    belief: float            # agent's belief at time of message
    emotion_valence: float   # mean emotion at time of message
    reply_to_id: UUID | None # if replying to a neighbor's action
    created_at: datetime
```

**CT-02** -- Thread summary derived from stored messages:

```python
@dataclass
class ThreadSummary:
    thread_id: str           # community_id-thread-{step_range}
    community_id: UUID
    topic: str               # derived from dominant action + campaign
    participant_count: int
    message_count: int
    avg_sentiment: float
    step_range: tuple[int, int]
```

### `1.2 Capture Logic

**CT-03** -- After each community tick, collect thread messages from
propagation events and agent tick results:

```python
def collect_thread_messages(
    community_id: UUID,
    simulation_id: UUID,
    step: int,
    tick_results: list[AgentTickResult],
    agents: dict[UUID, AgentState],
    campaign_message: str,
) -> list[ThreadMessage]:
    """Extract thread messages from agent actions in a step.

    Rules:
    - IGNORE actions do not produce messages
    - COMMENT/SHARE/REPOST/ADOPT produce messages
    - Content source: PropagationEvent.generated_content (Tier 3)
      or stance-based template (Tier 1/2)
    - reply_to_id links to the first neighbor whose action triggered this
    """
```

---

## `2 CT: Thread Storage

**CT-04** -- DB table `thread_messages`:

```sql
CREATE TABLE thread_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id UUID NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    community_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    step INT NOT NULL,
    action VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    belief FLOAT NOT NULL DEFAULT 0.0,
    emotion_valence FLOAT NOT NULL DEFAULT 0.0,
    reply_to_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_thread_sim_community ON thread_messages(simulation_id, community_id, step);
```

**CT-05** -- `SimulationPersistence.persist_thread_messages()`:
Fire-and-forget batch insert, same pattern as `persist_agent_memories()`.

---

## `3 CT: Thread API

**CT-06** -- `GET /communities/{community_id}/threads`:
Returns thread summaries grouped by step ranges (every 5 steps = 1 thread).
Falls back to synthetic generation if no stored messages exist (backward compat).

**CT-07** -- `GET /communities/{community_id}/threads/{thread_id}`:
Returns individual messages for the specified thread (step range).

**CT-08** -- Response format unchanged from current API contract.

---

## Acceptance Criteria

| Test ID | Assertion |
|---------|-----------|
| CT-AC-01 | collect_thread_messages returns empty for all-IGNORE step |
| CT-AC-02 | SHARE action produces message with campaign content for Tier 1 |
| CT-AC-03 | ADOPT action produces message with generated_content for Tier 3 |
| CT-AC-04 | persist_thread_messages writes to DB |
| CT-AC-05 | GET /threads returns real messages when available |
| CT-AC-06 | GET /threads falls back to synthetic when no messages stored |
| CT-AC-07 | Thread grouping by step range works correctly |

---

## Implementation Order

1. CT-01~02: Data types
2. CT-03: Capture logic in community_orchestrator
3. CT-04~05: DB model + persistence
4. CT-06~08: API update

All must pass: `uv run pytest tests/test_22_conversation_threads.py -v`
