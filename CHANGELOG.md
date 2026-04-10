# Changelog

All notable changes to Prophet will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1.0] - 2026-04-10

### Added
- Simulation quality Phase 1: Exposure Fatigue model (exponential decay on repeated
  ad exposure), real edge-weight perception from network topology, dynamic expert
  opinion scoring (controversy × skepticism × channel), prompt injection defense
  (sanitize + XML boundary isolation)
- Simulation quality Phase 2: Emotional Contagion (neighbor excitement/skepticism
  propagate through edges, alpha=0.15), Bounded Confidence opinion dynamics (Deffuant
  model, epsilon=0.3, mu=0.5 prevents unrealistic consensus), Content Generation
  prompt for Tier 3 agents to write personalized social posts
- Simulation quality Phase 3: Reflection Engine (Simulacra-style periodic belief
  revision from accumulated memories), Homophily edge weighting (personality
  similarity influences network trust via Manhattan distance)
- Inject event: target_communities filtering, bad_review event type support,
  frontend cache invalidation on success, 14 InjectEventModal tests
- EngineControlPanel frontend tests

### Changed
- PropagationEvent unified: single canonical type with action_type field, removing
  getattr duck-typing hacks from BridgePropagator and StepRunner
- types.py converted to pure re-export module (no duplicate class definitions)
- ReflectionEngine wired into both sync tick() and async_tick() execution paths
- AgentState gains last_reflection_step field for tracking reflection intervals

### Fixed
- Dead sync code removed: run_until_complete hack in tick.py (never executed in
  production FastAPI context)
- Fire-and-forget async tasks now log errors via _fire_and_forget helper (14 sites)
- Persistence: bare except → specific types + logging for agent serialization
- run_all: step_callback exceptions now isolated and logged (no more stuck RUNNING state)
- Network generator: validation failures now logged (was silent)
- _config_to_dict and _community_metric_to_dict: degraded fallbacks now log errors

## [0.1.0.0] - 2026-04-09

### Added
- Core engine: real echo chamber detection using network topology (intra/inter-community
  edge ratio) instead of the hardcoded 10:1 ratio that fired for every community
- Core engine: PersonalityDrift wired into agent tick pipeline — agents now evolve
  personality based on actions taken, with cumulative drift tracking per step
- Core engine: campaign controversy parameter connected through agent tick so
  MessageStrength correctly reflects the configured controversy value
- Monte Carlo: parallel scenario execution via `asyncio.Semaphore` (max concurrency 3)
  with real per-community adoption stats replacing previous sequential blocking runs
- API: historical simulation graceful degradation — agents, network, stop, compare,
  and export endpoints return empty/fallback data instead of 404 when in-memory state
  is lost after server restart; export falls back to DB records
- Frontend: ControlPanel split into 8 focused files (hooks + subcomponents) reducing
  the monolith to focused, testable units
- Frontend: EngineControlPanel centered modal layout
- Frontend: 3D graph visualization via react-force-graph-3d (WebGL/three.js) with
  orbit/zoom/pan controls and community-colored nodes and edges
- Frontend: TanStack Query migration across all pages — centralized query/mutation
  layer with request deduplication, cross-route caching, and background revalidation
- Frontend: central glossary system with HelpTooltip component for technical term
  definitions
- DB safety: background persistence tasks now capture their own DB session so they
  cannot use a closed request-scoped session (use-after-free fix)
- DB safety: FK commit guard in `run_scenario` prevents ghost simulations when DB
  persistence fails before `orchestrator.start()` is called
- DB safety: startup ORM migration marks orphaned running/paused simulations as
  failed on server restart
- DB safety: `load_steps` query now has a LIMIT guard to prevent unbounded reads
- SimulationListPage for browsing all simulations at `/simulation`
- E2E tests for campaign setup, help tooltips, and TanStack cache behavior
- Git branch strategy documentation and contributor-friendly improvements
  (fork workflow, issue templates, PR template)

### Changed
- GraphPanel rewritten from Cytoscape.js 2D to react-force-graph-3d
  (instanced sphere renderer, auto-scaled resolution, physics settle)
- CampaignSetupPage split from 617 lines to 111 lines + 6 focused sub-components
  + useCampaignForm hook
- API error handling tightened — broad exception catches replaced with specific
  ValueError/HTTPException-404 filters so real 500s surface instead of being
  silently swallowed
- Monte Carlo runner cleans up orchestrator state after each run to prevent
  memory accumulation
- Community metrics computation reduced from O(n×c) to O(n) via pre-bucketing
- Community link counting offloaded to thread pool to avoid blocking event loop
- LLM fallback stub tracking via `is_fallback_stub` flag on `LLMResponse`

### Fixed
- Echo chamber detector false positives — was hardcoded 10:1 intra/inter ratio
  applied uniformly to all communities regardless of actual graph topology
- PersonalityDrift dead code — drift was computed but `agent.personality` was never
  updated; now committed back on every tick
- Controversy hardcoded to 0.0 — campaign `controversy` field never reached agents;
  now propagated through the full tick pipeline to MessageStrength
- Monte Carlo sequential execution despite `parallel=True` flag — semaphore-based
  concurrency now honours the flag
- `create_task` background jobs using a closed request DB session (use-after-free)
  — tasks now open their own session
- `run_scenario` returning status `"running"` when DB persist failed, leaving an
  invisible in-memory-only simulation with no DB record
- `stop_simulation` returning HTTP 200 for nonexistent simulation IDs — now returns
  404 with a descriptive message
- Silent error masking in 7 API endpoints — non-404 HTTPExceptions were caught and
  swallowed, returning empty data instead of surfacing the real server error
- Monte Carlo memory leak — SimulationOrchestrator state not cleaned up after each
  completed run
- Replay endpoint returning a fake `replay_id` on failure — now properly raises 500

## [0.1.0] — Initial Public Release

### Added
- 6-layer agent engine: perception, memory, emotion, cognition, decision, influence
- Hybrid network generator (Watts-Strogatz + Barabási-Albert + bridge edges)
- Diffusion engine with RecSys-inspired exposure model
- Auto-detection of 5 emergent behaviors: viral cascade, polarization, echo
  chamber, collapse, slow adoption
- 3-tier LLM inference (Mass SLM / Heuristic / Elite LLM)
- LLM Gateway with batching, semantic cache, and provider fallback
- Real-time WebSocket visualization with Cytoscape.js
- Pause / Resume / Step / Reset / Run-All controls
- Monte Carlo simulation
- Community management (CRUD + agent reassignment)
- Project / scenario management
- Export to JSON / CSV
- Docker Compose deployment with PostgreSQL 16, pgvector, Valkey, Ollama
- 1,234+ tests across backend and frontend
