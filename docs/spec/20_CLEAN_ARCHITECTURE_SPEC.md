# 20_CLEAN_ARCHITECTURE_SPEC.md — Clean Architecture

> Version: 0.3.0
> Created: 2026-04-10
> Updated: 2026-04-11
> Status: APPROVED

**v0.3.0 change log (Round 3-6 hardening):**
- §2.4 persistence.py moved from `engine/simulation/` to `repositories/simulation_persistence.py` (R6)
- §2.5 memory.py SQL extracted to `repositories/memory_repo.py` helpers (R6)
- §3.4 `SimulationRepository` Protocol expanded: `session` kwarg + full `persist_*` coverage (R1)
- §4.3 `SimulationService` Protocol-typed — no concrete `SqlSimulationRepository` dependency (R2)
- §4.4 `NotificationPort` + `CreateSimulationInput` Ports in `services/ports.py` (R2)
- §4.5 `StopOutcome` enum + `SimulationNotFoundError` domain exception (R2)
- §4.6 `orchestrator.reset()`, `orchestrator.list_states()` — domain-owned state transitions (R3/R4)
- §4.7 `SimulationService.run_all()` — step_callback closure owned by service (R3)
- §5.4 `persist_creation` strict with 3x retry + `failed_queue` + re-raise (R4)
- §5.5 `BigInteger random_seed` Alembic migration `d1_bigint_seed` (R4)
- §5.6 Engine purity: `sha256` deterministic hashing + `uuid5` name-based UUIDs (R5)
- §7 CA-13, CA-14, CA-15 acceptance criteria added (composition root enforcement, engine purity, frontend invariants)
- §9 Frontend structural invariants — 8 static scan tests in `ArchitectureInvariants.test.ts` (R6)
- §10 Composition root formalized: `api/deps.py` is the sole wiring layer (R5)

---

## 1. Overview

Apply Clean Architecture (Robert C. Martin) dependency rules to the Prophet codebase.
Core principle: **Inner layers never import outer layers.**

### 1.1 Motivation

| Problem | Current State | Goal |
|------|----------|------|
| `api/simulations.py` bloat | 1,378 lines (HTTP + business + DB + WS) | ~200 lines (thin controller) |
| Domain↔Infrastructure coupling | `engine/` imports `app.config.settings` in 7 places, SQLAlchemy in 14 places | 0 occurrences |
| Direct ORM manipulation in API | 20+ session.execute/add/commit in `projects.py` | Only through Repository |
| FE component→API direct calls | `apiClient.` used directly in 7 component files | Only through hooks/queries |
| Type definition scattered | 25+ inline interfaces in `client.ts` | Separated into `types/api.ts` |

---

## 2. Layer Definition

### 2.1 Backend 4-Layer

```
┌──────────────────────────────────────────────────────┐
│  Layer 4: Infrastructure                              │
│  models/, database.py, ws.py, llm/ adapters           │
│  ┌──────────────────────────────────────────────┐    │
│  │  Layer 3: Interface Adapters                  │    │
│  │  api/ (controllers), repositories/ (impl)     │    │
│  │  ┌──────────────────────────────────────┐    │    │
│  │  │  Layer 2: Application Services       │    │    │
│  │  │  services/                            │    │    │
│  │  │  ┌──────────────────────────────┐    │    │    │
│  │  │  │  Layer 1: Domain              │    │    │    │
│  │  │  │  engine/ (pure business)      │    │    │    │
│  │  │  └──────────────────────────────┘    │    │    │
│  │  └──────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

### 2.2 Import Rules (Backend)

| Source Layer | May Import | NEVER Imports |
|-------------|-----------|---------------|
| **L1 Domain** (`engine/`) | stdlib, dataclasses, own subpackages | `app.config`, `app.models`, `app.api`, `app.services`, `sqlalchemy`, `fastapi` |
| **L2 Application** (`services/`) | `engine/` types, `repositories/` Protocols | `app.models`, `sqlalchemy`, `fastapi`, `app.api` |
| **L3 Interface** (`api/`, `repositories/`) | `services/`, `engine/` types, `schemas` | `app.models` (api only), direct session manipulation (api only) |
| **L4 Infrastructure** (`models/`, `database.py`) | `sqlalchemy` | `engine/`, `services/` |

### 2.3 Domain Config Injection Rule (CA-DI-01)

**Current violation**: `from app.config import settings` directly imported in 7 places within engine/.

```python
# ❌ Violation — domain depends on infrastructure configuration
from app.config import settings as _settings
MAX_DRIFT = _settings.agent_max_personality_drift

