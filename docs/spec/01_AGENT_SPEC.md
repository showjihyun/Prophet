# 01 — Agent SPEC
Version: 0.3.0 | Status: REVIEW | Previous: 0.2.0

---

## 1. Overview

Each Agent is an autonomous entity in the simulation with a 6-layer architecture. Agents perceive their environment, retrieve memories, update emotions, evaluate content, decide actions, and influence neighbors.

**Execution Model: Community-first Orchestration**

Agent들은 전체를 하나의 flat loop로 처리하지 않는다.
각 커뮤니티별 `CommunityOrchestrator`가 소속 agent들을 독립적으로 tick하고,
커뮤니티 간 전파는 별도 Phase에서 bridge edge를 통해 처리한다.
이는 현실 SNS의 "커뮤니티 내부 순환 → 외부 전파" 패턴을 재현한다.

상세: `04_SIMULATION_SPEC.md` §4 CommunityOrchestrator 참조.

**Agent Types:**
| Type | Role | LLM Tier | Default Ratio |
|------|------|----------|--------------|
| `consumer` | General population agent | Tier 1/2 | ~60% |
| `early_adopter` | High openness, trend-following | Tier 1/2 | ~15% |
| `skeptic` | High skepticism, resist adoption | Tier 1/2 | ~10% |
| `influencer` | High influence score, large social network | Tier 2/3 | ~10% |
| `expert` | Domain knowledge, LLM-driven analysis | Tier 3 | ~5% |

---

## 2. Data Schema — Agent

```python
# backend/app/engine/agent/schema.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class AgentPersonality:
    """5-dimensional personality vector. All fields in [0.0, 1.0].

    Invariant: 0.0 <= field <= 1.0 for all fields.
    Violation: raise ValueError at construction time.
    """
    openness: float           # willingness to try new things
    skepticism: float         # resistance to claims
    trend_following: float    # peer influence susceptibility
    brand_loyalty: float      # attachment to known brands
    social_influence: float   # ability to influence others

    def __post_init__(self):
        for f in ['openness', 'skepticism', 'trend_following', 'brand_loyalty', 'social_influence']:
            v = getattr(self, f)
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"AgentPersonality.{f} must be in [0.0, 1.0], got {v}")

    def as_vector(self) -> list[float]:
        """Returns [openness, skepticism, trend_following, brand_loyalty, social_influence]."""
        return [self.openness, self.skepticism, self.trend_following,
                self.brand_loyalty, self.social_influence]


@dataclass
class AgentEmotion:
    """4-dimensional emotion state. All fields in [0.0, 1.0].

    Invariant: 0.0 <= field <= 1.0 for all fields.
    Violation: clamp to [0.0, 1.0] with WARNING log (not exception).
    Rationale: emotions are updated frequently; clamping is safer than crashing mid-step.
    """
    interest: float           # attention level to content
    trust: float              # confidence in source
    skepticism: float         # differs from personality skepticism (emotional state)
    excitement: float         # enthusiasm level

    def clamped(self) -> 'AgentEmotion':
        """Returns a new AgentEmotion with all fields clamped to [0.0, 1.0]."""
        return AgentEmotion(
            interest=max(0.0, min(1.0, self.interest)),
            trust=max(0.0, min(1.0, self.trust)),
            skepticism=max(0.0, min(1.0, self.skepticism)),
            excitement=max(0.0, min(1.0, self.excitement)),
        )


class AgentType(str, Enum):
    CONSUMER      = "consumer"
    EARLY_ADOPTER = "early_adopter"
    SKEPTIC       = "skeptic"
    INFLUENCER    = "influencer"
    EXPERT        = "expert"


@dataclass
class AgentState:
    """Full mutable state of an agent at a given simulation step.

    Invariants:
      - belief in [-1.0, 1.0]
      - exposure_count >= 0
      - step >= 0
      - llm_tier_used in {None, 1, 2, 3}
      - len(activity_vector) == 24
      - each activity_vector[i] in [0.0, 1.0]
    """
    agent_id: UUID
    simulation_id: UUID
    agent_type: AgentType
    step: int
    personality: AgentPersonality
    emotion: AgentEmotion
    belief: float             # -1.0 (hostile) to 1.0 (advocate)
    action: 'AgentAction'     # action taken this step (IGNORE at init)
    exposure_count: int       # times exposed to campaign this step (reset each step)
    adopted: bool             # has adopted/purchased (monotonic: once True, never reverts)
    community_id: UUID
    influence_score: float    # 0.0-1.0, computed from network degree centrality
    llm_tier_used: int | None # 1, 2, or 3 (None before first tick)
    activity_vector: list[float] = field(default_factory=lambda: [0.5] * 24)
```

---

## 3. Agent Action Enum

```python
class AgentAction(str, Enum):
    # --- Passive ---
    IGNORE    = "ignore"      # no engagement
    VIEW      = "view"        # saw content but no interaction
    SEARCH    = "search"      # actively searched for content/product

    # --- Positive Engagement ---
    LIKE      = "like"        # passive positive signal
    SAVE      = "save"        # bookmarked for later (purchase intent signal)
    COMMENT   = "comment"     # active engagement, generates propagation
    SHARE     = "share"       # endorsement + amplification to all neighbors
    REPOST    = "repost"      # amplification without personal endorsement

    # --- Relationship ---
    FOLLOW    = "follow"      # creates new network edge to content source
    UNFOLLOW  = "unfollow"    # removes network edge (negative signal)

    # --- Conversion ---
    ADOPT     = "adopt"       # purchase / full conversion

    # --- Negative ---
    MUTE      = "mute"        # blocks content source (strong negative signal)
```

### Action Hierarchy & Propagation Rules

Engagement level (positive path): `IGNORE < VIEW < SEARCH < LIKE < SAVE < COMMENT < SHARE < ADOPT`

#### Action Weight Table

Each action has a numeric weight used in social pressure computation:

