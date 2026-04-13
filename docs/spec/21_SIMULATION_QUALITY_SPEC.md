# SPEC 21 — Simulation Quality (Consolidated P1 + P2 + P3)

> Version: 0.2.0
> Updated: 2026-04-10
> Status: CURRENT
> Supersedes: `19_SIMULATION_QUALITY_SPEC.md`, `20_SIMULATION_QUALITY_P2_SPEC.md`,
> `21_SIMULATION_QUALITY_P3_SPEC.md` (merged into this single document)

---

## Overview

A quality improvement series that incrementally enhances agent simulation realism.
Originally split across three SPECs (`19_P1`, `20_P2`, `21_P3`), they were merged
into a single SPEC to resolve the `19_*` / `20_*` number collision and simplify the
index. Each phase's anchor IDs (`SQ-`, `EC-`, `BC-`, `CG-`, `RF-`, `HM-`, `MP-`)
are preserved as-is, so code docstring references only need the filename updated.

### Phase Summary

| Phase | Scope | ID Prefix | Target Module |
|-------|-------|-----------|---------------|
| **P1** | Fatigue / Edge Weight / Expert Score / Prompt Injection | `SQ-` | `agent.fatigue`, `agent.perception`, `llm.prompt_builder` |
| **P2** | Emotional Contagion / Bounded Confidence / Content Generation | `EC-`, `BC-`, `CG-` | `agent.emotion`, `diffusion.opinion_dynamics`, `llm.prompt_builder` |
| **P3** | Agent Reflection / Homophily / Memory Persistence | `RF-`, `HM-`, `MP-` | `agent.reflection`, `network.generator`, `agent.memory`, `db.models` |

---

# Phase 1 — Immediate Quality Wins

Defines Phase 1 improvements derived from an agent simulation expert review.
Consists of 4 items that require minimal code changes and immediately improve
simulation realism.

## SQ-01: Fatigue / Saturation Model (Exposure Fatigue)

### Problem
`AgentState.exposure_count` is tracked every step but is not used to reduce
receptivity on repeated exposure. In real social media, ad fatigue from repeated
advertising is a core phenomenon.

### Contract

**`ExposureFatigue.compute_fatigue_factor(exposure_count: int) -> float`**

```
Input:  exposure_count — cumulative exposure count for the agent (>= 0)
Output: fatigue_factor — receptivity multiplier in the range [0.1, 1.0]
```

- exposure_count == 0 → fatigue_factor = 1.0 (maximum receptivity)
- exposure_count >= SATURATION_THRESHOLD (default 20) → fatigue_factor = MIN_FACTOR (0.1)
- in between: exponential decay `1.0 * decay_rate ^ exposure_count` (decay_rate=0.85)
- fatigue_factor is always clamped to [MIN_FACTOR, 1.0]

**Application point:** `PerceptionLayer.observe()` — `exposure_score *= fatigue_factor` when computing the exposure score

**No changes to AgentState** — reuses the existing `exposure_count` field.

### Configuration
```python
class FatigueConfig:
    saturation_threshold: int = 20   # above this count, MIN_FACTOR is fixed
    decay_rate: float = 0.85          # decay rate per step (exponential decay)
    min_factor: float = 0.1           # minimum receptivity multiplier
```

---

## SQ-02: Real Edge Weight Reflection (Perception Social Signals)

### Problem
`perception.py` hard-codes `edge_weight = 1.0`, so the trust/affinity of
network edges is not reflected in social signals.

### Contract

**`PerceptionLayer.observe()`** — when processing `neighbor_actions`:

```
New input: edge_weights: dict[UUID, float] | None = None
           per-agent trust weights (neighbor_id -> edge_weight)
```

- If `edge_weights` is not None and contains `na.agent_id`, use the real edge_weight
- If `edge_weights` is None or the neighbor_id is absent, fallback = 1.0 (preserves existing behavior)
- `weighted_score = action_weight * edge_weight` (existing formula preserved, weight is now real)

