# README Use Case Pilots — 2026-04-12

This document records end-to-end pilot runs of each marketing use case
described in `README.md`, with the actual engine output placed next to
the README claim. It is the evidence backing (or, where applicable,
contradicting) the promises the landing page makes.

**Headline finding:** Prophet's campaign framing inputs
(`novelty`, `utility`, `controversy`) are **not connected to the
propagation formula**. All six pilots produced statistically identical
step-by-step trajectories regardless of how the campaign was framed.
See [Root cause](#root-cause-novelty--utility--controversy-never-reach-the-tick-loop) below — it is the most important thing in this document.

## Method

- Stack: backend commit `1669ccb` (post-PR-#2 merge), Ollama `0.11.10`,
  model `llama3.2:1b`, `slm_llm_ratio=0.98` (Tier-1 SLM only, one
  Tier-3 call per community at the end for the opinion narrative).
- Runner: `backend/scripts/run_use_case_pilot.py` — creates a fresh
  simulation, steps 12 times, pauses, then calls the cross-community
  `/__overall__/opinion-summary` endpoint. Raw JSON blobs saved under
  `docs/pilot_results/{case}.json`.
- Seed: `42` for every pilot — deterministic runs so the delta between
  campaign framings is attributable to inputs alone.
- Populations:
  - UC1 + UC2 — 1,030 agents, 5 communities (early_adopters, mainstream,
    skeptics, experts, influencers) in a 20/60/15/3/5 ratio.
  - UC3 — 880 agents with an engineering-heavy employee mix
    (engineering / product / sales / leadership / hr).

## Results

| Case | controversy | utility | novelty | pop | step-1 adoption | step-6 adoption | final adoption | mean sentiment | emergent events |
|------|:-----------:|:-------:|:-------:|:---:|:---------------:|:---------------:|:--------------:|:--------------:|:---------------:|
| **uc1_baseline**         | 0.80 | 0.30 | 0.50 | 1030 | 0.357 | 0.904 | **0.973** | +0.656 | viral_cascade×2, slow_adoption×1 |
| **uc1_reframed**         | 0.20 | 0.75 | 0.80 | 1030 | 0.357 | 0.905 | **0.974** | +0.656 | viral_cascade×2, slow_adoption×1 |
| **uc2_strategy_b**       | 0.85 | 0.40 | 0.30 | 1030 | 0.357 | 0.903 | **0.975** | +0.656 | viral_cascade×2, slow_adoption×1 |
| **uc2_strategy_c**       | 0.15 | 0.85 | 0.75 | 1030 | 0.357 | 0.904 | **0.975** | +0.657 | viral_cascade×2, slow_adoption×1 |
| **uc3_rto_raw**          | 0.85 | 0.20 | 0.10 |  880 | 0.284 | 0.761 | **0.914** | +0.639 | viral_cascade×2 |
| **uc3_rto_restructured** | 0.35 | 0.70 | 0.45 |  880 | 0.284 | 0.760 | **0.911** | +0.639 | viral_cascade×2 |

Notice the columns. Within a given population size, **every single
pilot has identical step-by-step adoption** to 3 decimal places,
regardless of whether the campaign was framed as a 0.85-controversy
compliance message or a 0.15-controversy empowerment message.

## Claim-by-claim verdict

### ❌ UC1 — Pre-test a product launch

> "The simulation showed the message polarized the skeptical community at
> step 18 and adoption stalled at 12%. They reframed the campaign and
> hit 31% in the second simulation."

| Metric | README claim | Baseline (uc1_baseline) | Reframed (uc1_reframed) |
|---|---|---|---|
| Skeptic polarization | Yes | **No** — skeptics community adopts at ~86% | **No** — skeptics adopts at ~86% |
| Baseline adoption | Stall at 12% | **97.3%** (runaway cascade) | — |
| Reframed adoption | 31% | — | **97.4%** |
| Lift from reframing | +19 pts | — | **+0.1 pts** |

**Verdict:** the README scenario is not reproducible on the current
engine. Both the stall and the polarization claims are fiction, because
the campaign parameters that should drive them are ignored by the tick
loop.

### ❌ UC2 — Pre-screen public health messages

> "Strategy B caused echo-chamber formation in skeptical communities.
> Strategy C triggered a positive viral cascade through influencer nodes."

| Metric | README claim | Strategy B | Strategy C |
|---|---|---|---|
| Strategy B echo-chamber | Yes | **Cascade detector never fired `echo_chamber`** — only viral_cascade + slow_adoption |
| Strategy C viral cascade | Yes | — | `viral_cascade` fires (×2) — but Strategy B ALSO fires viral_cascade (×2) |
| Final adoption delta | "3× projected" | 0.975 | 0.975 (identical) |

**Verdict:** both strategies end at 97.5% adoption with an identical
emergent-event profile. The cascade detector IS firing `viral_cascade`
in both, which is directionally right for Strategy C but wrong for
Strategy B.

### ❌ UC3 — Stress-test internal communications

> "Prophet predicted a 38% sentiment collapse in engineering. They
> restructured the announcement with carve-outs and cut opposition by
> 60%."

| Metric | README claim | Raw mandate | Restructured |
|---|---|---|---|
| Engineering sentiment collapse | -38 pts | Engineering community ends at +0.7 mean_belief (very positive) |
| Restructured opposition | -60% vs raw | 0.914 vs 0.911 adoption — **+0.3 pts difference** |

**Verdict:** the engineering community doesn't collapse at all — it
ends strongly positive. The restructured message has zero measurable
effect.

### ✅ The opinion synthesis narrative

On the plus side: the cross-community opinion endpoint WORKED end-to-end
for all six pilots (6/6 non-stub `llama3.2:1b` responses, UNIQUE
constraint + shape guards held up, no deadlocks). The new R8-2
opinion-synthesis plumbing is production-ready.

However, the small LLM frequently **hallucinated narratives that
matched the README claims** rather than the actual metrics. For example,
`uc1_baseline` returned the theme `"rapid cascade in early_adopters
stalls against skeptic resistance"` while the actual metrics showed
every community at 86-100% adoption. The llama3.2:1b is too weak to
stay anchored to the numeric inputs — it reads the community names and
confabulates a plausible story. Using a bigger Tier-3 model would help,
but the underlying issue is that the hallucinated narrative happens to
align with what SHOULD have happened, masking the engine bug.

## Root cause: novelty + utility + controversy never reach the tick loop

`backend/app/engine/simulation/step_runner.py` reads the campaign
parameters once, at line 81-94, into a `CampaignEvent`:

```python
CampaignEvent(
    ...,
    novelty=campaign.novelty,
    controversy=campaign.controversy,
    utility=campaign.utility,
    ...,
)
```

That `CampaignEvent` is then converted into an `EnvironmentEvent` by
`_build_environment_events()` (line 97-116), which **only copies
`message`, `channel`, and `timestamp`**. `novelty`, `utility`, and
`controversy` are dropped on the floor at this boundary.

Meanwhile, `backend/app/engine/agent/tick.py` builds the `MessageStrength`
that feeds `propagation_probability` like this (line 215):

```python
ms = MessageStrength(
    novelty=min(media_signal, 1.0),                              # ← agent-level
    controversy=campaign_controversy,                             # ← method param, defaults 0.0
    utility=max(0.0, min(1.0, cognition.evaluation_score / 2.0)), # ← agent-level
)
```

`media_signal` is derived from the agent's perception of its feed, and
`cognition.evaluation_score` comes from the cognition layer's scoring
of the received content. Both are downstream of the message text but
have **no link to the numeric campaign parameters**. `campaign_controversy`
is a method parameter with a default of `0.0`, and a global grep of
`step_runner.py` for `campaign_controversy` returns **zero hits** —
nothing ever passes it through.

Net effect: the entire `(novelty, utility, controversy)` slider on the
campaign setup page is a UI decoration. The simulation outcome is
driven exclusively by population size / mix / seed, which is why every
pilot collapses to an identical trajectory.

## Follow-up items (proposed next P1 task)

1. **Wire `campaign.{novelty,utility,controversy}` into the tick**
   - Thread the values through `_build_environment_events` (or a sibling
     attribute on `EnvironmentEvent`) so the agent's perception layer
     sees them.
   - Pass them through the `AgentTick.tick()` call chain from
     `step_runner._run_step_py` so the `MessageStrength` constructor
     has real values. The simplest first move: make `campaign_novelty`
     and `campaign_utility` positional parameters next to the existing
     `campaign_controversy`, set in the runner from `state.config.campaign`.
   - Decide whether campaign values **replace** the agent-derived values
     or **blend** with them. Blending (e.g., `novelty = 0.6 * campaign +
     0.4 * media_signal`) is probably more honest but slightly harder
     to calibrate.

2. **Regression tests that compare outcomes across campaign framings**
   - Add a test class in `test_04_simulation_acceptance.py` (or a new
     file) that runs two simulations with identical seeds and
     communities but different campaign parameters, and asserts the
     final adoption rates are meaningfully different (e.g., >10pts).
     Today's pilot would have failed such a test immediately.

3. **Re-calibrate after the wire is fixed**
   - The R8-3 formula coefficients were tuned in isolation. Once
     campaign values actually drive the message strength, the
     coefficients will almost certainly need another pass to hit
     the "stuck at 12%" scenario the README claims. This is cheap.

4. **Harden the opinion LLM prompt**
   - Require the LLM to quote a numeric value from the per-community
     brief in its `summary` field. Right now small LLMs happily ignore
     the data and write fiction. A literal "must cite adoption=X.XX"
     rule would surface the disconnect immediately.
   - Alternatively, restrict Tier-3 opinion synthesis to a bigger
     model (Claude/GPT) when available — llama3.2:1b is too small
     for anti-hallucination discipline.

5. **Update README with a calibration disclaimer** (or remove the
   quantitative claims until the fix lands)
   - The "stuck at 12% → reframed to 31%" numbers cannot currently be
     reproduced. Either fix the engine first, or soften the numbers to
     "stalled adoption" / "meaningful lift" until the regression tests
     from (2) prove the claim again.

## Artifact manifest

Raw pilot JSON blobs (one per case):

- `docs/pilot_results/uc1_baseline.json`
- `docs/pilot_results/uc1_reframed.json`
- `docs/pilot_results/uc2_strategy_b.json`
- `docs/pilot_results/uc2_strategy_c.json`
- `docs/pilot_results/uc3_rto_raw.json`
- `docs/pilot_results/uc3_rto_restructured.json`

Each blob contains the full step history, per-community final metrics,
emergent event counts, and the EliteLLM opinion-synthesis response —
so the analysis above can be re-verified against raw data by anyone
re-reading this doc.

Runner script (reproducible): `backend/scripts/run_use_case_pilot.py`.