# ✅ Fix — constructor injection or constant default value
class PersonalityDrift:
    def __init__(self, max_drift: float = 0.3): ...
```

**Violation list (7 locations)**:

| File | Settings Used | Fix Method |
|------|-------------|----------|
| `engine/agent/drift.py:6` | `agent_max_personality_drift` | `__init__(max_drift=0.3)` |
| `engine/agent/memory.py:12` | `memory_fallback_*`, `agent_max_memories` | `__init__(**kwargs)` default values |
| `engine/simulation/orchestrator.py:66` | `sim_max_concurrent`, `sim_max_simulations`, `sim_ttl_seconds` | `__init__(max_concurrent=5, ...)` |
| `engine/simulation/step_runner.py:242` | implicit settings via imports | constructor param |
| `engine/simulation/community_orchestrator.py:52` | `community_batch_size` | class-level constant or `__init__` |
| `engine/simulation/monte_carlo.py:105` | settings | constructor param |
| `engine/network/evolution.py:77` | `max_network_edges` | `__init__` or config param |

### 2.4 persistence.py Location Change (CA-MOVE-01)

**Current**: `engine/simulation/persistence.py` — 14 SQLAlchemy ORM imports inside the domain.

**Goal**: Move `persistence.py` under `repositories/`. The domain (engine/) only references the Repository Protocol.

```
# migration path
engine/simulation/persistence.py → repositories/simulation_persistence.py
```

The existing `SimulationPersistence` class becomes the implementation detail of `SqlSimulationRepository`.

---

## 3. Backend — Repository Layer

### 3.1 SimulationRepository Protocol

```python
# backend/app/repositories/protocols.py

from typing import Any, Protocol
from uuid import UUID

class SimulationRepository(Protocol):
    """DB access abstraction — contract between domain and infrastructure."""

    # Writes
    async def save_creation(self, sim_id: UUID, config: Any, agents: list, edges: list, *, session: Any) -> None: ...
    async def save_step(self, sim_id: UUID, result: Any, agents: list | None = None, *, session: Any) -> None: ...
    async def save_status(self, sim_id: UUID, status: str, step: int | None = None, *, session: Any) -> None: ...

    # Reads
    async def find_by_id(self, sim_id: UUID, *, session: Any) -> dict | None: ...
    async def list_all(self, *, status: str | None, limit: int, offset: int, session: Any) -> list[dict]: ...
    async def count(self, status: str | None = None, *, session: Any) -> int: ...
    async def load_steps(self, sim_id: UUID, *, session: Any) -> list[dict]: ...
    async def restore_state(self, sim_id: UUID, *, session: Any) -> dict | None: ...
    async def row_exists(self, sim_id: UUID, *, session: Any) -> bool: ...

    # Supplementary
    async def persist_event(self, sim_id: UUID, event_type: str, step: int, data: dict, *, session: Any) -> None: ...
    async def persist_llm_calls(self, sim_id: UUID, call_logs: list, *, session: Any) -> None: ...
    async def persist_thread_messages(self, messages: list, *, session: Any) -> None: ...

    @property
    def failed_queue(self) -> list[dict]: ...
```

### 3.2 ProjectRepository Protocol

```python
class ProjectRepository(Protocol):
    async def create(self, name: str, *, session: Any) -> dict: ...
    async def find_by_id(self, project_id: UUID, *, session: Any) -> dict | None: ...
    async def list_all(self, *, session: Any) -> list[dict]: ...
    async def delete(self, project_id: UUID, *, session: Any) -> None: ...
    async def create_scenario(self, project_id: UUID, data: dict, *, session: Any) -> dict: ...
    async def list_scenarios(self, project_id: UUID, *, session: Any) -> list[dict]: ...
    async def delete_scenario(self, project_id: UUID, scenario_id: UUID, *, session: Any) -> None: ...
```

### 3.3 CommunityRepository Protocol

```python
class CommunityRepository(Protocol):
    async def list_for_simulation(self, sim_id: UUID, *, session: Any) -> list[dict]: ...
    async def get_detail(self, sim_id: UUID, community_id: str, *, session: Any) -> dict | None: ...
    async def list_threads(self, sim_id: UUID, community_id: str, *, session: Any) -> list[dict]: ...
    async def get_thread(self, sim_id: UUID, thread_id: str, *, session: Any) -> dict | None: ...