**`PerceptionLayer.observe()` signature change:**
```python
def observe(
    self,
    agent: AgentState,
    environment_events: list[EnvironmentEvent],
    neighbor_actions: list[NeighborAction],
    edge_weights: dict[UUID, float] | None = None,   # NEW — None default for backward compat
) -> PerceptionResult:
```

**Caller change:** `AgentTick._run_agent_tick()` passes trust_matrix as edge_weights.

---

## SQ-03: Expert Opinion Score Dynamic Calculation

### Problem
`perception.py` hard-codes `opinion_score = 0.5`, so the influence difference
between individual experts is not reflected.

### Contract

**`PerceptionLayer.observe()`** — when processing `expert_review` events:

The expert's `opinion_score` is dynamically calculated using the formula below:
```
opinion_score = clip(
    event.controversy * (1 - agent.personality.skepticism) * channel_boost,
    0.0, 1.0
)
```

- `event.controversy`: parsed from `EnvironmentEvent.message` or default 0.7
  (when passed as a payload dict: `payload.get("controversy", 0.7)`)
- `channel_boost`: channel == "direct" → 1.2, else → 1.0
- `credibility`: `1.0 - agent.personality.skepticism` (inversely proportional to agent skepticism)
- opinion_score range: clamped to [0.0, 1.0]

**`EnvironmentEvent` change:**
```python
controversy: float = 0.5   # NEW optional field — event controversiality (0=neutral, 1=high controversy)
```

---

## SQ-04: Prompt Injection Defense

### Problem
In `prompt_builder.py`, campaign messages are inserted directly into prompts via
f-strings. Malicious campaign messages can corrupt LLM instructions.

### Contract

**`PromptBuilder.sanitize_content(content: str) -> str`**

```
Input:  content   — user/campaign-supplied string
Output: sanitized — safe string with injection patterns removed
```

Processing rules:
1. Length limit: truncate when exceeding 500 characters + append "...[truncated]"
2. Separator isolation: replace prompt structure tokens such as `---`, `###`,
   `"""`, `'''`, `<|`, `|>`, `[INST]`, `[/INST]`, `<system>`, `</system>` with `[SEP]`
3. Newline compression: 3 or more consecutive newlines → compressed to 2
4. Remove null bytes and non-printable characters (`\x00`–`\x1f`, `\x7f`, except `\n\r\t`)

**`PromptBuilder.build_agent_cognition_prompt()` change:**
```python
# Before (vulnerable)
campaign_message = getattr(campaign, "message", str(campaign))

# After (defended)
campaign_message = self.sanitize_content(
    getattr(campaign, "message", str(campaign))
)
```

Isolate campaign message in the user section with explicit boundaries:
```
<campaign_content>
{sanitized_campaign_message}
</campaign_content>
```

---

## Phase 1 Test Requirements

Backend: `backend/tests/test_21_simulation_quality_p1.py`

| Test | Description |
|------|-------------|
| `TestExposureFatigue::test_zero_exposure_returns_1` | exposure_count=0 → 1.0 |
| `TestExposureFatigue::test_high_exposure_returns_min` | >= saturation → MIN_FACTOR |
| `TestExposureFatigue::test_fatigue_is_monotonically_decreasing` | verify monotonically decreasing |
| `TestExposureFatigue::test_fatigue_applied_in_perception` | reflected in PerceptionLayer |
| `TestEdgeWeightPerception::test_uses_real_edge_weight` | edge_weights actually applied |
| `TestEdgeWeightPerception::test_fallback_to_1_when_none` | fallback to 1.0 when None |
| `TestExpertOpinionScore::test_dynamic_score_range` | range [0.0, 1.0] |
| `TestExpertOpinionScore::test_skeptic_reduces_credibility` | skeptic agent has lower credibility |
| `TestPromptInjection::test_sanitize_removes_prompt_tokens` | separator tokens removed |
| `TestPromptInjection::test_sanitize_truncates_long_content` | truncated when exceeding 500 chars |
| `TestPromptInjection::test_campaign_content_isolated_in_prompt` | isolated with XML tags |
| `TestPromptInjection::test_normal_content_unchanged` | normal text unchanged |