| Action | Weight | Generates PropagationEvent? | Propagation Scope | Network Effect |
|--------|--------|---------------------------|-------------------|----------------|
| IGNORE | 0.0 | No | — | — |
| VIEW | 0.1 | No | — | — |
| SEARCH | 0.2 | No | — | Increases exposure_score for searched content |
| LIKE | 0.3 | No | — | Boosts content in RecSys ranking |
| SAVE | 0.4 | No | — | Purchase intent signal (analytics only) |
| COMMENT | 0.6 | **Yes** | Discussed neighbors (top-5 by edge weight) | — |
| SHARE | 0.8 | **Yes** | All neighbors (personal endorsement, trust_boost=0.1) | — |
| REPOST | 0.7 | **Yes** | All neighbors (neutral, trust_boost=0.0) | — |
| FOLLOW | 0.5 | No | — | **Creates edge** (W_init=0.3) |
| UNFOLLOW | -0.3 | No | — | **Removes edge** |
| ADOPT | 1.0 | **Yes** (passive) | All neighbors (P * 0.5, no amplification) | — |
| MUTE | -0.5 | No | — | **Removes edge + blocks future exposure** |

- `COMMENT` discussed neighbors: top-5 neighbors ranked by `W_ij` descending. If fewer than 5 neighbors, propagate to all.
- `SHARE` trust_boost: receiving agent's `trust_ij += 0.1` (clamped to 1.0) when processing this event.
- `ADOPT` passive propagation: probability reduced by 50% (`P * 0.5`), no message amplification.
- `FOLLOW` creates edge with initial weight `W_init = 0.3`.
- `MUTE` is irreversible within a single simulation run.

---

## 4. 6-Layer Architecture — Interface Contracts

### Layer 1: PerceptionLayer

```python
# backend/app/engine/agent/perception.py
# SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer

class PerceptionLayer:
    def __init__(self, feed_capacity: int = 20):
        """
        Args:
            feed_capacity: Maximum items in feed_items output. Default 20.
                           Must be > 0. Raises ValueError otherwise.
        """

    def observe(
        self,
        agent: AgentState,
        environment_events: list[EnvironmentEvent],
        neighbor_actions: list[NeighborAction],
    ) -> PerceptionResult:
        """
        Filters and weights incoming stimuli from the environment.

        Algorithm:
            1. Compute exposure_score for each event:
               exposure_score = recSys_rank(event, agent) * social_affinity_weight
            2. Sort events by exposure_score descending
            3. Truncate to feed_capacity items
            4. Extract social_signals from neighbor_actions (weighted by edge W_ij)
            5. Extract expert_signals from events where event_type == "expert_review"
            6. total_exposure_score = sum(item.exposure_score for item in feed_items)

        Args:
            agent: Current agent state. Must have valid agent_id and community_id.
            environment_events: Events this step. May be empty list [].
            neighbor_actions: Actions taken by neighbors. May be empty list [].

        Returns:
            PerceptionResult:
              - feed_items: sorted by exposure_score DESC, len <= feed_capacity
              - social_signals: one per neighbor who acted, weighted by W_ij
              - expert_signals: extracted from expert_review events only
              - total_exposure_score: sum of feed_items scores, in [0.0, +inf)

        Raises:
            Nothing. Empty inputs produce empty outputs (no items, score=0.0).

        Determinism: Pure function. Same inputs -> same output. No RNG.
        Side Effects: None.
        Performance: <= 5ms for 100 events + 50 neighbors.
        """


@dataclass
class EnvironmentEvent:
    """A single event in the simulation environment.

    Invariants:
      - event_type must be one of the Literal values
      - timestamp >= 0
      - message may be empty string but not None
    """
    event_type: Literal["campaign_ad", "influencer_post", "expert_review", "community_discussion"]
    content_id: UUID
    message: str
    source_agent_id: UUID | None   # None for system-generated events (campaign_ad)
    channel: str                    # e.g., "social_feed", "search", "direct"
    timestamp: int                  # step number, >= 0


@dataclass
class FeedItem:
    """A single item in the agent's perception feed."""
    content_id: UUID
    event_type: str
    message: str
    source_agent_id: UUID | None
    exposure_score: float          # >= 0.0, computed by RecSys ranking
    channel: str


@dataclass
class SocialSignal:
    """Weighted neighbor action signal."""
    neighbor_id: UUID
    action: AgentAction
    edge_weight: float             # W_ij in [0.0, 1.0]
    weighted_score: float          # action_weight * edge_weight


@dataclass
class ExpertSignal:
    """Expert opinion extracted from expert_review events."""
    expert_id: UUID
    opinion_score: float           # -1.0 (negative) to 1.0 (positive)
    credibility: float             # 0.0-1.0
    content_id: UUID


@dataclass
class NeighborAction:
    """Action taken by a neighbor agent this step."""
    agent_id: UUID
    action: AgentAction
    content_id: UUID
    step: int


@dataclass
class PerceptionResult:
    """Output of PerceptionLayer.observe().

    Invariants:
      - feed_items sorted by exposure_score DESC
      - len(feed_items) <= feed_capacity
      - total_exposure_score == sum(item.exposure_score for item in feed_items)
      - total_exposure_score >= 0.0
    """
    feed_items: list[FeedItem]
    social_signals: list[SocialSignal]
    expert_signals: list[ExpertSignal]
    total_exposure_score: float
```

---

### Layer 2: MemoryLayer

