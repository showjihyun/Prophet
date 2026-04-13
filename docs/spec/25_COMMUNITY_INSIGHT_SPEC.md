# 25_COMMUNITY_INSIGHT_SPEC.md — Community Insight Tools

> Version: 0.1.0
> Created: 2026-04-11
> Status: APPROVED

---

## 1. Overview

Addresses two user experience gaps discovered during the Round 7 pilot:

1. **Pre-flight gap** — when a user configures community personality_profiles similarly and runs the simulation, all 4 communities show identical trajectories. The user only discovers this after wasting 5–30 minutes of wall-clock time.
2. **Post-flight gap** — even after the simulation ends, the results are just numbers (`adoption_rate=0.62`, `severity=0.41`). There is no narrative interpretation of "why did this happen."

This SPEC defines two tools that address these gaps:

| Tool | Timing | Input | Output | Cost |
|------|--------|-------|--------|------|
| **§2 Similarity Advisor** | Before RUN (CampaignSetupPage) | `communities[*].personality_profile` | warning banner + trait CV table | $0 (client-side) |
| **§5 EliteLLM Opinion Synthesis** | After RUN (CommunityOpinionPage) | step history + thread excerpts + agent samples | structured JSON narrative | ~$0.05 / community |

The two tools are **complementary** and are managed within the same SPEC — both address the same domain concept of "community differentiation."

---

## 2. Similarity Advisor (Pre-flight)

### 2.1 Goal
Measures and warns about personality_profile similarity **in real time** while
the user edits community settings on `CampaignSetupPage`.

### 2.2 Algorithm (CSI-01)

**Input**: `communities: CommunityConfigInput[]`

**Step 1 — Per-trait Coefficient of Variation**:
```
For each trait T in [openness, skepticism, trend_following, brand_loyalty, social_influence]:
  values = [c.personality_profile[T] for c in communities]
  mean = avg(values)
  stdDev = sqrt(sum((v - mean)^2 for v in values) / len(values))
  CV[T] = stdDev / mean (0 if mean == 0)
```

**Step 2 — Pairwise Cosine Similarity**:
```
For each pair (c_i, c_j) where i < j:
  vec_i = personality vector (5-dim)
  vec_j = personality vector
  sim_ij = dot(vec_i, vec_j) / (|vec_i| * |vec_j|)
```

**Step 3 — Severity decision**:
```
overallSimilarity = avg(sim_ij) over all pairs
severity =
  "critical" if overallSimilarity > 0.97 (virtually identical)
  "warning"  if overallSimilarity > 0.92 (too similar)
  "ok"       otherwise
```

**Step 4 — Suggestions**:
- Identify trait with lowest CV → "increase spread of {trait}"
- Identify pairs with similarity > 0.95 → "{a} ↔ {b} are nearly identical"
- Recommended baseline → "skeptic.skepticism≥0.80, early_adopter.openness≥0.80, ..."

### 2.3 Acceptance Criteria

| ID | Criterion | Test |
|----|-----------|------|
| CSI-AC-01 | When `communities.length < 2`, severity=ok and empty reports | `test_single_community_ok` |
| CSI-AC-02 | 4 identical personalities → severity=critical | `test_critical_when_identical` |
| CSI-AC-03 | CV for 5 traits is calculated exactly | `test_per_trait_cv_math` |
| CSI-AC-04 | All pairs with similarity > 0.95 included in `similarPairs` | `test_similar_pairs_detected` |
| CSI-AC-05 | Trait with lowest CV appears in the first suggestion | `test_suggests_lowest_cv_trait` |
| CSI-AC-06 | Banner not rendered when severity=ok | `test_banner_hidden_when_ok` |
| CSI-AC-07 | Red banner + ARIA role="alert" when severity=critical | `test_critical_banner_a11y` |
| CSI-AC-08 | Expanding banner details shows per-trait CV table | `test_per_trait_table_expand` |

### 2.4 Files