---

# Phase 2 — Social Realism Extensions

Phase 2 extends agent social realism in three dimensions:

| ID | Feature | Target Module |
|----|---------|---------------|
| EC-01~04 | **Emotional Contagion** | `app.engine.agent.emotion` |
| BC-01~07 | **Bounded Confidence Opinion Dynamics** | `app.engine.diffusion.opinion_dynamics` (NEW) |
| CG-01~04 | **Agent Content Generation** | `app.llm.prompt_builder`, `app.llm.gateway` |

## §P2.1 — EC: Emotional Contagion

### Motivation

Currently `EmotionLayer.update()` responds only to campaign signals (media/social/expert
scalars). Neighbor agents' actual emotional states are ignored. In real social networks,
emotion spreads through ties — excited neighbors make you excited; skeptical neighbors
make you skeptical. (Hatfield et al. 1993, Kramer et al. 2014)

### New Parameter: `neighbor_emotions`

**EC-01** — `EmotionLayer.update()` MUST accept an optional
`neighbor_emotions: list[tuple[AgentEmotion, float]] | None = None` parameter.
Each tuple is `(AgentEmotion, edge_weight)`.

Backward compatibility: `None` (default) → no change in behavior.

**EC-02** — When `neighbor_emotions` is provided and non-empty, apply weighted-mean
contagion to `excitement` and `skepticism` dimensions only:

```
mean_excitement = Σ(e.excitement * w) / Σ(w)   for (e, w) in neighbor_emotions
mean_skepticism = Σ(e.skepticism * w) / Σ(w)

contagion_excitement = CONTAGION_ALPHA * (mean_excitement - current.excitement)
contagion_skepticism = CONTAGION_ALPHA * (mean_skepticism - current.skepticism)

new_excitement = clamp(updated_excitement + contagion_excitement, 0.0, 1.0)
new_skepticism = clamp(updated_skepticism + contagion_skepticism, 0.0, 1.0)
```

Where `CONTAGION_ALPHA = 0.15` (class constant, configurable via constructor).

**EC-03** — `interest` and `trust` dimensions are NOT affected by contagion (they
respond to content quality, not peer emotion).

**EC-04** — If `Σ(w) == 0`, skip contagion (no-op). Never raise; return the
signal-only updated emotion.

### Call Site

`EmotionLayer.update()` is called from `CognitionLayer._run_heuristic()` (Tier 2)
and from the Tier 3 LLM pathway. The step_runner supplies `edge_weights` for each
agent; these same weights MUST be passed as `neighbor_emotions` tuples.

```python
neighbor_emotions = [
    (neighbor_agent.emotion, edge_weights.get(neighbor_id, 1.0))
    for neighbor_id, neighbor_agent in neighbor_map.items()
]
```

### Acceptance Criteria

| Test ID | Assertion |
|---------|-----------|
| EC-AC-01 | update() with no neighbor_emotions matches original behavior exactly |
| EC-AC-02 | update() with high-excitement neighbors raises agent excitement |
| EC-AC-03 | update() with high-skepticism neighbors raises agent skepticism |
| EC-AC-04 | interest and trust are unaffected by neighbor_emotions |
| EC-AC-05 | zero-weight neighbors → no contagion effect |

---

## §P2.2 — BC: Bounded Confidence Opinion Dynamics

### Motivation

Currently belief updates are unconstrained: any propagation event can shift an
agent's belief regardless of how far the source and target beliefs are apart.
This produces unrealistically rapid consensus. The Deffuant (2000) Bounded
Confidence model corrects this: agents only shift toward peers whose opinions
fall within a confidence threshold ε.

### New Module: `app.engine.diffusion.opinion_dynamics`

**BC-01** — Create `OpinionDynamicsModel` class with method:

```python
def update_belief(
    self,
    agent_belief: float,         # current agent belief [-1.0, 1.0]
    neighbor_belief: float,      # neighbor's belief [-1.0, 1.0]
    edge_weight: float = 1.0,    # trust weight [0.0, 1.0]
) -> float:
    """Apply Deffuant bounded confidence update.

    Returns the new agent belief (unchanged if |delta| >= epsilon).
    """
```

**BC-02** — Deffuant update rule:

```
delta = |agent_belief - neighbor_belief|
if delta >= epsilon:
    return agent_belief   # no update — outside confidence bound

shift = mu * edge_weight * (neighbor_belief - agent_belief)
new_belief = clamp(agent_belief + shift, -1.0, 1.0)
return new_belief
```

Constants (configurable via constructor):
- `epsilon: float = 0.3` — confidence bound (max tolerable opinion gap)
- `mu: float = 0.5` — convergence rate [0.0, 1.0]

**BC-03** — `OpinionDynamicsModel` MUST expose a batch update method:

```python
def batch_update(
    self,
    agent_belief: float,
    neighbor_beliefs: list[tuple[float, float]],  # (belief, edge_weight)
) -> float:
    """Apply Deffuant update from multiple neighbors sequentially.

    Processes neighbors in belief-proximity order (closest first).
    Returns final belief after all within-bound neighbors applied.
    """
```

**BC-04** — Integration in `step_runner.py`:
After propagation events are generated for a community step, apply
`OpinionDynamicsModel.batch_update()` for each agent using the beliefs of
agents that sent propagation events to it in this step.

**BC-05** — The model MUST be deterministic: given the same inputs, always
return the same output. No RNG.

### Acceptance Criteria

| Test ID | Assertion |
|---------|-----------|
| BC-AC-01 | Neighbors within epsilon shift agent belief toward them |
| BC-AC-02 | Neighbors outside epsilon do NOT shift agent belief |
| BC-AC-03 | Higher edge_weight produces larger shift (within epsilon) |
| BC-AC-04 | belief remains clamped to [-1.0, 1.0] after update |
| BC-AC-05 | batch_update processes closest neighbors first |
| BC-AC-06 | mu=0 → no shift regardless of epsilon |
| BC-AC-07 | epsilon=0 → no update (delta always >= 0) |

---

## §P2.3 — CG: Agent Content Generation

### Motivation

When agents SHARE or COMMENT, they currently attach the original campaign message
verbatim. Real social sharing mutates content — agents add personal framing,
endorsement, or critique. This drives emergent narrative variation in the simulation.

### New Prompt Template

**CG-01** — `PromptBuilder.build_content_generation_prompt()`:

```python
def build_content_generation_prompt(
    self,
    agent: Any,
    original_content: str,
    action: AgentAction,
    step: int,
) -> LLMPrompt:
```

Returns an `LLMPrompt` with `max_tokens=128`.

System: agent identity + role context.
User: original content + action type + instruction to write a short post (≤ 140 chars).

Response format: JSON with key `generated_text: str`.

**CG-02** — The generated text MUST be sanitized via `sanitize_content()` before
being embedded in the prompt.

**CG-03** — `PropagationEvent.generated_content: str | None = None` (NEW FIELD).
When a Tier 3 agent generates content, it is stored here.

**CG-04** — Content generation is ONLY triggered for Tier 3 (Elite LLM) agents.
Tier 1 and Tier 2 agents propagate the original `campaign_message` unchanged.
If Tier 3 LLM call fails, fall back to original campaign_message (no crash).

### Acceptance Criteria

| Test ID | Assertion |
|---------|-----------|
| CG-AC-01 | build_content_generation_prompt returns LLMPrompt with max_tokens=128 |
| CG-AC-02 | system prompt includes agent identity |
| CG-AC-03 | user prompt includes original_content (sanitized) and action |
| CG-AC-04 | PropagationEvent.generated_content field exists and defaults to None |

---

# Phase 3 — Strategic Depth