```python
# backend/app/engine/agent/memory.py
# SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer

class MemoryLayer:
    """Agent memory storage and retrieval using GraphRAG-style scoring.

    Scoring weights (configurable via MemoryConfig):
        alpha (recency):          0.3   # higher = favor recent memories
        beta  (relevance):        0.4   # pgvector cosine similarity
        gamma (emotion_weight):   0.2   # emotional significance
        delta (social_importance): 0.1  # social relationship weight

    Fallback weights (when pgvector unavailable):
        alpha: 0.6, gamma: 0.3, delta: 0.1
        (beta is dropped; relevance unavailable without embeddings)
    """

    def retrieve(
        self,
        agent_id: UUID,
        query_context: str,
        top_k: int = 10,
        current_step: int = 0,
    ) -> list[MemoryRecord]:
        """
        Retrieves top-K relevant memories for the given agent.

        Algorithm:
            For each memory m of agent_id:
              recency_score   = 1.0 / (1 + (current_step - m.timestamp))
              relevance_score = cosine_similarity(embed(query_context), m.embedding)
                                OR 0.0 if m.embedding is None
              score = alpha * recency_score
                    + beta  * relevance_score
                    + gamma * m.emotion_weight
                    + delta * m.social_importance
            Sort by score DESC, return top_k.

        Args:
            agent_id: Must exist in database. Raises AgentNotFoundError if not.
            query_context: Text to embed for relevance matching. May be empty string
                          (in which case relevance_score = 0.0 for all memories).
            top_k: Number of memories to return. Must be > 0. Default 10.
            current_step: Current simulation step for recency calculation.

        Returns:
            list[MemoryRecord] with len <= top_k, sorted by composite score DESC.
            Each record has relevance_score populated.
            Empty list if agent has no memories.

        Raises:
            AgentNotFoundError: agent_id does not exist in database.
            ValueError: top_k <= 0.

        Determinism: Deterministic for same DB state + inputs.
        Side Effects: Read-only DB query.
        Performance: <= 10ms for 1000 memories (with pgvector IVFFlat index).
        """

    def store(
        self,
        agent_id: UUID,
        memory_type: Literal["episodic", "semantic", "social"],
        content: str,
        emotion_weight: float,
        social_importance: float = 0.0,
        embedding: list[float] | None = None,
        step: int = 0,
    ) -> MemoryRecord:
        """
        Stores a new memory record for the agent.

        Args:
            agent_id: Must exist. Raises AgentNotFoundError otherwise.
            memory_type: One of "episodic" (experiences), "semantic" (knowledge),
                        "social" (relationship events).
            content: Memory text. Must not be empty. Raises ValueError if empty.
            emotion_weight: Emotional significance, in [0.0, 1.0]. Clamped if out of range.
            social_importance: Social significance, in [0.0, 1.0]. Default 0.0. Clamped.
            embedding: 768-dim float vector from LLMAdapter.embed().
                      None if embedding unavailable (skips vector index).
                      Raises ValueError if provided and len != 768.
            step: Simulation step when memory was created.

        Returns:
            MemoryRecord with generated memory_id (UUID4) and relevance_score=None.

        Raises:
            AgentNotFoundError: agent_id does not exist.
            ValueError: content is empty, or embedding length != 768.

        Side Effects: INSERT into agent_memories table.
        Performance: <= 5ms per store (single row insert).
        """


@dataclass
class MemoryRecord:
    """A single memory entry.

    Invariants:
      - emotion_weight in [0.0, 1.0]
      - social_importance in [0.0, 1.0]
      - embedding is None or len == 768
      - relevance_score is None (not yet queried) or float
    """
    memory_id: UUID
    agent_id: UUID
    memory_type: Literal["episodic", "semantic", "social"]
    content: str
    timestamp: int               # step number when stored
    emotion_weight: float        # [0.0, 1.0]
    social_importance: float     # [0.0, 1.0]
    embedding: list[float] | None  # 768-dim or None
    relevance_score: float | None  # populated on retrieval, None on store


@dataclass
class MemoryConfig:
    """Configurable weights for memory retrieval scoring."""
    alpha: float = 0.3    # recency weight
    beta: float = 0.4     # relevance weight (pgvector cosine)
    gamma: float = 0.2    # emotion weight
    delta: float = 0.1    # social importance weight

    def __post_init__(self):
        total = self.alpha + self.beta + self.gamma + self.delta
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"MemoryConfig weights must sum to 1.0, got {total}")
```

---

### Layer 3: EmotionLayer

```python
# backend/app/engine/agent/emotion.py
# SPEC: docs/spec/01_AGENT_SPEC.md#layer-3-emotionlayer

class EmotionLayer:
    """Updates agent emotional state based on environmental signals.

    Update formula (applied to each emotion dimension independently):
        E_i(t+1) = clamp(E_i(t) + social_signal + media_signal + expert_signal - decay, 0.0, 1.0)

    Signal application per dimension:
        interest:   += media_signal * 0.5 + social_signal * 0.3 + expert_signal * 0.2
        trust:      += expert_signal * 0.5 + social_signal * 0.3 + media_signal * 0.2
        skepticism: -= expert_signal * 0.3 (positive expert reduces skepticism)
                    += media_signal * 0.1  (ads can increase skepticism)
        excitement: += media_signal * 0.4 + social_signal * 0.4 + expert_signal * 0.2
    """

    def update(
        self,
        current_emotion: AgentEmotion,
        social_signal: float,
        media_signal: float,
        expert_signal: float,
        decay: float = 0.05,
    ) -> AgentEmotion:
        """
        Updates all emotion dimensions and returns new clamped AgentEmotion.

        Args:
            current_emotion: Current state. Must have fields in [0.0, 1.0].
                            If out of range, clamped before processing with WARNING.
            social_signal: Weighted average of neighbor emotions. Range [-1.0, 1.0].
                          Positive = neighbors are enthusiastic. Negative = neighbors hostile.
            media_signal: Campaign exposure strength. Range [0.0, 1.0].
                         0.0 = no exposure. 1.0 = maximum exposure.
            expert_signal: Expert opinion signal. Range [-1.0, 1.0].
                          Positive = expert endorsement. Negative = expert criticism.
            decay: Per-step natural decay. Default 0.05. Must be >= 0.0.
                  Raises ValueError if negative.

        Returns:
            New AgentEmotion with all fields clamped to [0.0, 1.0].
            Never returns values outside [0.0, 1.0].

        Raises:
            ValueError: decay < 0.0

        Determinism: Pure function. Same inputs -> same output.
        Side Effects: None.
        Performance: <= 0.1ms (arithmetic only).
        """

    def emotion_factor(self, emotion: AgentEmotion) -> float:
        """
        Computes scalar factor for diffusion probability.

        Formula:
            factor = emotion.excitement - emotion.skepticism
            return clamp(factor, -1.0, 1.0)

        Args:
            emotion: AgentEmotion with fields in [0.0, 1.0].

        Returns:
            float in [-1.0, 1.0].
            Positive = agent is emotionally favorable for propagation.
            Negative = agent is emotionally resistant.

        Determinism: Pure function.
        Side Effects: None.
        Performance: <= 0.01ms.
        """
```

---

### Layer 4: CognitionLayer