| File | Role |
|------|------|
| `frontend/src/components/campaign/communitySimilarity.ts` | Pure function — `analyzeCommunitySimilarity()` |
| `frontend/src/components/campaign/SimilarityWarningBanner.tsx` | Component — renders the banner |
| `frontend/src/__tests__/communitySimilarity.test.ts` | Algorithm unit tests |
| `frontend/src/__tests__/SimilarityWarningBanner.test.tsx` | Component tests |
| `frontend/src/pages/CampaignSetupPage.tsx` | Banner mount point |

### 2.5 Performance constraint
- Client-side, instant. Recalculates only when communities change via `useMemo`.
- Within 200ms (5 communities × 5 traits → 10 pairs × 5 dimensions is microsecond-scale computation)

---

## 3. Round 7-a Performance Fix (already applied)

Background: During the Round 7 pilot, 5000 agents × 8 steps took 28 minutes. The root
cause was that the `slm_llm_ratio` API parameter was not wired to `TierConfig` in
`step_runner.py`, so even when passing `slm_llm_ratio=1.0`, 10% of agents still
attempted Tier 3 LLM calls. With Ollama models absent, the fallback chain ran on every
call, accumulating 2–3 seconds of latency per call.

### 3.1 Fix (PERF-01)

`step_runner.py:407-414`:
```python
sim_slm_ratio = max(0.0, min(1.0, config.slm_llm_ratio))
effective_tier3 = config.llm_tier3_ratio * (1.0 - sim_slm_ratio)
tier_config = TierConfig(
    max_tier3_ratio=effective_tier3,
    max_tier2_ratio=config.llm_tier3_ratio,
)
```

`slm_llm_ratio=1.0` → `effective_tier3=0` → 0 Tier 3 calls.

### 3.2 Verification Results

| Condition | Before | After | Speedup |
|-----------|--------|-------|---------|
| 1000 agents × 10 steps | ~440s (extrapolated) | **17s** | **25.9x** |
| 5000 agents × 20 steps | ~72 min (extrapolated) | ~170s (3 min) | ~25x |

### 3.3 Additional Recommendations
- Sync the default `slm_model: phi4` (config.py) to an actually available model (`phi3:mini` or `llama3.1:8b`)
- Document in README that `slm_llm_ratio=1.0` is the documented method for users who want to reduce LLM cost to zero

---

## 4. Diffusion Calibration (to be split into a separate SPEC)

Planned for Round 7-c. Key findings:
- 0 `agent_type` branches in `engine/agent/cognition.py`, `engine/agent/decision.py`
- Only 3 exist in `engine/diffusion/negative_cascade.py`
- `personality.skepticism` has weak influence on propagation probability
- Result: almost no community differentiation occurs on the positive diffusion path

Proposed direction: strengthen the personality-trait → propagation_multiplier coupling in
`engine/agent/decision.py` or `engine/diffusion/propagation.py`. To be written as a
separate SPEC `26_DIFFUSION_CALIBRATION_SPEC.md`.

---

## 5. EliteLLM Opinion Synthesis (Post-flight)

(Implemented in a later round — this round proceeds with §2 Similarity Advisor only)

### 5.1 Goal
After the simulation completes, when a user clicks "why?" for a community, EliteLLM
receives the step time series + thread excerpts + agent samples and generates a
natural-language narrative.

### 5.2 Sketch

```
POST /api/v1/simulations/{sim_id}/communities/{community_id}/opinion-summary
  → CommunityOpinionService.synthesize()
  → LLMGateway.request(tier=3, prompt=...)
  → CommunityOpinionSnapshot { themes, divisions, key_quotes, sentiment_trend }
  → DB persisted
  → Frontend renders in CommunityOpinionPage
```

Detailed acceptance criteria will be filled in during the implementation round.

---

## 6. Change Log

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-04-11 | Initial SPEC. §2 Similarity Advisor + §3 PERF-01 fix retroactive doc + §5 EliteLLM placeholder |
