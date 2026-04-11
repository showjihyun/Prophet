# CLAUDE.md — Prophet (MCASP)

This is the reference file Claude Code always consults when working in this project.

---

## Project Overview

**Prophet = MCASP (Multi-Community Agent Simulation Platform)**

A platform that pre-simulates how marketing campaigns, policies, and messages spread
through an AI-driven virtual society. It is an agent-based social simulation engine
that combines LLM + GraphRAG + viral diffusion.

- SPEC documents: `docs/spec/` (see `docs/spec/MASTER_SPEC.md` for the current list)
- Source briefs: `docs/init/` (read-only reference)
- Master SPEC: `docs/spec/MASTER_SPEC.md` (index)
- **Context strategy**: `HARNESS.md` (six principles — hierarchy / contract / verification / cognitive allocation / parallel decomposition / decay prevention)

> **Note:** Core SPECs (00-09, UI) are managed via `.gitignore` for IP protection.
> If they have been removed locally, treat the `SPEC:` references in code docstrings
> as historical pointers.

---

## Development Approach

**SPEC-DRIVEN + Harness Engineering**

### ⛔ SPEC-GATE Rules (never violate)

1. **No code without a SPEC**
   - If the feature you're implementing does not have a SPEC under `docs/spec/`, **do not write code.**
   - When you receive a request for a feature with no SPEC, **write the SPEC first**, then implement.
   - The order is always: write SPEC → user confirmation → implement.

2. **SPEC mapping checklist**
   - Before writing any code, run through this checklist:
     ```
     □ Does a SPEC document for this feature exist under docs/spec/?
     □ Does the SPEC define function signatures and I/O types?
     □ Does the SPEC version match the current implementation target?
     ```
   - If any answer is NO, **stop implementing** and update the SPEC first.

3. **SPEC-to-code traceability**
   - Every module/class docstring must carry a SPEC reference:
     ```python
     class PerceptionLayer:
         """Agent Perception Layer.
         SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perception
         """
     ```
     ```typescript
     /**
      * SimulationDashboard component
      * @spec docs/spec/07_FRONTEND_SPEC.md#simulation-dashboard
      */
     ```

4. **The SPEC interface contract is law**
   - Never break the function signatures or I/O types defined in a SPEC.
   - If the interface must change, **update the SPEC first**, bump its version, then change the code.

### Active SPEC files (docs/spec/)

| SPEC document | Scope | Status |
|---------------|-------|--------|
| `MASTER_SPEC.md` | Full index | Current |
| `SPEC_CHECKLIST.md` | Test count / coverage checklist | Current |
| `16_COMMUNITY_MGMT_SPEC.md` | Community CRUD + template management | Current |
| `17_PERFORMANCE_SPEC.md` | Backend performance optimization | Current |
| `18_FRONTEND_PERFORMANCE_SPEC.md` | Frontend perf + 3D graph + AgentDetail + SimulationList | Current |
| `19_SIMULATION_INTEGRITY_SPEC.md` | Simulation fidelity audit (6 Phase) | Current |
| `20_CLEAN_ARCHITECTURE_SPEC.md` | Clean Architecture (Repository/Service/Controller) | Current |
| `21_SIMULATION_QUALITY_SPEC.md` | Simulation quality (consolidated P1 SQ + P2 EC/BC/CG + P3 RF/HM/MP) | Current |
| `22_CONVERSATION_THREAD_SPEC.md` | Real thread capture + storage + API | Current |
| `23_EXPERT_LLM_SPEC.md` | Expert engine LLM integration (+ rule-based fallback) | Current |

> **Consolidation history**: the three earlier files `19_SIMULATION_QUALITY_SPEC.md`,
> `20_SIMULATION_QUALITY_P2_SPEC.md`, and `21_SIMULATION_QUALITY_P3_SPEC.md` were merged
> into `21_SIMULATION_QUALITY_SPEC.md` on 2026-04-10. All original anchor IDs (`SQ-`,
> `EC-`, `BC-`, `CG-`, `RF-`, `HM-`, `MP-`) are preserved.
>
> Core engine SPECs (00-09) and UI SPECs (16 files) are `.gitignore`-protected for IP.
> The `SPEC: docs/spec/01_AGENT_SPEC.md#...` references in code docstrings are historical.

### SPEC Change → Test Auto-Generation Rule

> **Core principle: SPEC change → generate tests FIRST → then implement (Red-Green-Refactor)**
>
> Tests verify the SPEC contract. They do not chase the implementation.
> It should be possible to write tests from the SPEC alone, and without an implementation
> the tests should FAIL — that is normal.

