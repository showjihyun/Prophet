# Prophet (MCASP) — Master SPEC Index

> Version: 0.1.3.0
> Updated: 2026-04-13

---

## SPEC Files on Disk

The following files exist in `docs/spec/` on disk. Core engine/API/UI SPECs
(00–15 + 16 UI files) were removed from version control for IP protection and
are listed in `.gitignore`. Code docstrings still carry SPEC traceability
references (`SPEC: docs/spec/NN_*.md#section`) so that intent is preserved
even without the source document.

### Index / Meta

| File | Scope | Status |
|------|-------|--------|
| `MASTER_SPEC.md` | This index | CURRENT |
| `SPEC_CHECKLIST.md` | Full compliance checklist (test counts, per-module status) | CURRENT |

### Product / Feature SPECs (series 16+)

| # | File | Scope | Status |
|---|------|-------|--------|
| 16 | `16_COMMUNITY_MGMT_SPEC.md` | Community CRUD, templates, reassignment, merge/split | CURRENT |
| 17 | `17_PERFORMANCE_SPEC.md` | Backend performance: O(1) lookup, async gather, bulk DB, memory caps | CURRENT |
| 18 | `18_FRONTEND_PERFORMANCE_SPEC.md` | Frontend perf, 3D Graph (§5), AgentDetail (§6), SimulationList + auto-provision (§7) | CURRENT |
| 19 | `19_SIMULATION_INTEGRITY_SPEC.md` | Simulation fidelity audit plan (6 Phase: Integrity → Opinion → Diffusion → Cognition → Network → WS) | CURRENT |
| 20 | `20_CLEAN_ARCHITECTURE_SPEC.md` | Clean Architecture (Repository/Service/Controller split, FE type reorg) | CURRENT |
| 21 | `21_SIMULATION_QUALITY_SPEC.md` | Simulation Quality consolidated (P1 SQ + P2 EC/BC/CG + P3 RF/HM/MP) | CURRENT |
| 22 | `22_CONVERSATION_THREAD_SPEC.md` | Real agent-generated thread capture + storage + API | CURRENT |
| 23 | `23_EXPERT_LLM_SPEC.md` | Expert engine LLM integration (rule-based → LLM-assisted) | CURRENT |
| 24 | `24_UI_WORKFLOW_SPEC.md` | 6-stage UI workflow components (WorkflowStepper, EmergentEventsPanel, DecidePanel, GraphLegend, ZoomTierBadge, FormProgressBanner) | CURRENT |
| 26 | `26_ANALYTICS_SPEC.md` | Post-Run Analytics page (summary cards, adoption/sentiment charts, community bar, emergent event timeline) — replaces IP-protected `07_FRONTEND_SPEC.md#simulationsidanalytics` | CURRENT |
| 27 | `27_OPINIONS_SPEC.md` | Three-level Opinions hierarchy (`/opinions`, `/opinions/:cid`, `/opinions/:cid/thread/:tid`) — real stat deltas, API-thread priority, shared sentiment colour utility — replaces IP-protected `ui/UI_13/14/15` | CURRENT |
| 28 | `28_SETTINGS_EXTENSIONS_SPEC.md` | Chinese LLM providers (DeepSeek / Qwen / Moonshot / Zhipu GLM) + `DEFAULT_MAX_STEPS` reconciliation (365 → 50) + Settings UI "Default Max Steps" field | CURRENT |
| 29 | `29_MONTE_CARLO_SPEC.md` | Real Monte Carlo sweep — `MonteCarloResult` / `RunSummary` schema, `POST /simulations/{id}/monte-carlo` endpoint, `useRunMonteCarlo` hook, DecidePanel MC tab with viral_prob + reach percentiles | CURRENT |

> **Consolidation note (2026-04-10):** Three earlier files —
> `19_SIMULATION_QUALITY_SPEC.md` (P1), `20_SIMULATION_QUALITY_P2_SPEC.md` (P2),
> and `21_SIMULATION_QUALITY_P3_SPEC.md` (P3) — were merged into
> `21_SIMULATION_QUALITY_SPEC.md`. This resolved the 19_/20_ number collisions
> that had arisen from parallel initiatives. All ID prefixes (`SQ-`, `EC-`,
> `BC-`, `CG-`, `RF-`, `HM-`, `MP-`) are preserved; code docstring references
> were migrated in the same commit. `19_SIMULATION_INTEGRITY_SPEC.md` and
> `20_CLEAN_ARCHITECTURE_SPEC.md` retain their original numbers (the 20+ engine
> refs and 10+ BE/FE refs respectively were not touched).

---

## Archived / IP-Protected SPECs (not on disk)

The following SPECs were authored during Phases 0-7 and cover the core engine,
API, DB, and UI contracts. They are excluded from version control (`.gitignore`)
for IP protection and exist only in the author's local environment.

