# Changelog

All notable changes to Prophet will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0.0] - 2026-04-09

### Added
- 3D graph visualization via react-force-graph-3d (WebGL/three.js), replacing
  2D Cytoscape canvas entirely with orbit/zoom/pan controls and community-colored
  nodes and edges
- TanStack Query migration across all pages — centralized query/mutation layer
  with request deduplication, cross-route caching, and background revalidation
- Central glossary system with HelpTooltip component for technical term definitions
- SimulationListPage for browsing all simulations at `/simulation`
- Parallel Monte Carlo execution via asyncio.Semaphore with real per-community
  adoption tracking
- Personality drift system — agents evolve personality based on actions taken,
  with cumulative drift tracking
- Campaign controversy parameter wired through agent tick pipeline
- Real intra/inter-community edge counting for cascade detection (was hardcoded)
- Historical simulation graceful degradation — API returns empty data instead
  of 404 for sims that lost in-memory state after server restart
- Simulation export now falls back to DB for historical simulations
- FK safety check in run_scenario — prevents ghost simulations when DB
  persistence fails
- Startup migration marks orphaned running/paused sims as failed on restart
- Git branch strategy documentation and contributor-friendly improvements
  (fork workflow, issue templates, PR template)
- E2E tests for campaign setup, help tooltips, and TanStack cache behavior
- 3 new E2E test files (campaign-setup, help-tooltip, tanstack-cache)

### Changed
- GraphPanel rewritten from Cytoscape.js 2D to react-force-graph-3d
  (instanced sphere renderer, auto-scaled resolution, physics settle)
- CampaignSetupPage split from 617 lines to 111 lines + 6 focused sub-components
  + useCampaignForm hook
- API error handling tightened — broad exception catches replaced with specific
  ValueError/HTTPException-404 filters so real 500s surface instead of returning
  silent empty data
- Monte Carlo runner cleans up orchestrator state after each run to prevent
  memory accumulation
- Community metrics computation reduced from O(n×c) to O(n) via pre-bucketing
- Community link counting offloaded to thread pool to avoid blocking event loop
- LLM fallback stub tracking via is_fallback_stub flag on LLMResponse

### Fixed
- Silent error masking in 7 API endpoints — non-404 HTTPExceptions were caught
  and swallowed, returning empty data instead of surfacing server errors
- Monte Carlo memory leak — SimulationOrchestrator state not cleaned up after
  completing each run
- Ghost simulation bug — orchestrator.start() called before DB persistence
  confirmed, creating invisible in-memory-only simulations
- Replay endpoint no longer returns fake replay_id on failure (now properly 500s)
- Monte Carlo return type annotation corrected (was RunSummary, actually tuple)

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