```python
# backend/app/engine/agent/cognition.py
# SPEC: docs/spec/01_AGENT_SPEC.md#layer-4-cognitionlayer

class CognitionLayer:
    """Evaluates content and produces action recommendations.

    Three tiers with IDENTICAL output shape (CognitionResult):

    Tier 1 — Rule Engine (~80% of agents):
        evaluation = (agent.emotion.interest * 0.3
                     + agent.emotion.trust * 0.25
                     - agent.emotion.skepticism * 0.25
                     + community_bias * 0.1
                     + memory_weight * 0.1)
        Where:
          community_bias = mean(belief) of agent's community neighbors (default 0.0 if no data)
          memory_weight  = mean(m.emotion_weight for m in memories) (default 0.0 if empty)
        evaluation is clamped to [-2.0, 2.0]
        confidence = abs(evaluation) / 2.0  (normalized to [0.0, 1.0])
        recommended_action = map_score_to_action(evaluation) (see mapping below)

    Tier 2 — Heuristic (~10% of agents):
        base = Tier 1 evaluation
        personality_adj = (agent.personality.openness * 0.3
                         - agent.personality.skepticism * 0.3
                         + agent.personality.trend_following * 0.2
                         + agent.personality.brand_loyalty * 0.2)
        evaluation = clamp(base + personality_adj * 0.5, -2.0, 2.0)

    Tier 3 — LLM (~10% of agents):
        Builds prompt via PromptBuilder (see 05_LLM_SPEC)
        Calls LLMAdapter.complete(prompt, response_format="json")
        Parses JSON into CognitionResult
        Timeout: falls back to Tier 2 (NOT Tier 1, to preserve personality effects)
    """

    def evaluate(
        self,
        agent: AgentState,
        perception: PerceptionResult,
        memories: list[MemoryRecord],
        cognition_tier: Literal[1, 2, 3],
        community_bias: float = 0.0,
    ) -> CognitionResult:
        """
        Args:
            agent: Full agent state for this step.
            perception: Output of PerceptionLayer.observe().
            memories: Output of MemoryLayer.retrieve(). May be empty [].
            cognition_tier: 1 (rule), 2 (heuristic), or 3 (LLM).
                           Raises ValueError for other values.
            community_bias: Mean belief of community neighbors. Default 0.0.
                           Range [-1.0, 1.0]. Clamped if out of range.

        Returns:
            CognitionResult:
              - evaluation_score in [-2.0, 2.0] (clamped)
              - reasoning: None for Tier 1/2, str for Tier 3
              - recommended_action: AgentAction based on score mapping
              - confidence in [0.0, 1.0]

        Raises:
            ValueError: cognition_tier not in {1, 2, 3}
            LLMTimeoutError: Tier 3 LLM call exceeds timeout (auto-falls back to Tier 2)
            LLMParseError: Tier 3 LLM returns invalid JSON (auto-falls back to Tier 2)

        Determinism:
            Tier 1/2: Pure function (deterministic).
            Tier 3: Non-deterministic (LLM temperature > 0).
        Side Effects:
            Tier 1/2: None.
            Tier 3: LLM API call (logged to llm_calls table).
        Performance:
            Tier 1: <= 1ms
            Tier 2: <= 2ms
            Tier 3: <= 10s (timeout threshold, configurable in LLMOptions)
        """


# --- Score-to-Action Mapping ---
# evaluation_score range -> recommended_action
#   [-2.0, -1.0)  -> MUTE     (strongly negative)
#   [-1.0, -0.5)  -> IGNORE   (negative)
#   [-0.5,  0.0)  -> VIEW     (mildly negative / neutral)
#   [ 0.0,  0.3)  -> LIKE     (mildly positive)
#   [ 0.3,  0.5)  -> SAVE     (positive)
#   [ 0.5,  0.8)  -> COMMENT  (engaged)
#   [ 0.8,  1.2)  -> SHARE    (enthusiastic)
#   [ 1.2,  2.0]  -> ADOPT    (strongly positive)
# Note: SEARCH, REPOST, FOLLOW, UNFOLLOW selected by personality modifiers (Tier 2/3 only).


@dataclass
class CognitionResult:
    """Output of CognitionLayer.evaluate().

    Invariants:
      - evaluation_score in [-2.0, 2.0]
      - confidence in [0.0, 1.0]
      - reasoning is None for Tier 1/2, non-empty str for Tier 3
    """
    evaluation_score: float      # [-2.0, 2.0]
    reasoning: str | None        # LLM-generated reasoning (Tier 3 only)
    recommended_action: AgentAction
    confidence: float            # [0.0, 1.0]
    tier_used: int               # actual tier (may differ if fallback occurred)
```

---

### Layer 5: DecisionLayer

```python
# backend/app/engine/agent/decision.py
# SPEC: docs/spec/01_AGENT_SPEC.md#layer-5-decisionlayer

class DecisionLayer:
    """Converts cognition results into probabilistic action selection.

    Algorithm:
        1. Compute base score per action from cognition.evaluation_score
        2. Add social_pressure to positive actions (LIKE through ADOPT)
        3. Apply personality modifiers:
           - openness > 0.7:          SEARCH probability * 1.5
           - trend_following > 0.7:   SHARE/REPOST probability * 1.5
           - skepticism > 0.7:        MUTE/IGNORE probability * 1.5
           - brand_loyalty > 0.7:     ADOPT probability * 1.3 (if already exposed 3+ times)
        4. Softmax over all action scores -> probability distribution
        5. Sample action from distribution using agent-specific RNG
    """

    def choose_action(
        self,
        cognition: CognitionResult,
        social_pressure: float,
        personality: AgentPersonality,
        agent_seed: int,
    ) -> AgentAction:
        """
        Args:
            cognition: Output of CognitionLayer.evaluate().
            social_pressure: Scalar from compute_social_pressure(). Range [-5.0, 5.0].
                            Clamped if out of range.
            personality: Agent's personality vector.
            agent_seed: Seed for this agent's RNG (sim_seed + agent_id_hash + step).
                       Ensures reproducibility per agent per step.

        Returns:
            AgentAction sampled from softmax probability distribution.

        Raises:
            Nothing. Always returns a valid AgentAction.

        Determinism: Deterministic for same seed + inputs.
        Side Effects: None.
        Performance: <= 0.5ms.
        """

    def compute_social_pressure(
        self,
        agent_id: UUID,
        neighbors: list[NeighborAction],
        trust_matrix: dict[tuple[UUID, UUID], float],
    ) -> float:
        """
        Computes social pressure from neighbor actions.

        Formula:
            social_pressure = sum(
                trust_matrix.get((agent_id, n.agent_id), 0.0)
                * ACTION_WEIGHT[n.action]
                for n in neighbors
            )

        Where ACTION_WEIGHT is defined in the Action Weight Table (Section 3).

        Args:
            agent_id: The agent receiving social pressure.
            neighbors: List of neighbor actions this step. May be empty [].
            trust_matrix: Edge weights keyed by (source, target) UUID pair.
                         Missing keys default to 0.0 (no relationship).

        Returns:
            float. Can be negative (if neighbors took negative actions like MUTE/UNFOLLOW).
            Typical range [-5.0, 5.0] but not clamped here.

        Determinism: Pure function.
        Side Effects: None.
        Performance: <= 0.5ms for 50 neighbors.
        """
```