```

---

## 4. Backend — Application Service Layer

### 4.1 SimulationService

| Method | Responsibility | Current Location |
|--------|------|----------|
| `create()` | config build + orch.create + persist + WS | `api/simulations.py` L164-231 |
| `start()` | state transition + persist + WS | `api/simulations.py` L349-369 |
| `step()` | step execution + persist + LLM logging + WS + agent broadcast | `api/simulations.py` L372-558 |
| `run_all()` | full execution loop + persist each step + WS | `api/simulations.py` L561-620 |
| `pause()` / `resume()` / `stop()` | state transition + persist + WS | 10-20 lines each |
| `inject_event()` | event injection | `api/simulations.py` L794-832 |
| `replay()` | replay branch | `api/simulations.py` L835-870 |
| `engine_control()` | SLM/LLM ratio adjustment | `api/simulations.py` L961-997 |

### 4.2 ProjectService

| Method | Current Location |
|--------|----------|
| `create_project()` | `api/projects.py` — session.add + commit |
| `list_projects()` | `api/projects.py` — session.execute(select) |
| `get_project()` | `api/projects.py` — session.execute(select) |
| `delete_project()` | `api/projects.py` — session.execute(delete) |
| `create_scenario()` | `api/projects.py` — session.add + commit |
| `run_scenario()` | `api/projects.py` — orch.create + start + session |
| `delete_scenario()` | `api/projects.py` — session.execute(delete) |

### 4.3 Thin Controller Pattern

```python
# Goal: all API handlers follow this pattern
@router.post("/{simulation_id}/step", response_model=StepResultResponse)
async def step_simulation(
    simulation_id: str,
    service: SimulationService = Depends(get_simulation_service),
    session: AsyncSession = Depends(get_session),
) -> StepResultResponse:
    """SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstep"""
    return await service.step(simulation_id, session=session)
