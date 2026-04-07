# Changelog

All notable changes to Prophet will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Real-time propagation animation with zoom-based level-of-detail (close-up,
  mid, overview tiers)
- Floating particle effects for high-probability propagation events
- Per-step propagation pair data for animation
- Animation toggle in control panel
- Sliding-window memory cap (100 most recent steps) to prevent unbounded growth
- `setStepsBulk` action for O(1) bulk history loading
- In-flight guard on auto-step interval to prevent request pileup at high speed
- WebSocket reconnect counter to force effect re-run on manual reconnect
- `SIM_STATUS` constants and helper sets for typed status comparisons
- Empty-state UI for influencer page when no simulation is active
- Recovery from `failed`/`completed` state via Play button (auto stop + start)

### Changed
- Granular Zustand selectors across 6 components — `latestStep` instead of
  full `steps` array — eliminates cascading re-renders on every step
- Pre-sorted node ID cache in `GraphPanel` — O(1) slice instead of O(n log n)
  sort per step
- Debounced LOD zoom handler (100ms) — eliminates per-node iteration on every
  wheel event
- `SimulationPage` lazy-loaded — keeps Cytoscape (~400KB) out of initial bundle
- Extracted all hardcoded simulation status literals to `SIM_STATUS` constants
- Backend `ExposureModel` and `PropagationModel` now accept pre-built
  `agent_to_node` map for O(1) node lookup
- `CommunityOrchestrator` processes Tier 3 agents concurrently via
  `asyncio.gather` (5–10x faster LLM processing)
- Replaced `copy.deepcopy(graph)` with `graph.copy()` in `NetworkEvolver`
  (50–200ms savings per step at 10K agents)
- Numpy-based cosine similarity in agent memory and LLM gateway (~100x faster)
- Reused `ollama.AsyncClient` across calls instead of constructing per request
- Backend community-orchestrator now caches expensive read-only network derivations
  per `(simulation_id, current_step)`

### Fixed
- `PropagationEvent.action_type` AttributeError in Monte Carlo and replay tests
- Pause button visibility during Run All execution
- TopInfluencers page no longer shows mock data when no simulation is active

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