---

### Layer 6: InfluenceLayer (Social Propagation)

```python
# backend/app/engine/agent/influence.py
# SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer

class InfluenceLayer:
    """Models how agent actions propagate to network neighbors.

    Propagation occurs ONLY for actions with Generates PropagationEvent = Yes:
      COMMENT, SHARE, REPOST, ADOPT (see Action Weight Table, Section 3).

    For non-propagating actions, propagate() returns empty list.
    """

    def propagate(
        self,
        source_agent: AgentState,
        action: AgentAction,
        target_agent_ids: list[UUID],
        graph_edges: dict[tuple[UUID, UUID], float],
        message_strength: MessageStrength,
        step_seed: int,
    ) -> list[PropagationEvent]:
        """
        Computes propagation probability for each target and generates events.

        Algorithm:
            If action not in {COMMENT, SHARE, REPOST, ADOPT}: return []

            scope = select_targets(action, target_agent_ids, graph_edges)
            events = []
            for target_id in scope:
                trust_ij = graph_edges.get((source_agent.agent_id, target_id), 0.0)
                emotion_f = EmotionLayer.emotion_factor(source_agent.emotion)
                P = source_agent.influence_score * trust_ij * max(emotion_f, 0.0) * message_strength.score

                if action == ADOPT:
                    P *= 0.5  # passive visibility reduction

                P = clamp(P, 0.0, 1.0)

                rng = Random(step_seed ^ hash(target_id))
                if rng.random() < P:
                    events.append(PropagationEvent(...))
            return events

        Target Selection (select_targets):
            COMMENT -> top-5 neighbors by edge weight (discussed subset)
            SHARE   -> all target_agent_ids
            REPOST  -> all target_agent_ids
            ADOPT   -> all target_agent_ids

        Args:
            source_agent: The agent propagating content.
            action: The action taken. If not propagating, returns [].
            target_agent_ids: Potential targets (neighbors). May be empty.
            graph_edges: Edge weights keyed by (source, target).
            message_strength: Content properties (novelty, controversy, utility).
            step_seed: Seed for reproducible random threshold.

        Returns:
            list[PropagationEvent]. Empty if action doesn't propagate or no targets.
            Each event contains a ContextualPacket.

        Raises:
            Nothing. Non-propagating actions and empty targets return [].

        Determinism: Deterministic for same step_seed + inputs.
        Side Effects: None (events are returned, not applied).
        Performance: <= 2ms for 100 targets.
        """


@dataclass
class MessageStrength:
    """Content properties affecting propagation probability.

    Invariants: all fields in [0.0, 1.0].
    """
    novelty: float       # how new/surprising the content is
    controversy: float   # how polarizing the content is
    utility: float       # practical value of the content

    @property
    def score(self) -> float:
        """Aggregate score. Returns mean of all dimensions. Range [0.0, 1.0]."""
        return (self.novelty + self.controversy + self.utility) / 3.0

    def __post_init__(self):
        for f in ['novelty', 'controversy', 'utility']:
            v = getattr(self, f)
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"MessageStrength.{f} must be in [0.0, 1.0], got {v}")


@dataclass
class PropagationEvent:
    """A single propagation from source to target.

    Created by InfluenceLayer.propagate().
    Consumed by DiffusionEngine in the next step.
    """
    source_agent_id: UUID
    target_agent_id: UUID
    content_id: UUID
    probability: float              # the P value that passed threshold, in [0.0, 1.0]
    packet: 'ContextualPacket'
    step: int


@dataclass
class ContextualPacket:
    """Structured propagation payload — carries source agent's reasoning context.

    Enables the "butterfly effect": content transforms as it spreads.
    A skeptic sharing sarcastically creates a different cascade than an
    enthusiast sharing with excitement.
    """
    source_agent_id: UUID
    source_emotion: AgentEmotion
    source_summary: str           # 1-2 sentence summary of reasoning
    message_strength: MessageStrength
    sentiment_polarity: float     # [-1.0, 1.0] derived from source_emotion:
                                  #   = (excitement + trust - skepticism) / 2.0, clamped to [-1, 1]
    action_taken: AgentAction
    step: int
```

---

## 5. Agent Tick — Full Execution Flow