Phase 3 adds strategic depth and realism to agent behavior and network structure.

| ID | Feature | Target Module |
|----|---------|---------------|
| RF-01~05 | **Agent Reflection** | `app.engine.agent.reflection` (NEW) |
| HM-01~04 | **Homophily Edge Weighting** | `app.engine.network.generator` |
| MP-01~04 | **Memory Persistence** | `app.engine.agent.memory`, `app.db.models` |

## §P3.1 — RF: Agent Reflection (Simulacra-style)

### Motivation

Tier 3 agents currently process each stimulus independently. Real humans periodically
reflect on accumulated experience — "What have I learned?", "Am I changing my mind?"
(Park et al. 2023, Generative Agents). Periodic reflection enables belief revision
that transcends individual events.

### New Module: `app.engine.agent.reflection`

**RF-01** — Create `ReflectionEngine` class:

```python
class ReflectionEngine:
    def should_reflect(
        self,
        memory_count_since_last: int,
        step: int,
        last_reflection_step: int,
    ) -> bool:
        """Returns True when agent should perform reflection.

        Conditions (ANY triggers reflection):
        - memory_count_since_last >= MEMORY_THRESHOLD (default: 5)
        - step - last_reflection_step >= STEP_INTERVAL (default: 10)
        """

    def build_reflection_input(
        self,
        recent_memories: list[MemoryRecord],
        current_belief: float,
    ) -> ReflectionInput:
        """Prepare structured input for LLM or heuristic reflection."""

    def apply_reflection_heuristic(
        self,
        reflection_input: ReflectionInput,
    ) -> ReflectionResult:
        """Tier 1/2 fallback: compute belief_delta from memory patterns.

        Algorithm:
        - Count positive vs negative memories (emotion_weight > 0.5 → positive)
        - ratio = (positive - negative) / total
        - belief_delta = REFLECTION_WEIGHT * ratio
        - clamp belief_delta to [-0.3, 0.3]
        """
```

**RF-02** — Data types:

```python
@dataclass
class ReflectionInput:
    agent_id: UUID
    recent_memories: list[MemoryRecord]
    current_belief: float
    step: int

@dataclass
class ReflectionResult:
    belief_delta: float        # [-0.3, 0.3]
    insight: str               # 1-line summary of what agent "learned"
    new_memories_generated: int # count of synthetic semantic memories created
```

**RF-03** — Constants (configurable via constructor):
- `MEMORY_THRESHOLD: int = 5` — minimum memories since last reflection
- `STEP_INTERVAL: int = 10` — minimum steps between reflections
- `REFLECTION_WEIGHT: float = 0.2` — scaling factor for belief_delta

**RF-04** — Reflection generates one synthetic "semantic" memory summarizing
the insight, stored back to MemoryLayer with `memory_type="semantic"` and
`emotion_weight = abs(belief_delta)`.

**RF-05** — Reflection is deterministic for Tier 1/2 (heuristic). Tier 3 (LLM)
uses `PromptBuilder.build_memory_reflection_prompt()` (already exists).

### Acceptance Criteria

| Test ID | Assertion |
|---------|-----------|
| RF-AC-01 | should_reflect returns True when memory_count >= threshold |
| RF-AC-02 | should_reflect returns True when step interval elapsed |
| RF-AC-03 | should_reflect returns False when neither condition met |
| RF-AC-04 | apply_reflection_heuristic returns belief_delta in [-0.3, 0.3] |
| RF-AC-05 | All-positive memories → positive belief_delta |
| RF-AC-06 | All-negative memories → negative belief_delta |
| RF-AC-07 | Empty memories → belief_delta == 0.0 |
| RF-AC-08 | build_reflection_input includes current_belief and memories |

---

## §P3.2 — HM: Homophily Edge Weighting

### Motivation

Current edge weights are community-based (same=0.7, different=0.3). Real social
networks exhibit personality-based homophily: similar people form stronger bonds.
(McPherson et al. 2001, "Birds of a Feather")

