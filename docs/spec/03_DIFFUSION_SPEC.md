# 03 — Social Diffusion Engine SPEC
Version: 0.1.1 | Status: DRAFT

---

## 1. Overview

The Social Diffusion Engine models how content (campaigns, opinions, information) spreads through the social network. It extends classical cascade models (Independent Cascade, Linear Threshold) with LLM cognition and emotion dynamics.

**Target phenomena to reproduce:**

| Phenomenon | Trigger | Detection |
|-----------|---------|-----------|
| Viral Cascade | Influencer share → rapid adoption | `cascade_size > viral_threshold` |
| Slow Adoption | Low novelty, conservative community | `R(t) < slow_threshold` for N steps |
| Polarization | Expert criticism in skeptic community | `sentiment_variance > polar_threshold` |
| Collapse | Negative expert review + influencer backlash | `adoption_rate drops > 20% in 3 steps` |
| Echo Chamber | Community isolation | `internal_links >> external_links` |

---

## 2. Diffusion Pipeline

```
Content Event
      │
      ▼  ExposureModel
Exposure Scores per Agent
      │
      ▼  CognitionModel  (per-agent, uses AgentEngine Layers 1–4)
Evaluation Scores
      │
      ▼  BehaviorDecision  (AgentEngine Layer 5)
Actions (ignore/like/share/adopt)
      │
      ▼  PropagationModel
New Propagation Events for next step
      │
      ▼  SentimentModel
Community Sentiment Update
      │
      ▼  CascadeDetector
Emergent Behavior Flags
```

---

## 3. Interface Contracts

### ExposureModel (RecSys-inspired, OASIS 차용)

> **설계 의도:** 실제 SNS는 모든 콘텐츠를 모든 사용자에게 보여주지 않는다.
> 추천 알고리즘이 feed를 큐레이션한다. OASIS의 RecSys 개념을 차용하여
> ExposureModel 내부에 **Feed Recommendation Engine**을 포함한다.

```python
class ExposureModel:
    def compute_exposure(
        self,
        agents: list[AgentState],
        graph: SocialNetwork,
        active_events: list[CampaignEvent],
        step: int,
        recsys_config: RecSysConfig | None = None,
    ) -> dict[UUID, ExposureResult]:
        """
        Two-phase exposure:

        Phase 1 — Candidate Generation:
            All content available this step (campaign ads, neighbor shares, expert reviews).
            P_exposure(i) = Σ_j (influence_j * W_ij) + direct_channel_exposure

        Phase 2 — RecSys Feed Ranking (OASIS-inspired):
            Each agent's feed is ranked by a simulated recommendation algorithm:

            feed_rank_score = w1 * recency
                            + w2 * social_affinity   (trust to content source)
                            + w3 * interest_match    (content topic vs personality)
                            + w4 * engagement_signal (likes/shares on content)
                            + w5 * ad_boost          (paid campaign budget allocation)

            Top-K items make it into the agent's visible feed (K = feed_capacity).
            Remaining items are suppressed (agent never sees them this step).

        This models the "filter bubble" and "algorithmic amplification" effects
        that drive real-world viral cascades.

        Returns dict of agent_id → ExposureResult
        """

@dataclass
class RecSysConfig:
    """Configurable recommendation algorithm weights."""
    feed_capacity: int = 20          # max items agent sees per step
    w_recency: float = 0.2
    w_social_affinity: float = 0.3   # trust to content source
    w_interest_match: float = 0.2    # personality alignment
    w_engagement_signal: float = 0.2 # existing likes/shares count
    w_ad_boost: float = 0.1          # paid promotion weight
    enable_filter_bubble: bool = True # same-community content boosted
    diversity_penalty: float = 0.05  # penalty for repeated same-source content

    # OASIS RecSys Reference Algorithms (informational)
    # Prophet implements its own weighted model but these are reference points:
    # - Twitter-style: In-network popularity + TwHIN-BERT out-of-network embedding similarity
    # - Reddit-style: Hot Score = log10(max(|u-d|, 1)) + sign(u-d) * (t-t0) / 45000
    # - Random: uniform random (baseline)
    # Prophet's RecSys combines elements of all three with marketing-specific ad_boost weight.

@dataclass
class ExposureResult:
    agent_id: UUID
    exposure_score: float        # 0.0–1.0
    exposed_events: list[CampaignEvent]
    social_feed: list[FeedItem]  # ranked by feed_rank_score (top-K only)
    suppressed_count: int        # items not shown due to RecSys filtering
    is_directly_exposed: bool    # reached by campaign channel (bypasses RecSys)
    feed_diversity_score: float  # 0–1, how diverse the feed is (low = echo chamber risk)
```