```python
# backend/app/engine/agent/engine.py
# SPEC: docs/spec/01_AGENT_SPEC.md#agent-tick

class AgentEngine:
    async def tick(
        self,
        agent: AgentState,
        environment_events: list[EnvironmentEvent],
        neighbor_actions: list[NeighborAction],
        graph_context: GraphContext,
        cognition_tier: int,
    ) -> AgentTickResult:
        """
        Full agent execution for one simulation step.

        Execution Order (strict sequential, no reordering):
            1. ACTIVITY CHECK
               hour = step_to_hour(agent.step, temporal_config)
               if random(agent_seed) > agent.activity_vector[hour]:
                   return AgentTickResult(unchanged state, action=IGNORE, no propagation)

            2. PERCEPTION
               perception = PerceptionLayer.observe(agent, events, neighbors)

            3. MEMORY RETRIEVAL
               context = summarize(perception)  # first 200 chars of top feed_item
               memories = MemoryLayer.retrieve(agent.agent_id, context, top_k=10, current_step=agent.step)

            4. EMOTION UPDATE
               social_signal  = mean(s.weighted_score for s in perception.social_signals) or 0.0
               media_signal   = min(perception.total_exposure_score / 10.0, 1.0)
               expert_signal  = mean(e.opinion_score * e.credibility for e in perception.expert_signals) or 0.0
               emotion = EmotionLayer.update(agent.emotion, social_signal, media_signal, expert_signal)

            5. COGNITION
               community_bias = graph_context.get_community_mean_belief(agent.community_id)
               try:
                   cognition = CognitionLayer.evaluate(agent, perception, memories, cognition_tier, community_bias)
               except LLMTimeoutError:
                   cognition = CognitionLayer.evaluate(agent, perception, memories, tier=2, community_bias)

            6. DECISION
               social_pressure = DecisionLayer.compute_social_pressure(agent.agent_id, neighbors, graph_context.trust_matrix)
               action = DecisionLayer.choose_action(cognition, social_pressure, agent.personality, agent_seed)

            7. INFLUENCE PROPAGATION
               if action in {COMMENT, SHARE, REPOST, ADOPT}:
                   message_strength = compute_message_strength(perception)
                   events = InfluenceLayer.propagate(agent, action, neighbor_ids, edges, message_strength, step_seed)
               else:
                   events = []

            8. MEMORY STORAGE
               memory = MemoryLayer.store(agent.agent_id, "episodic", step_summary, emotion_weight=mean(emotion))

            9. STATE UPDATE
               updated_state = agent.copy(
                   emotion=emotion,
                   action=action,
                   belief=update_belief(agent.belief, cognition.evaluation_score),
                   adopted=agent.adopted or (action == ADOPT),
                   llm_tier_used=cognition.tier_used,
               )

        Belief Update Formula:
            new_belief = clamp(
                agent.belief + cognition.evaluation_score * 0.1,
                -1.0, 1.0
            )

        Args:
            agent: Current AgentState (immutable input; returns updated copy).
            environment_events: Events this step.
            neighbor_actions: Neighbor actions this step.
            graph_context: Network topology (edges, trust matrix, community beliefs).
            cognition_tier: Assigned tier from TierSelector.

        Returns:
            AgentTickResult:
              - updated_state: new AgentState with updated emotion, belief, action
              - propagation_events: list of events to process next step
              - memory_stored: the episodic memory created this step
              - llm_call_log: LLMCallLog if Tier 3 was invoked, else None

        Raises:
            AgentNotFoundError: if agent.agent_id not in database (during memory ops).
            Note: LLMTimeoutError is caught internally and falls back to Tier 2.

        Determinism:
            Tier 1/2: Fully deterministic with same seed.
            Tier 3: Non-deterministic (LLM response varies).
        Side Effects:
            - MemoryLayer.store() inserts into database.
            - LLM API call (Tier 3 only).
        Performance:
            Tier 1: <= 50ms per agent (including DB I/O).
            Tier 2: <= 50ms per agent.
            Tier 3: <= 10s per agent (dominated by LLM latency).
            Target: 1000 Tier 1 agents in <= 1s (parallel via asyncio).
        """


@dataclass
class GraphContext:
    """Network topology context provided to AgentEngine.tick().

    Provided by SimulationOrchestrator from NetworkGenerator state.
    """
    edges: dict[tuple[UUID, UUID], float]           # all edge weights
    trust_matrix: dict[tuple[UUID, UUID], float]     # = edges (alias for clarity)
    neighbor_ids: dict[UUID, list[UUID]]             # agent_id -> list of neighbor IDs
    community_beliefs: dict[UUID, float]             # community_id -> mean belief

    def get_community_mean_belief(self, community_id: UUID) -> float:
        """Returns mean belief for community. Default 0.0 if unknown."""
        return self.community_beliefs.get(community_id, 0.0)


@dataclass
class AgentTickResult:
    """Output of AgentEngine.tick().

    Invariants:
      - updated_state.step == input agent.step (step is incremented by Orchestrator, not Agent)
      - updated_state.adopted == True implies input agent.adopted == True OR action == ADOPT
      - propagation_events may be empty
      - llm_call_log is None unless Tier 3 was actually invoked
    """
    updated_state: AgentState
    propagation_events: list[PropagationEvent]
    memory_stored: MemoryRecord
    llm_call_log: 'LLMCallLog | None'
```

---

## 6. Agent Initialization Strategy

```python
# backend/app/engine/agent/initializer.py
# SPEC: docs/spec/01_AGENT_SPEC.md#agent-initialization

class AgentInitializer:
    def initialize_agents(
        self,
        communities: list[CommunityConfig],
        seed: int | None = None,
    ) -> list[AgentState]:
        """
        Creates agents for all communities with sampled personality traits.

        Algorithm:
            rng = numpy.random.RandomState(seed)
            agents = []
            for community in communities:
                for i in range(community.agent_count):
                    agent_type = sample_agent_type(community, rng)
                    personality = sample_personality(agent_type, rng)
                    activity = sample_activity_vector(rng)
                    agents.append(AgentState(
                        agent_id=uuid4(),
                        agent_type=agent_type,
                        personality=personality,
                        emotion=DEFAULT_EMOTION,
                        belief=0.0,
                        action=AgentAction.IGNORE,
                        exposure_count=0,
                        adopted=False,
                        influence_score=0.0,  # set after network generation
                        activity_vector=activity,
                    ))
            return agents

        Personality Distributions (truncated normal, clamped [0, 1]):

            | Agent Type     | openness     | skepticism   | trend_following | brand_loyalty | social_influence |
            |----------------|-------------|-------------|-----------------|---------------|-----------------|
            | consumer       | N(0.5, 0.15) | N(0.5, 0.15) | N(0.5, 0.15)   | N(0.5, 0.2)   | N(0.3, 0.15)    |
            | early_adopter  | N(0.8, 0.1)  | N(0.2, 0.1)  | N(0.8, 0.1)    | N(0.5, 0.2)   | N(0.5, 0.15)    |
            | skeptic        | N(0.3, 0.1)  | N(0.8, 0.1)  | N(0.3, 0.1)    | N(0.5, 0.2)   | N(0.4, 0.15)    |
            | influencer     | N(0.7, 0.1)  | N(0.4, 0.15) | N(0.7, 0.1)    | N(0.5, 0.2)   | N(0.9, 0.1)     |
            | expert         | N(0.6, 0.1)  | N(0.6, 0.1)  | N(0.4, 0.15)   | N(0.5, 0.2)   | N(0.7, 0.1)     |

            Sampling: value = rng.normal(mu, sigma); clamp(value, 0.0, 1.0)

        Default Emotion:
            interest=0.5, trust=0.5, skepticism=0.5, excitement=0.3

        Activity Vector:
            24-dim vector sampled per agent. Each hour sampled from rng.beta(2, 5)
            then multiplied by agent_type modifier:
              consumer: * 1.0 (baseline)
              early_adopter: * 1.3 (more active)
              influencer: * 1.5 (most active)
              skeptic: * 0.8 (less active)
              expert: * 0.7 (least active, focused engagement)
            Clamped to [0.0, 1.0].

        Args:
            communities: List of CommunityConfig defining agent count and type distribution.
            seed: RNG seed for reproducibility. None = random.

        Returns:
            list[AgentState] with len == sum(c.agent_count for c in communities).
            influence_score = 0.0 (must be set after network generation).

        Raises:
            ValueError: community.agent_count <= 0 or community list is empty.

        Determinism: Fully deterministic with same seed.
        Side Effects: None (in-memory only).
        Performance: <= 100ms for 1000 agents.
        """
```