| # | Original File | Scope |
|---|--------------|-------|
| 00 | `00_ARCHITECTURE.md` | System architecture — FastAPI + React 18 + PostgreSQL + Valkey |
| 01 | `01_AGENT_SPEC.md` | 6-Layer Agent Engine (Perception → Influence) |
| 02 | `02_NETWORK_SPEC.md` | Hybrid WS+BA network generator + community graph |
| 03 | `03_DIFFUSION_SPEC.md` | Exposure / Propagation / Sentiment / Cascade models |
| 04 | `04_SIMULATION_SPEC.md` | SimulationOrchestrator lifecycle + 3-Phase step |
| 05 | `05_LLM_SPEC.md` | 3-Tier LLM adapter (SLM / Heuristic / Elite) |
| 06 | `06_API_SPEC.md` | REST/WebSocket API — 55+ endpoints |
| 07 | `07_FRONTEND_SPEC.md` | UI component specs, page layouts |
| 08 | `08_DB_SPEC.md` | PostgreSQL schema + Alembic migrations |
| 09 | `09_HARNESS_SPEC.md` | Test harness F18-F30 |
| 10 | `10_VALIDATION_SPEC.md` | Validation pipeline VAL-01~08 |
| 15 | `15_DEV_WORKFLOW_SPEC.md` | Dev model selection (Opus/Sonnet strategy) |
| UI | `docs/spec/ui/*` (16 files) | Per-page UI SPEC (Simulation, Agent, Communities, etc.) |

---

## Implementation Status by Module

| Module | SPEC Ref | Status | Notes |
|--------|----------|--------|-------|
| **Agent Engine (6-Layer)** | `01_AGENT_SPEC.md` | Fully implemented | PersonalityDrift wired; all 6 layers active |
| **Network Generator** | `02_NETWORK_SPEC.md` | Fully implemented | WS + BA + bridge topology |
| **Diffusion Engine** | `03_DIFFUSION_SPEC.md` | Fully implemented | Echo chamber uses real network topology |
| **Simulation Orchestrator** | `04_SIMULATION_SPEC.md` | Fully implemented | Monte Carlo runs in parallel (asyncio.gather) |
| **LLM Gateway** | `05_LLM_SPEC.md` | Working (3-tier) | Tier routing hardened (see `fix: LLM tier routing`) |
| **API Layer** | `06_API_SPEC.md` | Fully implemented | 55+ endpoints; historical sim graceful degradation |
| **Frontend** | `07_FRONTEND_SPEC.md` + `18_FRONTEND_PERFORMANCE_SPEC.md` | Fully implemented | 20 pages, 21 routes, TanStack Query, 3D graph (react-force-graph-3d) |
| **DB / Persistence** | `08_DB_SPEC.md` | Fully implemented | PostgreSQL + Alembic; FK safety guards; fire-and-forget writes |
| **Community Management** | `16_COMMUNITY_MGMT_SPEC.md` | Fully implemented | CRUD, templates, reassignment, merge/split |
| **Simulation Integrity** | `19_SIMULATION_INTEGRITY_SPEC.md` | Implemented (multi-phase) | Friedkin opinion model, cognition coupling, persistence safety |
| **Clean Architecture** | `20_CLEAN_ARCHITECTURE_SPEC.md` | Implemented | `app/repositories/`, `app/services/`, FE `types/api.ts` |
| **Simulation Quality (P1+P2+P3)** | `21_SIMULATION_QUALITY_SPEC.md` | P1/P2 implemented; P3 RF/HM in progress, MP implemented | Consolidated SPEC covering SQ/EC/BC/CG/RF/HM/MP |
| **Conversation Threads** | `22_CONVERSATION_THREAD_SPEC.md` | Implemented | Thread capture + storage + `/communities/{id}/threads` |
| **Expert LLM** | `23_EXPERT_LLM_SPEC.md` | Implemented | LLM-assisted expert reasoning with rule-based fallback |

---

## Recent Additions (18_FRONTEND_PERFORMANCE_SPEC.md)

The following contracts were added to `18_FRONTEND_PERFORMANCE_SPEC.md` and are
the authoritative source for these features:

| Section | Topic |
|---------|-------|
| §5 | **Graph 3D Rendering** — react-force-graph-3d, OrbitControls, InstancedMesh perf rules (G3D-01~09), acceptance criteria (G3D-AC-01~07) |
| §6 | **AgentDetailPage Real-Data-Only** — no MOCK fallback contract (AD-01~07), loading/not-found gates |
| §7.1 | **GraphPanel Lazy Loading** — React.lazy + Suspense for three.js chunk |
| §7.2 | **Scenario Auto-Provisioning** — `handleScenarioChange` → `runScenario` → instant Play |
| §7.3 | **persist_creation FK Safety** — explicit flush ordering (PC-01~03) |

---

## Test Summary

> Updated 2026-04-13 after Chinese LLM adapter integration + default
> max-steps reconciliation (SPEC 28).

| Layer | Count | Command |
|-------|-------|---------|
| Backend (pytest) | **1,032 passing**, 2 skipped | `cd backend && uv run pytest tests/ -q` |
| Frontend (vitest) | **656 passing** (40 files) | `cd frontend && npx vitest run` |
| TypeScript | 0 errors | `cd frontend && npx tsc -b` |
| ESLint | 0 errors, 0 warnings | `cd frontend && npx eslint .` |

> **⛔ `tsc --noEmit` warning**: the root `tsconfig.json` is references-only
> (`"files": []`), so running without `-b` silently no-ops and returns 0
> errors even if the project references have errors. Always use `tsc -b`.

Backend breakdown includes:
- 29 `test_25_simulation_service.py` tests (TestContractDiscipline + TestCompositionRoot + TestEnginePurity + behavioral)
- 3 engine purity invariants (no string-hash, no module-level sqlalchemy, no module-level config import)

Frontend breakdown includes:
- 8 `ArchitectureInvariants.test.ts` static-scan structural invariants
- 47 tests across 6 UI workflow components (WorkflowStepper, EmergentEventsPanel, DecidePanel, GraphLegend/ZoomTierBadge, FormProgressBanner)
