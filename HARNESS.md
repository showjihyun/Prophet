# HARNESS.md — Harness Engineering Context Strategy

**Prophet's framework for giving AI agents the context they need to operate.**

> Harness engineering is the discipline of tool-ifying the context (information + environment)
> an AI agent needs to behave correctly. It defines the structural principles that let an agent
> autonomously build a large system — without writing a single line by hand directly — and still
> produce consistently high-quality output.

---

## Document Relationships

```
HARNESS.md (why? the principles)          ← this document
    │
    ├── CLAUDE.md (what? operational rules)
    │     "Do not implement without a SPEC" → why? → Contract-first context (§2)
    │
    ├── AGENTS.md (who? role allocation)
    │     "backend-agent uses Sonnet" → why? → Cognitive resource allocation (§4)
    │
    ├── docs/spec/09_HARNESS_SPEC.md (how? test tooling)
    │     "MockLLM, Sandbox, Replay" → why? → Verification loop (§3)
    │
    └── docs/spec/15_DEV_WORKFLOW_SPEC.md (how? model selection)
          "Think with Opus, Code with Sonnet" → why? → Cognitive resource allocation (§4)
```

---

## §1. Context Hierarchy

The context an agent receives is not a single prompt — it is a **five-layer stack**.
Higher layers are more stable and persist longer; lower layers are more volatile.

```
┌─────────────────────────────────────────────────────────┐
│  L5: Session Memory                                      │  permanent (cross-session)
│  ┌─────────────────────────────────────────────────────┐│
│  │  L4: Project Identity                               ││  whole conversation (always loaded)
│  │  ┌─────────────────────────────────────────────────┐││
│  │  │  L3: SPEC Contract                              │││  per task (on-demand)
│  │  │  ┌─────────────────────────────────────────────┐│││
│  │  │  │  L2: Agent Role                             ││││  agent lifetime
│  │  │  │  ┌─────────────────────────────────────────┐│││││
│  │  │  │  │  L1: Task Prompt                        ││││││  single invocation
│  │  │  │  └─────────────────────────────────────────┘│││││
│  │  │  └─────────────────────────────────────────────┘││││
│  │  └─────────────────────────────────────────────────┘│││
│  └─────────────────────────────────────────────────────┘││
└─────────────────────────────────────────────────────────┘│
```

### What each layer carries

| Layer | File / Mechanism | Lifetime | Role | Prophet realization |
|-------|-----------------|----------|------|---------------------|
| **L5** | `MEMORY.md` + individual `.md` | Permanent | User profile, project strategy, past feedback | User role, Prophet hybrid strategy memory |
| **L4** | `CLAUDE.md` | Whole conversation | Project rules, tech stack, Phase status, hard rules | SPEC-GATE, uv-only, Phase progress table |
| **L3** | `docs/spec/*.md` | Per task | Function signatures, I/O types, Acceptance Criteria | 15 SPECs + 16 UI SPECs |
| **L2** | `AGENTS.md` + Agent prompt | Agent lifetime | Owned modules, selected model, coding rules | backend-agent=Sonnet, plan-agent=Opus |
| **L1** | Prompt passed to Agent tool | Single invocation | Specific task instruction, file paths, diffs | "Implement InjectEventModal per SPEC..." |

### Design principles

**1. Higher layers constrain lower layers.**
- L4 (CLAUDE.md) rule "no implementation without SPEC" constrains every L1 task
- L2 (Agent Role) rule "use Sonnet for implementation" constrains L1's model choice

**2. Lower layers reference upper layers.**
- An L1 task must read the L3 SPEC before implementing
- An L2 Agent Role must honor the rules in L4 CLAUDE.md

**3. Manage the token budget across layers.**
- L4 (CLAUDE.md) is loaded every time → keep it terse (≤ 200 lines recommended)
- L3 (SPEC) is read only when needed → can be detailed
- L5 (Memory) loads only the index; bodies are on-demand

---

## §2. Contract-First Context