**When a Backend SPEC changes:**
- For every public interface defined in the SPEC, create or update test files under
  `backend/tests/` **before** the implementation.
- Test file naming: `test_{spec_number}_{module}.py`
  - e.g., `01_AGENT_SPEC.md` changes → `test_01_perception.py`, `test_01_memory.py`, ...
- Tests must be written to **fail (Red)** while no implementation exists:
  ```python
  """
  Auto-generated from SPEC: docs/spec/01_AGENT_SPEC.md
  SPEC Version: 0.1.0
  Generated BEFORE implementation — tests define the contract.
  """
  import pytest

  class TestPerceptionLayer:
      """SPEC: 01_AGENT_SPEC.md#layer-1-perception"""

      def test_observe_returns_perception_result(self):
          """SPEC contract: observe() → PerceptionResult"""
          from app.engine.agent.perception import PerceptionLayer
          layer = PerceptionLayer()
          result = layer.observe(agent=..., events=[], neighbors=[])
          assert hasattr(result, 'feed_items')
          assert hasattr(result, 'social_signals')
          assert hasattr(result, 'total_exposure_score')

      def test_observe_ranks_by_exposure_score(self):
          """SPEC contract: feed_items ranked by exposure_score desc"""
          from app.engine.agent.perception import PerceptionLayer
          layer = PerceptionLayer()
          result = layer.observe(agent=..., events=mock_events, neighbors=[])
          scores = [item.exposure_score for item in result.feed_items]
          assert scores == sorted(scores, reverse=True)
  ```
- After writing the tests, run `uv run pytest --collect-only` to confirm they are collected.
- Update the harness tests as well: the matching runner under `backend/harness/`.

**When a Frontend SPEC changes:**
- For every component/hook defined in the SPEC, create or update test files under
  `frontend/src/__tests__/` **before** the implementation.
- Test file naming: `{ComponentName}.test.tsx` or `{hookName}.test.ts`
- Tests must be written to **fail (Red)** while no implementation exists:
  ```typescript
  /**
   * Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md
   * SPEC Version: 0.1.0
   * Generated BEFORE implementation — tests define the contract.
   */
  import { render, screen } from '@testing-library/react';

  describe('SimulationDashboard', () => {
    /** @spec 07_FRONTEND_SPEC.md#simulation-dashboard */
    it('renders graph visualization panel', () => {
      // Will fail until SimulationDashboard is implemented
      const { SimulationDashboard } = require('@/components/SimulationDashboard');
      render(<SimulationDashboard />);
      expect(screen.getByTestId('graph-panel')).toBeInTheDocument();
    });

    it('displays real-time metrics via WebSocket', () => {
      const { SimulationDashboard } = require('@/components/SimulationDashboard');
      render(<SimulationDashboard />);
      expect(screen.getByTestId('metrics-panel')).toBeInTheDocument();
    });
  });
  ```

**When an API SPEC changes (both sides):**
- Backend: create `backend/tests/test_06_api_{endpoint}.py`
- Frontend: create `frontend/src/api/__tests__/{endpoint}.test.ts`
- API contract tests must verify the request/response schema.

### How to author a new SPEC

When a request arrives for a feature with no SPEC:

```
1. Create the SPEC under docs/spec/ (follow the existing numbering scheme)
2. Add the reference to MASTER_SPEC.md
3. Ask the user to review the SPEC
4. After approval, generate the test code (before implementation!)
5. Confirm the tests FAIL (Red)
6. Start implementing (goal: make the tests pass)
7. Confirm the tests PASS (Green)
```

### Harness-first development flow (Red-Green-Refactor)

```
Write / confirm the SPEC
     ↓
Generate test code (from the SPEC contract, before implementation!)
     ↓
Run the tests → confirm all FAIL (Red)
     ↓
Write harness fixtures / mocks
     ↓
Implement the code (goal: pass the tests)
     ↓
Run the tests → confirm all PASS (Green)
     ↓
Refactor (improve while keeping tests green)
     ↓
Phase complete
```

5. Every Phase must pass its harness tests before moving to the next.
6. Every LLM-dependent feature must have an SLM (Tier 1) fallback.

### Development model selection strategy (Think with Opus, Code with Sonnet)

> **SPEC: `docs/spec/15_DEV_WORKFLOW_SPEC.md`**

Apply Prophet's simulation 3-Tier strategy to the development workflow as well.