```

---

## 5. Backend — DB / Infrastructure Rules

### 5.1 models/ Isolation Rules

- `models/*.py` contains only SQLAlchemy ORM definitions
- Direct import of `models/` files from `engine/`, `services/` is prohibited
- Only `repositories/` implementations and `database.py` are allowed to import `models/`

### 5.2 Session Management Rules

- `AsyncSession` is created in `api/deps.py` and injected as request-scoped
- Services accept session as a parameter but do not directly call commit/rollback
- Only Repository implementations perform session.add/execute/commit

### 5.3 Migration (Alembic) Rules

- Schema changes must go through Alembic migration
- Run `uv run alembic revision --autogenerate` when modifying models/
- Direct DDL execution is prohibited

---

## 6. Frontend — Layer Structure

### 6.1 Layer Definition

```
frontend/src/
├── types/           (L1: domain types — no dependencies)
│   ├── simulation.ts   (SimulationRun, StepResult, PropagationPair, etc.)
│   └── api.ts          (API request/response interfaces)
│
├── api/             (L2: network layer — depends on types only)
│   ├── client.ts       (pure HTTP fetch wrapper)
│   └── queries.ts      (TanStack Query hooks)
│
├── store/           (L3: client state — depends on types only)
│   └── simulationStore.ts
│
├── hooks/           (L4: business logic — depends on api, store, types)
│   ├── useSimulationSocket.ts
│   └── (control hooks)
│
├── components/      (L5: UI — depends on hooks, store, types only)
│   └── (NO direct apiClient import)
│
└── pages/           (L6: route composition — composes components, hooks)
```

### 6.2 Import Rules (Frontend)

| Source | May Import | NEVER Imports |
|--------|-----------|---------------|
| `types/` | nothing | — |
| `api/client.ts` | `types/` | components, pages, store |
| `api/queries.ts` | `api/client.ts`, `types/` | components, pages |
| `store/` | `types/` | api, components, pages |
| `hooks/` | `api/queries.ts`, `store/`, `types/` | components, pages |
| `components/` | `hooks/`, `store/` (selectors), `types/` | direct `api/client.ts` import prohibited |
| `pages/` | `components/`, `hooks/`, `store/` | direct `api/client.ts` import prohibited |

### 6.3 Current Violation List (7 items)

| File | Violation | Fix |
|------|------|------|
| `components/graph/EgoGraph.tsx` | direct `apiClient.` usage | convert to TanStack Query hook |
| `components/control/hooks/useAutoStepLoop.ts` | `apiClient.` import | queries.ts hook already exists, replace |
| `components/control/hooks/usePlaybackControls.ts` | `apiClient.` import | use queries.ts hook |
| `components/control/hooks/useProjectScenarioSync.ts` | `apiClient.` import | use queries.ts hook |
| `components/control/hooks/usePrevSimulations.ts` | `apiClient.` import | use queries.ts hook |
| `components/agent/AgentInspector.tsx` | direct `apiClient.` usage | convert to hook |
| `components/shared/SimulationReportModal.tsx` | direct `apiClient.` usage | convert to hook |

---

## 7. Acceptance Criteria

### Backend

| ID | Criterion | Verification Method |
|----|------|----------|
| CA-01 | 0 `sqlalchemy`, `fastapi`, `app.models` imports in `engine/` | `grep -r "from sqlalchemy\|from fastapi\|from app.models" engine/` |
| CA-02 | 0 `from app.config import settings` in `engine/` | `grep -r "from app.config" engine/` |
| CA-03 | 0 `sqlalchemy`, `fastapi`, `app.models` imports in `services/` | grep verification |
| CA-04 | `api/*.py` handlers follow Service call pattern (inline business logic prohibited) | code review |
| CA-05 | 0 direct `session.execute/add/commit` calls in `api/*.py` | grep verification |
| CA-06 | All DB access goes through Repository | `app.models` import only in `repositories/` and `database.py` |

### Frontend

| ID | Criterion | Verification Method |
|----|------|----------|
| CA-07 | 0 direct `apiClient` imports in `components/` | `grep -r "apiClient\." components/` |
| CA-08 | 0 interface definitions in `api/client.ts` (re-export only) | code review |
| CA-09 | `types/api.ts` is single source of truth for all API interfaces | code review |

### Common

| ID | Criterion |
|----|------|
| CA-10 | All existing tests GREEN (BE + FE) |
| CA-11 | `tsc --noEmit` 0 errors |
| CA-12 | `eslint .` 0 errors |

---

## 8. Migration Sequence

```
Phase 1: move persistence.py to repositories/ (resolve CA-01)
    ↓
Phase 2: engine/ config singleton → constructor injection (resolve CA-02)
    ↓
Phase 3: api/simulations.py → SimulationService migration (resolve CA-04, CA-05)
    ↓
Phase 4: api/projects.py → ProjectService + ProjectRepo migration (resolve CA-05)
    ↓
Phase 5: FE components/ → through hooks (resolve CA-07)
    ↓
Phase 6: full verification (CA-10~12)
```

**Run full test suite after each Phase** to prevent regression.

---

## 9. Round 3-6 Additions (v0.3.0)

This section records contracts added since v0.2.0. All items are enforced as CI gates
in `TestContractDiscipline`, `TestCompositionRoot`, `TestEnginePurity` classes
in `tests/test_25_simulation_service.py`.

### 9.1 Domain API Completeness (Round 3-4)

| ID | Method/Item | Location | Purpose |
|----|-----------|------|------|
| DA-01 | `SimulationOrchestrator.reset(sim_id)` | `orchestrator.py:481` | Encapsulate COMPLETED/FAILED → CREATED. Direct `state.status = "created"` modification prohibited |
| DA-02 | `SimulationOrchestrator.list_states(*, status)` | `orchestrator.py:677` | Replace direct exposure of `_simulations` internal dict |
| DA-03 | `StopOutcome` enum | `services/ports.py` | Replace sentinel dict return (`COMPLETED`, `RESET`) |
| DA-04 | `SimulationNotFoundError` | `services/ports.py` | Domain exception instead of "not_found" string |
| DA-05 | `orchestrator.delete_simulation()` on persist failure | `services/simulation_service.py:214` | Automatic ghost state reclamation |

### 9.2 Protocol-First Dependencies (Round 1-2)

| ID | Protocol | Implementation | Consumer |
|----|----------|--------|-------|
| PR-01 | `SimulationRepository` | `SqlSimulationRepository` | `SimulationService` |
| PR-02 | `ProjectRepository` | `SqlProjectRepository` | `api/projects.py` |
| PR-03 | `NotificationPort` | `ConnectionManager` (structural) | `SimulationService` |
| PR-04 | `CreateSimulationInput` | Pydantic `CreateSimulationRequest` | `SimulationService.create()` |

**Rule (PR-DI-01)**: Services do not use concrete classes in type hints. They only accept Protocols.

### 9.3 Persistence Strictness (Round 4)

| ID | Contract | File |
|----|------|------|
| PS-01 | `persist_creation` strict — 3x retry + `failed_queue` logging + re-raise | `repositories/simulation_persistence.py:98-248` |
| PS-02 | All other `persist_*` are best-effort (swallow + log) | specified in docstring |
| PS-03 | `BigInteger random_seed` — Alembic migration `d1_bigint_seed` | `models/simulation.py:27` |
| PS-04 | Ghost state reclamation on persist failure in `SimulationService.create()` | `services/simulation_service.py:200-215` |

### 9.4 Engine Purity (Round 5-6)

| ID | Rule | Enforcement Test |
|----|------|------------|
| EP-01 | `hash(str)` calls prohibited in `engine/**` (non-deterministic) | `test_engine_has_no_string_hash_calls` |
| EP-02 | Module-level `from sqlalchemy` prohibited in `engine/**` (CA-01) | `test_engine_has_no_runtime_sqlalchemy_import` |
| EP-03 | Module-level `from app.config import` prohibited in `engine/**` (CA-02) | `test_engine_has_no_module_level_config_import` |
| EP-04 | Community UUID is `sha256(f"{sim_id}:{cid}")` based (reproducible) | `orchestrator.py:239-253` |
| EP-05 | Campaign UUID is `uuid5(NAMESPACE_OID, ...)` based | `step_runner.py:73-79` |
| EP-06 | NetworkX node_id → int mapping is SHA-1 based (deterministic) | `repositories/simulation_persistence.py:35` |

### 9.5 Composition Root (Round 5)

**CA-CR-01**: `app/api/deps.py` is the **sole** module that instantiates concrete infrastructure types.
Import of the following types is allowed only in deps.py or the file that defines that type:

| Concrete Type | Allowed Location | Enforcement Test |
|--------------|----------|------------|
| `SimulationPersistence` | `repositories/simulation_persistence.py` (definition), `repositories/simulation_repo.py` (wrapper), `api/deps.py` (wiring) | `test_simulation_persistence_only_imported_at_composition_root` |
| `SqlSimulationRepository` | `repositories/__init__.py`, `repositories/simulation_repo.py`, `api/deps.py` | `test_sql_repository_classes_only_imported_at_composition_root` |
| `SqlProjectRepository` | same | same |

All other modules only import Protocols.

### 9.6 Service Run-all Ownership (Round 3)

`SimulationService.run_all(sim_id, *, session)` — migrates the `step_callback` closure
previously inlined in the `api/simulations.py` route handler to the service.
The route only maps `SimulationCapacityError`, `InvalidStateError`, etc. to HTTP status codes.

### 9.7 Test Infrastructure (Round 4)

- `NullPool` usage — resolves connection dying in pool when pytest creates a new event loop per test. `app/database.py:13-24`
- `conftest.py::_clean_simulation_db` autouse fixture — ensures isolation by `TRUNCATE TABLE simulations CASCADE` + `TRUNCATE TABLE projects CASCADE` before each test

---

## 10. Frontend Structural Invariants (v0.3.0)

**Parity with backend harness**: The backend has structural invariant tests such as `TestContractDiscipline`,
but the frontend previously had only functional tests and no structural tests.
`ArchitectureInvariants.test.ts` added in Round 6 enforces the following 8 rules via static scan.

| ID | Rule | Test Number |
|----|------|-----------|
| FE-INV-01 | `components/**` does not runtime-import `apiClient` | #1 |
| FE-INV-02 | `pages/**` does not runtime-import `apiClient` | #2 |
| FE-INV-03 | `store/**` does not import `api/client` or `components/` | #3 |
| FE-INV-04 | `types/**` is a leaf layer (0 runtime dependencies) | #4 |
| FE-INV-05 | `SimulationStatus` literals must not be hardcoded outside `constants.ts` | #5 |
| FE-INV-06 | Community color hex must not be hardcoded outside `constants.ts` | #6 |
| FE-INV-07 | Raw `fetch()` to `/api/v1` only in `api/client.ts` | #7 |
| FE-INV-08 | Component files export only components (react-refresh rule) | #8 |

**Baseline strategy**: Pre-existing violation files are recorded in an explicit allow-list.
New code cannot be added to the allow-list — tests fail immediately. The allow-list is
a ratchet and decreases in follow-up rounds.

---

## 11. Acceptance Criteria (v0.3.0 extension)

| ID | Criterion | Verification |
|----|------|------|
| CA-13 | 0 `SimulationPersistence` or `Sql*Repository` imports outside composition root | `TestCompositionRoot` |
| CA-14 | 0 module-level sqlalchemy / app.config imports in `engine/**` | `TestEnginePurity::test_engine_has_no_runtime_sqlalchemy_import`, `test_engine_has_no_module_level_config_import` |
| CA-15 | Frontend 8 structural invariants GREEN | `ArchitectureInvariants.test.ts` |
