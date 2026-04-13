# SPEC 23 — Expert Engine LLM Integration

> Version: 0.1.0
> Updated: 2026-04-10
> Status: CURRENT

---

## Overview

Upgrade `ExpertInterventionEngine` from purely rule-based (`belief * skepticism`)
to LLM-assisted expert reasoning for Tier 3 agents, while preserving the fast
heuristic path for Tier 1/2.

| ID | Feature | Target Module |
|----|---------|---------------|
| EX-01~03 | **LLM Expert Reasoning** | `app.engine.agent.expert_engine` |
| EX-04 | **Prompt Template** | `app.llm.prompt_builder` |
| EX-05 | **Fallback** | Rule-based heuristic (existing) |

---

## Motivation

Expert agents currently compute `score = belief * skepticism`, which is a
1-dimensional signal. Real experts form nuanced opinions based on evidence,
domain context, and campaign attributes. LLM-generated expert reasoning
produces richer, more realistic opinions that influence surrounding agents.

---

## `1 EX: LLM Expert Reasoning

### `1.1 Modified Method

**EX-01** -- `ExpertInterventionEngine.generate_expert_opinion_async()`:

```python
async def generate_expert_opinion_async(
    self,
    agent: AgentState,
    campaign: CampaignConfig | CampaignEvent,
    step: int,
    gateway: LLMGateway | None = None,
) -> ExpertOpinion | None:
    """Generate expert opinion using LLM for Tier 3, heuristic for Tier 1/2.

    LLM path:
    - Builds prompt with agent personality, campaign context, step info
    - Calls gateway.complete() with tier=3
    - Parses response to extract score [-1.0, 1.0] and reasoning text
    - Falls back to heuristic on any failure

    Heuristic path (unchanged):
    - score = belief * skepticism
    - reasoning = template string
    """
```

**EX-02** -- LLM response parsing:
```
Expected format: "SCORE: {float}\nREASONING: {text}"
Parse score from first line, clamp to [-1.0, 1.0].
Reasoning is everything after first line.
If parsing fails, use heuristic score with LLM reasoning text.
```

**EX-03** -- The sync `generate_expert_opinion()` method remains unchanged
as the fast path. `generate_expert_opinion_async()` is called only for
Tier 3 agents from `async_tick()`.

### `1.2 Prompt Template

**EX-04** -- `PromptBuilder.build_expert_opinion_prompt()`:

```python
def build_expert_opinion_prompt(
    self,
    agent: AgentState,
    campaign_message: str,
    step: int,
) -> LLMPrompt:
    """Build prompt for expert opinion generation.

    System: "You are an expert analyst evaluating a marketing campaign..."
    User: Agent personality, campaign message, current step, community context
    max_tokens: 128
    """
```

### `1.3 Fallback

**EX-05** -- If LLM call fails (timeout, error, parsing failure), fall back
to the existing rule-based heuristic. Log warning but do not crash.

---

## Acceptance Criteria

| Test ID | Assertion |
|---------|-----------|
| EX-AC-01 | generate_expert_opinion (sync) behavior unchanged |
| EX-AC-02 | generate_expert_opinion_async with gateway returns LLM-based opinion |
| EX-AC-03 | generate_expert_opinion_async without gateway falls back to heuristic |
| EX-AC-04 | LLM response parsing extracts score and reasoning |
| EX-AC-05 | Malformed LLM response falls back to heuristic score |
| EX-AC-06 | Non-EXPERT agent returns None |

---

## Implementation Order

1. EX-04: Prompt template
2. EX-01~03: Async method + parsing
3. EX-05: Fallback tests

All must pass: `uv run pytest tests/test_23_expert_llm.py -v`