| Task type | Model | Share |
|-----------|-------|-------|
| **Planning / analysis**: SPEC authoring, plan drafting, architecture design, audit, complex debugging | **Opus 4.6** | ~10% |
| **Implementation / tests**: code, test generation, refactoring, code review, boilerplate | **Sonnet 4.6** | ~80% |
| **Direct tools**: Glob, Grep, Read (no model needed) | — | ~10% |

**When invoking the Agent tool, pass the `model` parameter explicitly:**
```
# Planning — Opus
Agent(subagent_type="Plan", model="opus")

# Code implementation — Sonnet
Agent(subagent_type="general-purpose", model="sonnet")

# Deep exploration — Opus
Agent(subagent_type="Explore", model="opus")

# Code review — Sonnet
Agent(subagent_type="feature-dev:code-reviewer", model="sonnet")
```

**Exception**: if the user specifies a model explicitly, honor it immediately.

---

## Tech Stack

### Backend
- **Python 3.12+** / **FastAPI** (async)
- **SQLAlchemy 2.0** (async ORM) + **Alembic** (migrations)
- **PostgreSQL 16** + **pgvector** (vector memory)
- **Valkey** (LLM cache, sessions)
- **NetworkX** (social graph at runtime)


### LLM
- **Ollama** (local, default) — `ollama-python`
- **Claude API** — `anthropic` SDK
- **OpenAI API** — `openai` SDK

### Frontend
- **React 18** + **TypeScript** + **Vite**
- **react-force-graph-3d** (three.js-based 3D graph visualization)
- **Cytoscape.js** (EgoGraph and other auxiliary 2D graphs)
- **Recharts** (Timeline / Metric charts)
- **Zustand** (state management)
- **TanStack Query** (server state — migration complete across all pages)
- **Tailwind CSS** + **shadcn/ui**

---

## Package Management — uv only

```bash
# ✅ Correct
uv add <package>
uv add --dev <package>
uv sync
uv run <command>
uv run pytest
uv run uvicorn app.main:app --reload

# ❌ Forbidden
pip install ...
pip3 install ...
python -m pip install ...
```

- Dependency files: `pyproject.toml` + `uv.lock`
- Do not create a `requirements.txt`

---

## Directory Layout

```
Prophet/
├── CLAUDE.md          ← this file
├── AGENTS.md          ← multi-agent working guide
├── DESIGN.md          ← UI design master (Pencil integration)
├── docs/
│   ├── init/          ← source briefs (read-only, 12 files)
│   └── spec/          ← SPEC documents (see MASTER_SPEC.md for the list)
├── backend/           ← FastAPI backend
│   ├── app/
│   ├── harness/       ← F18–F30 test harness
│   ├── tests/
│   ├── migrations/    ← Alembic
│   └── pyproject.toml
└── frontend/          ← React 18 frontend
    ├── src/
    └── package.json
```

---

## Coding Rules

### Python
- Prefer `async/await` — sync code is reserved for pure I/O-free computation
- Type hints are mandatory on every function parameter and return value
- Define data structures with `@dataclass` or `pydantic BaseModel`
- Raise specific exception types (`LLMTimeoutError`, `NetworkValidationError`, ...)
- Run tests with `uv run pytest`

### TypeScript / React
- Prefer `interface` (use `type` only for unions/intersections)
- React 18 — no `use client` (Vite SPA)
- Zustand stores live only in `src/store/`
- All API calls go through `src/api/client.ts`
- **⛔ No hard-coded domain enum literals** — values like `SimulationStatus` and
  `AgentAction` must never appear as inline string literals. Use the constants in
  `@/config/constants` (`SIM_STATUS`, `TERMINAL_SIM_STATUSES`, `STARTABLE_SIM_STATUSES`,
  etc.). When a new enum value is needed, add it to `constants.ts` first, then import
  it. SPEC: `docs/spec/18_FRONTEND_PERFORMANCE_SPEC.md`

### DB
- All migrations go through Alembic (`uv run alembic revision --autogenerate`)
- Never run DDL directly — always through `migrations/`

---

## Phase Progress