---

## 7. LLM Tier Selection Algorithm

```python
# backend/app/engine/agent/tier_selector.py
# SPEC: docs/spec/01_AGENT_SPEC.md#tier-selection

class TierSelector:
    def assign_tiers(
        self,
        agents: list[AgentState],
        config: TierConfig,
        step_seed: int,
    ) -> dict[UUID, int]:
        """
        Assigns inference tier (1, 2, or 3) to each agent for this step.

        Algorithm (pseudocode):
            rng = Random(step_seed)
            max_tier3 = ceil(len(agents) * config.max_tier3_ratio)
            max_tier2 = ceil(len(agents) * config.max_tier2_ratio)

            # --- Phase 1: Tier 3 selection (priority order) ---
            tier3_candidates = []

            # Priority 1: Expert agents — always eligible
            tier3_candidates += [a for a in agents if a.agent_type == EXPERT]

            # Priority 2: High-influence agents
            tier3_candidates += [a for a in agents
                                 if a.agent_type == INFLUENCER
                                 and a.influence_score > 0.7
                                 and a not in tier3_candidates]

            # Priority 3: Critical decision agents (conflicting signals)
            tier3_candidates += [a for a in agents
                                 if abs(a.belief) < 0.2          # near-neutral
                                 and a.exposure_count > 3         # high exposure
                                 and a.adopted == False           # not yet adopted
                                 and a not in tier3_candidates]

            # Cap and sample if over limit
            if len(tier3_candidates) > max_tier3:
                tier3 = tier3_candidates[:max_tier3]  # priority order preserved
            else:
                tier3 = tier3_candidates

            # --- Phase 2: Tier 2 selection ---
            remaining = [a for a in agents if a.agent_id not in {t.agent_id for t in tier3}]
            tier2_candidates = [a for a in remaining
                                if a.influence_score > 0.5
                                or (a.agent_type == SKEPTIC and a.emotion.skepticism > 0.7)]

            if len(tier2_candidates) > max_tier2:
                tier2 = rng.sample(tier2_candidates, max_tier2)
            else:
                tier2 = tier2_candidates

            # --- Phase 3: Tier 1 = everyone else ---
            tier1_ids = {a.agent_id for a in agents} - {t.agent_id for t in tier3} - {t.agent_id for t in tier2}

            return {a.agent_id: 3 for a in tier3}
                 | {a.agent_id: 2 for a in tier2}
                 | {id: 1 for id in tier1_ids}

        Args:
            agents: All agents in simulation. Must not be empty.
            config: Tier configuration with ratio caps.
            step_seed: Seed for this step (sim_seed + step_number).

        Returns:
            dict mapping every agent_id to tier (1, 2, or 3).
            Guarantees: every agent_id in input appears exactly once in output.

        Raises:
            ValueError: agents list is empty.

        Determinism: Deterministic for same step_seed + agent states.
        Side Effects: None.
        Performance: <= 5ms for 1000 agents.
        """


@dataclass
class TierConfig:
    """Configuration for tier selection ratios.

    Invariant: max_tier3_ratio + max_tier2_ratio <= 0.5
               (at least 50% of agents must be Tier 1)
    """
    max_tier3_ratio: float = 0.10    # <= 10% agents use LLM
    max_tier2_ratio: float = 0.10    # <= 10% agents use heuristic
    slm_llm_ratio_override: float | None = None  # user override from SimulationConfig

    def __post_init__(self):
        if self.max_tier3_ratio + self.max_tier2_ratio > 0.5:
            raise ValueError("Tier 2+3 ratio must not exceed 50%")
```

---

## 8. Personality Drift

```python
# backend/app/engine/agent/drift.py
# SPEC: docs/spec/01_AGENT_SPEC.md#personality-drift

class PersonalityDrift:
    """Optional personality evolution based on cumulative experience.

    Enabled via SimulationConfig.enable_personality_drift: bool (default False).

    Formula:
        P_dim(t+1) = clamp(P_dim(t) + learning_rate * delta_dim, 0.0, 1.0)

    Drift limits:
        Max drift per dimension per simulation: 0.3
        (tracked via cumulative_drift dict per agent per dimension)

    If cumulative_drift[dim] >= 0.3, no further drift in that dimension.
    """

    DRIFT_TABLE: dict[AgentAction, dict[str, float]] = {
        AgentAction.ADOPT:   {"openness": 0.01, "brand_loyalty": 0.02},
        AgentAction.SHARE:   {"social_influence": 0.01, "trend_following": 0.01},
        AgentAction.REPOST:  {"trend_following": 0.005},
        AgentAction.COMMENT: {"openness": 0.005},
        AgentAction.FOLLOW:  {"trend_following": 0.005},
        AgentAction.MUTE:    {"skepticism": 0.01},
        # All other actions: no drift
    }

    def apply_drift(
        self,
        personality: AgentPersonality,
        action: AgentAction,
        cumulative_drift: dict[str, float],
        learning_rate: float = 0.01,
    ) -> tuple[AgentPersonality, dict[str, float]]:
        """
        Args:
            personality: Current personality (frozen dataclass — returns new instance).
            action: Action taken this step.
            cumulative_drift: Running total of drift per dimension.
                             Keys: personality field names. Values: total drift so far.
            learning_rate: Multiplier for drift deltas. Default 0.01.

        Returns:
            (new_personality, updated_cumulative_drift)
            If action has no drift entry, returns (personality, cumulative_drift) unchanged.

        Raises:
            Nothing.

        Determinism: Pure function.
        Side Effects: None.
        """
```

---

## 8.5. Additional Agent Modules (Post-initial SPEC)

### tick.py — Agent Tick Logic
```python
# backend/app/engine/agent/tick.py
class AgentTick:
    """Main per-step agent processing.
    Orchestrates the 6-layer pipeline: Perception → Memory → Emotion → Cognition → Decision → Influence.
    agent_core.py is a re-export shim that exports AgentTick.
    """
    async def tick(self, agent: AgentState, context: TickContext) -> AgentTickResult: ...
```