> **Principle: the minimum unit of context is not natural language — it is an interface contract.**

### Why a contract

Natural language instructions are ambiguous. When an agent is generating 1,000 lines of
code, an instruction like "write a function that handles agent cognition" cannot
guarantee I/O types, invariants, or error handling.

A contract, by contrast, expresses expectations in a **verifiable** form:

```
❌ Weak context (natural language)
"Write a function that handles agent cognition"

✅ Strong context (contract)
SPEC: 01_AGENT_SPEC.md#layer-3-cognition
Input:  CognitionInput(perception: PerceptionResult, memories: list[MemoryRecord])
Output: CognitionResult(reasoning: str, action_intent: ActionIntent, confidence: float)
Constraint: tier=1 → rule-based, tier=3 → LLM call with fallback
```

### Prophet's contract system

```
SPEC document (defines the contract)
    │
    ├── Function signature: name, parameters, return type
    ├── Data types: dataclass / Pydantic / TypeScript interface
    ├── Constraints: ranges, invariants, preconditions
    ├── Error spec: which exceptions, in which conditions
    └── Acceptance Criteria: tests that verify compliance
```

### SPEC-GATE = contract enforcement

The SPEC-GATE rules in CLAUDE.md are the operational implementation of this principle:

```
Implementation request arrives
      │
      ▼
  Does a SPEC exist? ── No ──→ Write the SPEC first (create the contract)
      │
      Yes
      ▼
  Does the SPEC define signatures/types? ── No ──→ Update the SPEC (strengthen the contract)
      │
      Yes
      ▼
  Generate the test code (create the contract verifier)
      │
      ▼
  Implement the code (fulfill the contract)
```

### Traceability = contract tracking

The rule that every code module must carry a SPEC reference exists to **keep contract and
implementation linked**:

```python
class PerceptionLayer:
    """Agent Perception Layer.
    SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perception
    """
```

This is not a decorative comment. It is a mechanism for tracing "which contract this code
fulfills". When the contract changes, the reference lets you find every piece of code
affected by that change.

---

## §3. Verification Loop

> **Principle: context is not one-way delivery. It is a feedback loop.**

### One-way vs. two-way

```
❌ One-way (context delivery only)
SPEC ──→ agent ──→ code (no confirmation it is correct)

✅ Two-way (context + verification)
SPEC ──→ test(Red) ──→ agent ──→ code ──→ test(Green?) ──→ done or retry
              ↑                                  │
              └──────── feedback on FAIL ────────┘
```

### Red-Green-Refactor = verification loop in practice

Prophet's harness-first development flow:

```
1. Confirm/author the SPEC              ← define the contract
2. Generate test code (from the SPEC)   ← build the verifier
3. Run the tests → all FAIL (Red)       ← prove the verifier actually runs
4. Implement the code                   ← agent fulfills the contract
5. Run the tests → all PASS (Green)     ← confirm the fulfillment
6. Refactor (keeping tests green)       ← improve under a stable contract
```

### Verification tools = 09_HARNESS_SPEC implementation

| Verification tool | Role | 09_HARNESS_SPEC reference |
|-------------------|------|---------------------------|
| `pytest` | Backend contract verifier | F18 Unit Test Hooks |
| `MockLLMAdapter` | Verification without external dependencies | F19 Mock Environment |
| `SimulationSandbox` | Isolated integration verification | F24 Simulation Sandbox |
| `vitest` | Frontend contract verifier | — (07_FRONTEND_SPEC §9.5) |
| `playwright` | E2E user-scenario verification | — (07_FRONTEND_SPEC §9.5) |
| `tsc -b` | Type-contract verifier | — (TypeScript strict mode) |

### Agent self-correction

The core value of a verification loop: the agent can judge "done" for itself.

```
Agent: code written
    ↓
Agent: runs `uv run pytest tests/ -x -q`
    ↓
Harness: 586 passed, 0 failed
    ↓
Agent: can declare "Phase complete"    ← objective evidence, not a narrative judgment
```

On failure:

```
Harness: 3 failed — test_perception_returns_ranked_feed
    ↓
Agent: reads the error message and patches the code
    ↓
Agent: re-runs → passed
    ↓
Agent: done
```

Without this loop, the agent can only *guess* that its output is correct.
With the loop, it can *prove* it.

---

## §4. Cognitive Resource Allocation

> **Principle: a context strategy includes deciding how much cognition to spend on which task.**

### Prophet's 3-Tier parallel

The Prophet simulation applies a 3-Tier model to agent cognition. The same principle
applies to the development workflow:

| Prophet simulation | Development workflow | Share |
|--------------------|---------------------|-------|
| **Tier 1: Mass SLM** (80%) | **Sonnet 4.6**: code implementation, tests, refactoring | ~80% |
| **Tier 2: Heuristic** (10%) | **Direct tools**: Glob, Grep, Read (no model needed) | ~10% |
| **Tier 3: Elite LLM** (10%) | **Opus 4.6**: SPEC, planning, architecture, audit | ~10% |

### Why split

Using the strongest model for every task means:
- **Cost**: 67% more expensive (Phase B: $0.72 vs $0.24)
- **Speed**: 2.7× slower (Opus 45s vs Sonnet 15s per component)
- **Quality**: no improvement (with a proper SPEC, Sonnet implements it correctly)

**Key insight**: when the SPEC is detailed enough, deep reasoning is unnecessary at
the implementation step. Deep reasoning is needed to **write** the SPEC, not to
**follow** it.

### Decision flowchart

```
Task request arrives
      │
      ▼
  New SPEC / architectural decision needed? ── Yes ──→ Opus (Architect)
      │ No
      ▼
  Multi-module complex debugging? ── Yes ──→ Opus (Architect)
      │ No
      ▼
  Implementation against an existing SPEC? ── Yes ──→ Sonnet (Builder)
      │ No
      ▼
  File search / read? ── Yes ──→ Direct tool (Glob / Grep / Read)
      │ No
      ▼
  Opus (safe default)
```

Detailed implementation: `docs/spec/15_DEV_WORKFLOW_SPEC.md`

---

## §5. Parallel Decomposition

> **Principle: decompose large work at SPEC boundaries and connect the pieces via interface contracts.**

### SPEC = decomposition boundary

```
01_AGENT_SPEC ──── independent ──── 02_NETWORK_SPEC
       │                                    │
       └──── both required ──→ 03_DIFFUSION_SPEC
                                            │
                                    04_SIMULATION_SPEC (needs all)
```

This dependency graph naturally determines parallel work units:

```
Phase 2 (Agent) ──┐
                  ├── runs in parallel (independent)
Phase 3 (Network) ┘
                  ├── Phase 4 (Diffusion) ← after 2 + 3
                  └── Phase 5 (LLM) ──── parallel ──── Phase 7 (Frontend)
                                    └── Phase 6 (Orchestrator) ← after 2+3+4+5
```

### Interface contract = connective tissue

Parallel agents don't know each other's internals. The only connection between them
is the **interface contract in the SPEC**:

```
backend-agent (Agent Core)         backend-agent (Network Generator)
  │                                  │
  ├── AgentState (output)            ├── SocialNetwork (output)
  └── AgentTickResult (output)       └── NetworkMetrics (output)
           │                                  │
           └────── both ──────→ DiffusionEngine (consumer)
                                SPEC: 03_DIFFUSION_SPEC.md
                                Input: list[AgentState] + SocialNetwork
```

What happens when agent A changes a field on `AgentState`?
→ Update the SPEC first → consumers see the SPEC change → consumers update their code.

### AGENTS.md = operational decomposition matrix

The per-Phase parallel work matrix in `AGENTS.md` is the concrete execution plan for
this principle.

---

## §6. Context Decay Prevention

> **Principle: context decays over time. You need a source of truth and a sync mechanism.**

### Decay types and counter-measures

