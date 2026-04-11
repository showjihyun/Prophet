# AGENTS.md — Prophet Multi-Agent Working Guide

This file is the reference Claude Code consults when delegating work to
parallel sub-agents via the Agent tool.

---

## Working Principles

1. **SPEC-driven work** — every agent reads the relevant SPEC under `docs/spec/` before touching code.
2. **Honor interface contracts** — modules talk across boundaries only through the interfaces defined in SPEC.
3. **Independent parallelism** — modules that do not depend on each other run as parallel agents simultaneously.
4. **Harness verification** — after implementation, `uv run pytest` must pass on the affected harness tests.

---

## Model Selection Strategy

> **SPEC: `docs/spec/15_DEV_WORKFLOW_SPEC.md`** — "Think with Opus, Code with Sonnet"

| Agent Role | Model | Rationale |
|------------|-------|-----------|
| **plan-agent** (design) | Opus 4.6 | Architecture design, SPEC authoring, whole-system reasoning |
| **audit-agent** (audit) | Opus 4.6 | Consistency checks, trade-off analysis |
| **backend-agent** (implementation) | Sonnet 4.6 | SPEC-guided code generation |
| **frontend-agent** (implementation) | Sonnet 4.6 | Component/page generation |
| **harness-agent** (testing) | Sonnet 4.6 | Test scaffolding |
| **db-agent** (migrations) | Sonnet 4.6 | Alembic migration authoring |
| **code-reviewer** | Sonnet 4.6 | Pattern-based review |

When invoking the Agent tool, always pass an explicit `model` parameter
matched to the task type.

---

## Agent Role Inventory

### backend-agent
**Owns:** Python backend implementation | **Model: Sonnet 4.6**

| Module | SPEC | Directory |
|--------|------|-----------|
| Agent Engine | `01_AGENT_SPEC.md` | `backend/app/engine/agent/` |
| Network Generator | `02_NETWORK_SPEC.md` | `backend/app/engine/network/` |
| Diffusion Engine | `03_DIFFUSION_SPEC.md` | `backend/app/engine/diffusion/` |
| Simulation Orchestrator | `04_SIMULATION_SPEC.md` | `backend/app/engine/simulation/` |
| LLM Adapter | `05_LLM_SPEC.md` | `backend/app/llm/` |
| API Routes | `06_API_SPEC.md` | `backend/app/api/` |
| DB Models | `08_DB_SPEC.md` | `backend/app/models/` |

**Rules:**
- `uv` only (no pip)
- Type hints are mandatory on every function
- `async/await` is the default; sync code is reserved for pure computation
- Honor the interface signatures from SPEC exactly when implementing

---

### frontend-agent
**Owns:** React 18 frontend implementation | **Model: Sonnet 4.6**

**Design authority:** `DESIGN.md` (Pencil integration, design tokens, component mapping)

| Module | SPEC | UI SPEC (Pencil) | Directory |
|--------|------|------------------|-----------|
| Simulation Page | `07_FRONTEND_SPEC.md` §2 | `ui/UI_01_SIMULATION_MAIN.md` | `frontend/src/pages/` |
| Communities Page | `07_FRONTEND_SPEC.md` §2 | `ui/UI_02_COMMUNITIES_DETAIL.md` | `frontend/src/pages/` |
| Influencers Page | `07_FRONTEND_SPEC.md` §2 | `ui/UI_03_TOP_INFLUENCERS.md` | `frontend/src/pages/` |
| Agent Detail Page | `07_FRONTEND_SPEC.md` §2 | `ui/UI_04_AGENT_DETAIL.md` | `frontend/src/pages/` |
| Global Metrics Page | `07_FRONTEND_SPEC.md` §2 | `ui/UI_05_GLOBAL_METRICS.md` | `frontend/src/pages/` |
| Graph Panel | `07_FRONTEND_SPEC.md` §4 | `DESIGN.md` §5 Graph Engine | `frontend/src/components/graph/` |
| Timeline Panel | `07_FRONTEND_SPEC.md` §4 | — | `frontend/src/components/timeline/` |
| Control Panel | `07_FRONTEND_SPEC.md` §4 | — | `frontend/src/components/control/` |
| LLM Dashboard | `07_FRONTEND_SPEC.md` §4 | — | `frontend/src/components/llm/` |
| Zustand Store | `07_FRONTEND_SPEC.md` §5 | — | `frontend/src/store/` |
| API Client | `07_FRONTEND_SPEC.md` §8 | — | `frontend/src/api/` |
| TypeScript Types | `07_FRONTEND_SPEC.md` §7 | — | `frontend/src/types/` |

**Rules:**
- TypeScript strict mode
- Prefer `interface` (`type` only for unions/intersections)
- Component props must reuse the interfaces defined in SPEC verbatim
- Cytoscape.js graphs must hold ≥ 30 fps at 1,000 nodes
- Use the CSS variables from `DESIGN.md` §3 for design tokens (no hard-coding)
- Pencil Frame ID ↔ React component mapping lives in `DESIGN.md` §10

---

### harness-agent
**Owns:** Test harness and pytest implementation | **Model: Sonnet 4.6**

| Module | SPEC | Directory |
|--------|------|-----------|
| Mock Environment | `09_HARNESS_SPEC.md` §4 | `backend/harness/mocks/` |
| Fixtures | `09_HARNESS_SPEC.md` §13 | `backend/harness/fixtures/` |
| Runners | `09_HARNESS_SPEC.md` §3 | `backend/harness/runners/` |
| Sandbox | `09_HARNESS_SPEC.md` §8 | `backend/harness/sandbox.py` |
| Acceptance Tests | final §Acceptance in each SPEC | `backend/tests/` |