| Phase | Scope | Status |
|-------|-------|--------|
| **Phase 0** | SPEC authoring | ✅ Done (15 SPECs + 16 UI SPECs) |
| **Phase 1** | Project skeleton + harness foundation | ✅ Done (8/8 GREEN tests) |
| **Phase 2** | Agent Core (6-Layer) | ✅ Done (81/81 GREEN tests) |
| **Phase 3** | Network Generator | ✅ Done (19/19 GREEN tests) |
| **Phase 4** | Diffusion Engine | ✅ Done (78/78 GREEN tests) |
| **Phase 5** | LLM Integration | ✅ Done (92/92 GREEN tests) |
| **Phase 6** | Simulation Orchestrator + API | ✅ Done (127/127 GREEN tests) |
| **Phase 7** | Visualization (Frontend) | ✅ Done (tsc 0 errors, build OK) |
| **Phase A** | API → Frontend wire-up (37 endpoints) | ✅ Done |
| **Phase B** | 5 feature UIs (Inject / Replay / MC / Engine / Compare) | ✅ Done |
| **Phase C** | Mock → Real API (5 pages) | ✅ Done |
| **Phase D** | Design tokens (70+ colors) + Vitest (145 tests) | ✅ Done |
| **DB** | PostgreSQL persistence (fire-and-forget) | ✅ Done |
| **LLM** | Async Tier 3 cognition (evaluate_async) | ✅ Done |
| **VAL** | Validation pipeline VAL-01~08 (33 tests) | ✅ Done |
| **S** | Silent Stub resolution (Network / LLM / Memory / Inject) | ✅ Done |
| **M** | Mock → Real pages (GlobalMetrics / Opinions / Thread) | ✅ Done |
| **T** | 41 failing tests fixed + 4 pages, 91 tests added | ✅ Done |
| **F** | Campaign Setup + Project CRUD + EgoGraph Filter | ✅ Done |
| **N** | Run-All + GraphRAG + DB restore + Platform + Lint 10.0 | ✅ Done |
| **H** | 09_HARNESS F18-F28 fully implemented (+43 tests) | ✅ Done |
| **G** | SPEC consistency (method rename + Sidebar + AgentInspector + AnalyticsPage) | ✅ Done |

> **Total tests: 1,658+ GREEN** (Backend 1,002 + Frontend 656)
> - Backend: `uv run pytest tests/` → 1,002 passed, 2 skipped
> - Frontend: `npx vitest run` → 656 passed (40 files)
> - Contract discipline: 29 backend meta tests + 8 frontend structural invariants
> - ESLint: 0 errors, 0 warnings
> - TypeScript (tsc -b): see "Health Stack" notes below
> - Docker: 5 services (4 healthy, ollama occasionally unhealthy)
> - API: 55+ endpoints, 20 pages, 21 routes
> - 3D Graph: react-force-graph-3d (three.js WebGL)
> - Sidebar: global layout (except SimulationPage detail / LoginPage)

### Performance benchmark (2026-03-30)

| Measurement | Result | SPEC target |
|-------------|--------|-------------|
| 1,000 agents × 1 step | **287ms avg** | <1,000ms (NF01) |
| Simulation creation (1,000 agents + network) | 1,362ms | — |
| Docker E2E (5 services healthy) | ✅ | — |

---

## Hard Rules

- **⛔ Never implement without a SPEC** — if `docs/spec/` has no SPEC, write the SPEC first. Never generate code without a SPEC.
- **⛔ SPEC change requires test update** — whenever a Backend/Frontend SPEC changes, the relevant tests must be created or updated.
- **⛔ SPECs are private assets — never commit to public** — `docs/spec/`, `docs/init/`,
  `docs/BUSINESS_REPORT.md`, `docs/MARKETING_STRATEGY.md`, and `docs/OASIS_vs_Prophet.md`
  are the project's IP/moat and are listed in `.gitignore`. Keep these files local and
  never push them to GitHub. When writing public documents like README.md, never quote
  or link to SPEC documents or their contents — anyone with the SPEC alone can
  reproduce Prophet.
- **⛔ No pip** — `uv` only
- **SLM fallback required** — every Tier 3 (Elite LLM) feature must have a Tier 1 (Mass SLM) fallback
- **Harness first** — write harness fixtures/mocks before the implementation
- **PostgreSQL is the source of truth** — in-memory state is just a cache
- **SPEC traceability** — every module docstring must carry a SPEC reference

## Health Stack

- typecheck: cd frontend && npx tsc -b
- lint: cd frontend && npx eslint .
- test-fe: cd frontend && npx vitest run
- test-be: cd backend && uv run pytest tests/ -q
- deadcode: (not installed)
- shell: (not installed)

> **⛔ typecheck warning — do not use `tsc --noEmit`**. The root `tsconfig.json` is
> `"files": []` + references-only, so running without `-b` compiles an empty project
> and **falsely returns 0 errors** (a silent no-op). Always run `tsc -b` so both
> project references (`tsconfig.app.json` and `tsconfig.node.json`) are checked.
> (Discovered 2026-04-10: this mistake let 130 type errors accumulate silently.)

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