### Modification: `NetworkGenerator._compute_edge_weights()`

**HM-01** — When agent personality data is available on nodes, compute personality
similarity as part of edge weight:

```
personality_sim = 1.0 - manhattan_distance(p_u, p_v) / n_dims
edge_weight = trust_weight * community_trust
            + interaction_weight * interaction_freq
            + homophily_weight * personality_sim
```

Where `homophily_weight` is a new field on `NetworkConfig` (default: `0.0` for
backward compatibility, set to `0.2` to enable).

**HM-02** — `NetworkConfig` gains a new field:
```python
homophily_weight: float = 0.0  # when > 0, personality similarity influences edges
```

When `homophily_weight > 0`, the existing `trust_similarity_weight` and
`interaction_freq_weight` are rescaled so all three sum to 1.0.

**HM-03** — Personality data is optional on nodes. When `personality` attribute is
missing from a node, skip homophily for that edge (use community-only weights).

**HM-04** — The Manhattan distance normalization divides by number of personality
dimensions (5 in current schema: openness, skepticism, trend_following, brand_loyalty,
social_influence). This maps similarity to [0.0, 1.0].

### Acceptance Criteria

| Test ID | Assertion |
|---------|-----------|
| HM-AC-01 | homophily_weight=0 → behavior matches original |
| HM-AC-02 | Similar personalities → higher edge weight than dissimilar |
| HM-AC-03 | Missing personality → graceful fallback to community-only |
| HM-AC-04 | personality_sim in [0.0, 1.0] for all valid personality vectors |

---

## §P3.3 — MP: Memory Persistence (PostgreSQL)

### Motivation

Agent memories are in-memory dicts (`MemoryLayer._store`). If the server restarts
or a simulation is paused/resumed, all memory state is lost. For multi-day or
large simulations, persistence is required.

### DB Schema

**MP-01** — Add Alembic migration for `agent_memories` table:

```sql
CREATE TABLE agent_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id UUID NOT NULL REFERENCES simulations(id),
    agent_id UUID NOT NULL,
    memory_type VARCHAR(20) NOT NULL,  -- 'episodic', 'semantic', 'social'
    content TEXT NOT NULL,
    step INT NOT NULL,
    emotion_weight FLOAT NOT NULL,
    social_importance FLOAT NOT NULL,
    embedding VECTOR(768),  -- pgvector, nullable
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_agent_memories_sim_agent ON agent_memories(simulation_id, agent_id);
```

**MP-02** — `MemoryLayer` gains optional `persistence_mode: Literal["memory", "db"]`.
Default `"memory"` (current behavior). When `"db"`, `store()` and `retrieve()` hit
PostgreSQL via async SQLAlchemy session.

**MP-03** — Fire-and-forget write pattern: `store()` writes to in-memory first (for speed),
then enqueues an async DB write task. Same pattern used by simulation persistence.

**MP-04** — `retrieve()` with `persistence_mode="db"`: loads from DB on first access
(cold start), then uses in-memory cache. Subsequent calls use cache until eviction.

### Acceptance Criteria

| Test ID | Assertion |
|---------|-----------|
| MP-AC-01 | store() in memory mode works identically to current behavior |
| MP-AC-02 | store() in db mode creates database record |
| MP-AC-03 | retrieve() in db mode returns records from database |
| MP-AC-04 | Cold start: retrieve() loads from DB when _store is empty |

---

## Implementation Order

**Phase 1** (SQ-): fatigue → edge weight → expert score → prompt injection
**Phase 2**: EC (emotion contagion) → BC (bounded confidence) → CG (content gen)
**Phase 3**: RF (reflection) → HM (homophily) → MP (memory persistence)

All must pass:

```
uv run pytest tests/test_21_simulation_quality_p1.py -v
uv run pytest tests/test_21_simulation_quality_p2.py -v
uv run pytest tests/test_21_simulation_quality_p3.py -v
uv run pytest tests/test_21_memory_pgvector.py -v
```