### PropagationModel

```python
class PropagationModel:
    def propagate(
        self,
        source_agent: AgentState,
        action: AgentAction,
        graph: SocialNetwork,
        message: CampaignMessage,
        step: int,
    ) -> list[PropagationEvent]:
        """
        Actions that generate propagation events:
            COMMENT  → Active propagation to discussed neighbors (subset)
            SHARE    → Active propagation to all neighbors (with endorsement)
            REPOST   → Active propagation to all neighbors (without endorsement, lower trust)
            ADOPT    → Passive propagation (adoption visible to direct neighbors)

        Actions that modify the network graph:
            FOLLOW   → Creates new edge from agent to content source
            UNFOLLOW → Removes edge from agent to content source
            MUTE     → Removes edge + blocks future exposure from source

        Actions that affect RecSys ranking:
            LIKE     → Boosts content engagement_signal score
            SAVE     → Strong purchase intent signal (tracked in analytics)
            SEARCH   → Increases exposure_score for searched content
        """

    def compute_diffusion_rate(
        self,
        adoption_history: list[int],   # adoption count per step
    ) -> float:
        """
        R(t) = dN/dt ≈ (N(t) - N(t-1))
        Returns current diffusion rate.
        """

@dataclass
class PropagationEvent:
    source_agent_id: UUID
    target_agent_id: UUID
    action_type: AgentAction
    probability: float
    step: int
    message_id: UUID
```

### SentimentModel

```python
class SentimentModel:
    def update_community_sentiment(
        self,
        community_id: UUID,
        agent_states: list[AgentState],
        expert_opinions: list[ExpertOpinion],
    ) -> CommunitySentiment:
        """
        sentiment = average(belief_i for agent_i in community)
        sentiment_variance = variance(belief_i)

        Expert opinion influence:
            E_i(t+1) = E_i(t) + α * O_k   (α = expert_influence_factor, default 0.3)
            where O_k is expert opinion score [-1, 1]
        """

    def detect_polarization(
        self,
        communities: list[CommunitySentiment],
        threshold: float = 0.4,
    ) -> bool:
        """sentiment_variance > threshold across communities"""

@dataclass
class CommunitySentiment:
    community_id: UUID
    mean_belief: float          # -1.0 to 1.0
    sentiment_variance: float
    adoption_rate: float        # % of agents that have adopted
    step: int
```

### CascadeDetector

```python
class CascadeDetector:
    def detect(
        self,
        step_results: StepResult,
        history: list[StepResult],
        config: CascadeConfig,
    ) -> list[EmergentEvent]:
        """
        Checks all emergent behavior thresholds:
            - Viral Cascade
            - Slow Adoption
            - Polarization
            - Collapse
            - Echo Chamber

        Returns list of EmergentEvent (may be empty).
        """

@dataclass
class CascadeConfig:
    viral_cascade_threshold: float = 0.15     # 15% adoption in single step
    slow_adoption_steps: int = 5              # N steps below threshold
    polarization_variance_threshold: float = 0.4
    collapse_drop_rate: float = 0.20          # 20% drop in 3 steps
    echo_chamber_ratio: float = 10.0          # internal/external link ratio

@dataclass
class EmergentEvent:
    event_type: Literal["viral_cascade", "slow_adoption", "polarization", "collapse", "echo_chamber"]
    step: int
    community_id: UUID | None
    severity: float                # 0.0–1.0
    description: str
    affected_agent_ids: list[UUID]
```

---

## 4. Expert Intervention Model

Expert agents (Community D) run LLM reasoning to generate opinions that influence the network:

```python
class ExpertInterventionEngine:
    async def generate_expert_opinion(
        self,
        expert_agent: AgentState,
        campaign: Campaign,
        current_sentiment: CommunitySentiment,
        llm_adapter: LLMAdapter,
    ) -> ExpertOpinion:
        """
        Constructs expert analysis prompt:
            "As a {expert_role}, analyze this product/campaign based on:
             - Community sentiment: {mean_belief}
             - Current adoption rate: {adoption_rate}
             - Product details: {campaign.message}
             - Recent agent feedback: {top_memories}"

        Parses LLM response into ExpertOpinion with score and reasoning.

        Always called at Tier 3. Falls back to rule-based opinion if LLM fails:
            if campaign.controversy > 0.7 → opinion.score = -0.5
            else → opinion.score = 0.2
        """

@dataclass
class ExpertOpinion:
    expert_agent_id: UUID
    score: float           # -1.0 to 1.0
    reasoning: str
    step: int
    affects_communities: list[UUID]
    confidence: float
```

---