| Decay type | Symptom | Cause | Counter-measure |
|------------|---------|-------|-----------------|
| **SPEC ↔ Code drift** | Code behaves differently from SPEC | SPEC not updated after code changes | SPEC-GATE: SPEC edited first → then code |
| **Test ↔ Code divergence** | Tests pass but actual behavior differs | Tests not updated after implementation | Rule: SPEC change auto-triggers test update |
| **Phase status error** | Thought it was done, actually isn't | Subjective progress tracking | CLAUDE.md Phase table records test counts |
| **Memory decay** | Recommends functions/files that no longer exist | Memory not updated after refactor | Cross-check memory against current code before use |
| **Dependency drift** | Inter-module interfaces misalign | Only one side was updated | API contract tests (verify both sides) |

### Source-of-truth hierarchy

```
SPEC document ← Source of Truth (human-maintained)
    │
    ├──→ Test code ← Contract Verifier (derived from SPEC)
    │         │
    │         └──→ Production code ← Derived (only exists if tests pass)
    │
    ├──→ CLAUDE.md Phase table ← Status (verifiable via test counts)
    │
    └──→ Memory ← Point-in-time snapshot (verify before trusting)
```

### Sync rules

1. **SPEC change → update tests first → then code**
   - Violating the order creates SPEC ↔ code drift
   - See CLAUDE.md "SPEC Change → Test Auto-Generation Rule"

2. **Phase completion = defined by passing test count**
   - "Phase 2 complete = 81/81 GREEN" (no subjective judgment)
   - The Phase progress table in CLAUDE.md serves this role

3. **Verify memory before using it**
   - "Memory says function X exists" → grep for it before recommending
   - Memory is "this used to be true", not "this is still true"

4. **API contract tests on both sides**
   - Backend: `test_06_api_{endpoint}.py` (server-side contract verification)
   - Frontend: `apiClient.test.ts` (client-side contract verification)
   - Testing only one side misses drift on the other

---

## Summary: Six principles at a glance

```
┌─────────────────────────────────────────────────────────────────┐
│                    Harness Engineering                           │
│                    Context Strategy                              │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ §1       │  │ §2       │  │ §3       │                      │
│  │ Context  │  │ Contract │  │ Verify   │                      │
│  │ Hierarchy│  │ First    │  │ Loop     │                      │
│  │          │  │          │  │          │                      │
│  │ 5-layer  │→│ contract  │→│ tests    │                      │
│  │ stack    │  │ = min    │  │ prove   │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
│       ↕              ↕              ↕                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ §4       │  │ §5       │  │ §6       │                      │
│  │ Cognitive│  │ Parallel │  │ Decay    │                      │
│  │ Alloc    │  │ Decomp   │  │ Prevent  │                      │
│  │          │  │          │  │          │                      │
│  │ Opus/    │  │ split at │  │ SoT      │                      │
│  │ Sonnet   │  │ SPEC     │  │ sync     │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
│                                                                 │
│  These six combined produce:                                     │
│  "AI autonomously authors 1M LOC, yet stays consistently high   │
│  quality."                                                       │
└─────────────────────────────────────────────────────────────────┘
```

| # | Principle | One-line summary | Prophet implementation |
|---|-----------|------------------|-----------------------|
| §1 | Context Hierarchy | Context is a 5-layer stack | MEMORY → CLAUDE.md → SPEC → AGENTS.md → Task |
| §2 | Contract-First | The minimum unit is an interface contract | SPEC-GATE + traceability |
| §3 | Verification Loop | Tests prove completion | Red-Green-Refactor + 09_HARNESS_SPEC |
| §4 | Cognitive Allocation | Allocate cognition per task | Think with Opus, Code with Sonnet |
| §5 | Parallel Decomposition | Split at SPEC boundaries | AGENTS.md per-Phase matrix |
| §6 | Decay Prevention | Sync source of truth | SPEC change → test → code order |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-04-02 | Initial draft — six context strategy dimensions |
| 0.1.1 | 2026-04-11 | Translated to English, updated tsc reference to `tsc -b` |