**Rules:**
- Harness code is written before production code
- `MockLLMAdapter` and `MockDatabase` must run with zero external dependencies
- Pytest marks are mandatory: `@pytest.mark.phase1`, `@pytest.mark.acceptance`, etc.
- `uv run pytest -v -m "phaseN"` must be able to run a specific phase in isolation

---

### db-agent
**Owns:** PostgreSQL schema and migrations | **Model: Sonnet 4.6**

| Module | SPEC | Directory |
|--------|------|-----------|
| SQLAlchemy Models | `08_DB_SPEC.md` §2 | `backend/app/models/` |
| Alembic Migrations | `08_DB_SPEC.md` §4 | `backend/migrations/` |
| pgvector Setup | `08_DB_SPEC.md` §2 (agent_memories) | `backend/app/models/memory.py` |

**Rules:**
- Never run DDL directly — all schema changes go through Alembic migrations
- `uv run alembic revision --autogenerate -m "description"`
- pgvector IVFFlat indexes are only created once there are ≥ 100 rows

---

## Per-Phase Parallel Work Matrix

The following diagrams show which agents can run in parallel at each Phase.

### Phase 1: Project Scaffold + Harness Foundations

```
┌─────────────────────────────────────────────────────────┐
│ Runs in parallel                                         │
│                                                          │
│  backend-agent          frontend-agent    harness-agent  │
│  ├ uv init              ├ npm create vite  ├ conftest.py │
│  ├ pyproject.toml       ├ package.json     ├ MockLLM     │
│  ├ FastAPI skeleton     ├ Vite config      ├ MockDB      │
│  └ Alembic init         └ Tailwind setup   └ Sandbox     │
│                                                          │
│  db-agent (depends on backend-agent init)                │
│  ├ SQLAlchemy models                                     │
│  └ Initial migration                                     │
└─────────────────────────────────────────────────────────┘
```

### Phases 2–4: Engine Implementation

```
┌─────────────────────────────────────────────────────────┐
│ Phase 2             Phase 3              Phase 4         │
│ (Agent Core)       (Network Generator)  (Diffusion)      │
│                                                          │
│  backend-agent:     backend-agent:       backend-agent:  │
│  ├ agent_core.py    ├ generator.py       ├ exposure.py   │
│  ├ perception.py    ├ community_graph.py ├ propagation.py│
│  ├ memory_layer.py  ├ influencer.py      ├ cascade.py    │
│  ├ emotion.py       └ edge_weights.py    └ sentiment.py  │
│  ├ cognition.py                                          │
│  ├ decision.py      harness-agent:       harness-agent:  │
│  └ influence.py     └ NET-01 ~ NET-10   └ DIF-01~DIF-10 │
│                                                          │
│  harness-agent:                                          │
│  └ AGT-01 ~ AGT-08                                      │
│                                                          │
│  ⚠ Phases 2 and 3 are independent → can run in parallel  │
│  ⚠ Phase 4 starts only after Phases 2 + 3 complete       │
└─────────────────────────────────────────────────────────┘
```

### Phases 5–7: Integration

```
┌─────────────────────────────────────────────────────────┐
│ Phase 5               Phase 6              Phase 7       │
│ (LLM Integration)    (Orchestrator)       (Frontend)     │
│                                                          │
│  backend-agent:       backend-agent:       frontend-agent│
│  ├ adapter.py         ├ orchestrator.py    ├ Pages       │
│  ├ ollama_client.py   ├ step_runner.py     ├ GraphPanel  │
│  ├ claude_client.py   ├ metric_collector   ├ Timeline    │
│  ├ openai_client.py   ├ monte_carlo.py     ├ Control     │
│  ├ prompt_builder.py  └ WebSocket          ├ LLM Dash    │
│  └ cache.py                                └ API Client  │
│                                                          │
│  ⚠ Phases 5 and 7 are independent → can run in parallel  │
│  ⚠ Phase 6 starts only after Phases 2+3+4+5 complete     │
└─────────────────────────────────────────────────────────┘
```

---

## Inter-Agent Communication Rules

1. **Interface boundary** — agents only communicate through the interfaces defined in SPEC. No agent depends on another agent's internal implementation.

2. **Shared types** — every shared data type lives in one of these locations:
   - Backend: `backend/app/engine/types.py` (shared dataclasses/enums)
   - Frontend: `frontend/src/types/` (TypeScript interfaces)

3. **DB schema changes** — only `db-agent` creates migrations. If another agent needs a schema change, it updates the SPEC first and then delegates to `db-agent`.

4. **API contract** — the endpoint contract in `06_API_SPEC.md` is the one and only interface between backend-agent and frontend-agent. Both sides obey it.

---

## Agent Execution Example

```
# Phase 1 — 4 agents running in parallel
User: "Start Phase 1"

Claude:
  ├── Agent(backend-agent):  uv init + FastAPI skeleton
  ├── Agent(frontend-agent): Vite + React 18 init
  ├── Agent(harness-agent):  conftest.py + MockLLM + MockDB + Sandbox
  └── Agent(db-agent):       SQLAlchemy models + Alembic init  (after backend init)
```

---

## Completion Checklist — Agent Task Done Criteria

- [ ] Does it match the SPEC interface signatures exactly?
- [ ] Are the Phase's Acceptance Criteria tests written?
- [ ] Does `uv run pytest -v -m "phaseN"` pass?
- [ ] Any lingering pip usage? (should be zero)
- [ ] Do LLM calls have fallbacks wired up?
- [ ] Does the code follow async/await patterns?
- [ ] Are type hints present on every function?