### expert_engine.py — Expert Agent Engine
```python
# backend/app/engine/agent/expert_engine.py
class ExpertEngine:
    """Expert-specific agent engine using Tier 3 LLM cognition.
    Provides deeper analysis for expert agent types.
    @spec docs/spec/platform/13_SCALE_VALIDATION_SPEC.md
    """
    async def evaluate(self, agent: AgentState, context: TickContext) -> CognitionResult: ...
```

### interview.py — Agent Interviewer
```python
# backend/app/engine/agent/interview.py
class AgentInterviewer:
    """Enables mid-simulation agent interviews via Tier 3 LLM.
    Researcher can ask questions to agents and receive in-character responses.
    @spec docs/spec/platform/13_SCALE_VALIDATION_SPEC.md
    """
    async def interview(self, agent: AgentState, question: str) -> InterviewResponse: ...
```

### group_chat.py — Group Chat Manager
```python
# backend/app/engine/agent/group_chat.py
class GroupChatManager:
    """Multi-agent group discussions.
    Creates chat sessions between selected agents for researcher observation.
    @spec docs/spec/platform/13_SCALE_VALIDATION_SPEC.md
    """
    async def create_session(self, agents: list[AgentState], topic: str) -> GroupChatSession: ...
    async def add_message(self, session_id: UUID, content: str) -> list[ChatMessage]: ...
```

### File Name Aliases

구현에서 6-layer 파일은 두 가지 이름이 공존한다:
| Canonical (SPEC) | Alias (legacy) |
|-------------------|---------------|
| `cognition_engine.py` | `cognition.py` |
| `decision_model.py` | `decision.py` |
| `emotion_model.py` | `emotion.py` |
| `memory_layer.py` | `memory.py` |
| `influence_model.py` | `influence.py` |

Canonical 이름이 정식이며, alias는 import 편의를 위해 유지.

### TODO
- `AgentState.activity_vector`: `len == 24` invariant를 `__post_init__`에서 강제하지 않음. 향후 추가 필요.

---

## 9. Error Specification

| Situation | Exception Type | Recovery | Logging |
|-----------|---------------|----------|---------|
| LLM Tier 3 timeout (>10s default) | `LLMTimeoutError` | Fallback to Tier 2 evaluation | WARN + log to `llm_calls` table |
| LLM Tier 3 invalid JSON response | `LLMParseError` | Fallback to Tier 2 evaluation | WARN + log raw response |
| pgvector unavailable for memory retrieval | — (graceful) | Use fallback weights (recency-only) | INFO at first occurrence per sim |
| Agent not found in DB (memory ops) | `AgentNotFoundError` | Skip memory op, continue tick | ERROR |
| Personality field out of [0, 1] at construction | `ValueError` | Reject construction | ERROR |
| Emotion field out of [0, 1] during update | — (clamp) | Clamp to [0.0, 1.0] | WARN |
| Empty agent list for tier selection | `ValueError` | Reject call | ERROR |
| Network edge missing in trust_matrix | — (default 0.0) | Treat as no relationship | DEBUG (not logged by default) |
| Activity check fails (inactive hour) | — (skip) | Return IGNORE, no propagation | DEBUG |

---

## 10. Acceptance Criteria (Harness Tests)

| ID | Test | Given | When | Then |
|----|------|-------|------|------|
| AGT-01 | Tier 1 rule engine output range | agent: neutral (all emotions 0.5), no memories, community_bias=0.0 | CognitionLayer.evaluate(tier=1) | evaluation_score in [-2.0, 2.0], confidence in [0.0, 1.0] |
| AGT-02 | High skepticism ignores ad | agent: personality.skepticism=0.9, emotion.skepticism=0.8, campaign_ad event (controversy=0.3) | tick() x1000 (seeds 1-1000), Tier 1 only, no neighbors | action==IGNORE ratio > 0.6 AND action==ADOPT ratio == 0.0 |
| AGT-03 | Expert signal boosts trust | emotion: trust=0.3, expert_signal=0.8 | EmotionLayer.update(social=0, media=0, expert=0.8) | result.trust > 0.3 (increased) |
| AGT-04 | High-influence agent propagates | agent: influence_score=0.9, trust_ij=0.8 for all 10 neighbors, emotion_factor=0.7, msg_strength=0.8 | InfluenceLayer.propagate() x100 (seeds 1-100) | mean(len(events)) > 3 (at least some propagation) |
| AGT-05 | LLM timeout falls back to Tier 2 | Mock LLM that always times out after 100ms | tick(tier=3) | result.llm_tier_used == 2 (not 3), valid CognitionResult returned |
| AGT-06 | Memory retrieval respects top-K | agent with 50 stored memories, top_k=10 | MemoryLayer.retrieve(top_k=10) | len(result) == 10, sorted by score DESC |
| AGT-07 | Personality drift accumulates | personality.openness=0.5, enable_drift=True | apply_drift(action=ADOPT) x10 | openness >= 0.55 (increased by ~0.05 with learning_rate=0.01, delta=0.01, 10 times) |
| AGT-08 | Tier 1 tick performance | 1000 agents, Tier 1, mock DB (SQLite), no LLM | parallel tick() via asyncio | total time <= 1000ms (1s) |
| AGT-09 | Activity vector skips inactive hour | agent.activity_vector[14]=0.0 (2PM inactive), step maps to hour 14 | tick() | action==IGNORE, propagation_events==[], no memory stored |
| AGT-10 | Tier selector respects caps | 1000 agents (50 experts, 100 influencers), max_tier3_ratio=0.10 | assign_tiers() | len(tier3) <= 100, all experts in tier3, remaining influencers in tier2 or tier3 |
| AGT-11 | Seed reproducibility | Same agent state + seed=42 | tick() x2 | Both runs produce identical AgentTickResult |
| AGT-12 | Drift capped at 0.3 per dimension | openness=0.5, drift enabled | apply_drift(ADOPT) x100 | openness <= 0.8 (0.5 + 0.3 cap) |
| AGT-13 | Social pressure computation | 3 neighbors: SHARE(W=0.8), LIKE(W=0.5), MUTE(W=0.3) | compute_social_pressure() | result == 0.8*0.8 + 0.5*0.3 + 0.3*(-0.5) == 0.64 + 0.15 - 0.15 == 0.64 |
| AGT-14 | ContextualPacket sentiment polarity | emotion: excitement=0.8, trust=0.7, skepticism=0.2 | compute sentiment_polarity | (0.8+0.7-0.2)/2.0 = 0.65, clamped to [-1,1] -> 0.65 |