## 5. Negative Cascade Model

```python
class NegativeCascadeModel:
    def compute_negative_spread(
        self,
        skeptic_agents: list[AgentState],
        negative_event: NegativeEvent,   # e.g., bad review, controversy
        graph: SocialNetwork,
    ) -> list[PropagationEvent]:
        """
        Negative content spreads faster among skeptics:
            P_neg(i→j) = skepticism_i * controversy * influencer_effect_i

        controversy: attribute of the negative event (0.0–1.0)
        """

@dataclass
class NegativeEvent:
    event_type: Literal["bad_review", "controversy", "fake_news", "competitor_attack"]
    content: str
    controversy: float
    source_agent_id: UUID | None
    step: int
```

---

## 6. Monte Carlo Simulation

```python
class MonteCarloRunner:
    async def run(
        self,
        simulation_config: SimulationConfig,
        n_runs: int = 100,
        parallel: bool = True,
    ) -> MonteCarloResult:
        """
        Runs simulation N times with identical config but different random seeds.
        Aggregates results to compute:
            - viral_probability: % of runs where viral cascade detected
            - expected_reach: mean final adoption count
            - community_adoption: per-community adoption rates
            - p5/p50/p95 confidence intervals

        Each run uses rule engine (Tier 1) only for speed unless
        config.monte_carlo_llm_enabled = True.
        """

@dataclass
class MonteCarloResult:
    n_runs: int
    viral_probability: float
    expected_reach: float
    community_adoption: dict[str, float]
    p5_reach: float
    p50_reach: float
    p95_reach: float
    run_summaries: list[RunSummary]
```

---

## 7. Diffusion Equation (Reference)

```
dA/dt = β * influence * trust * emotion * network_structure

A(t+1) = A(t) + diffusion_rate - decay

where:
    β            = base diffusion rate (campaign strength)
    influence    = source agent influence score
    trust        = W_ij edge weight
    emotion      = excitement - skepticism
    network_structure = degree(i) / max_degree  (hub bonus)
    decay        = 0.01 per step (forgetting rate)
```

---

## 8. Error Specification

| Situation | Exception Type | Recovery | Logging |
|-----------|---------------|----------|---------|
| RecSys weight sum ≠ 1.0 (±0.01 tolerance) | `ValueError` | Reject config — do not auto-normalize | ERROR |
| ExposureModel receives empty agent list | `ValueError` | Reject call | ERROR |
| No active campaign at current step | — (no-op) | All exposure scores = 0.0, skip pipeline | DEBUG |
| PropagationModel probability > 1.0 | — (clamp) | Clamp to 1.0 | WARN |
| PropagationModel probability < 0.0 | — (clamp) | Clamp to 0.0 | WARN |
| CascadeDetector receives fewer steps than `window_size` | — (skip) | Return empty events list, wait for sufficient data | DEBUG |
| ExpertIntervention LLM timeout | `LLMTimeoutError` | Fallback to Tier 1 heuristic opinion (sentiment = -0.3 default) | WARN |
| ExpertIntervention LLM parse error | `LLMParseError` | Fallback to Tier 1 heuristic opinion | WARN |
| Community sentiment NaN (division by zero in empty community) | — (guard) | Return 0.0 sentiment for empty community | WARN |
| Monte Carlo run crashes mid-execution | `SimulationStepError` | Mark run as FAILED, exclude from aggregation, continue remaining runs | ERROR |
| Cascade threshold ≤ 0 in config | `ValueError` | Reject config | ERROR |
| Negative diffusion rate R(t) computed | — (clamp) | Clamp to 0.0 | WARN |

---

## 9. Acceptance Criteria (Harness Tests)

| ID | Test | Expected |
|----|------|----------|
| DIF-01 | Exposure model with no active campaign | All exposure scores = 0 |
| DIF-02 | High-influence agent share → multiple propagation events | `len(events) > 0` |
| DIF-03 | Skeptic agent with controversy event → negative spread | Negative propagation detected |
| DIF-04 | Viral cascade detection triggers at threshold | `EmergentEvent(viral_cascade)` returned |
| DIF-05 | Polarization detection with split community sentiment | `EmergentEvent(polarization)` returned |
| DIF-06 | Expert negative opinion reduces community trust | `mean_belief` decreases after expert opinion |
| DIF-07 | Monte Carlo 100 runs completes within 60s | Benchmark |
| DIF-08 | Diffusion rate R(t) is 0 with no active agents | Correctly returns 0 |
| DIF-09 | Collapse detection after rapid belief drop | `EmergentEvent(collapse)` returned |
| DIF-10 | Propagation probability clamped to [0, 1] | No probability outside range |
