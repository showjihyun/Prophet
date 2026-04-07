# Prophet (MCASP)

**The wind tunnel for marketing campaigns.**

Run your campaign, message, or policy through a virtual society of **10,000 AI
agents** organized into real social communities — and watch it succeed or burn
down before you spend a dollar on the launch.

[![Tests](https://img.shields.io/badge/tests-1234%20passing-brightgreen)]()
[![Backend](https://img.shields.io/badge/backend-861%2F863-brightgreen)]()
[![Frontend](https://img.shields.io/badge/frontend-373%2F373-brightgreen)]()
[![TypeScript](https://img.shields.io/badge/TypeScript-0%20errors-blue)]()
[![Health](https://img.shields.io/badge/health-10.0%2F10-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

---

## What is Prophet?

Prophet (MCASP — Multi-Community Agent Simulation Platform) is an open-source
simulation engine that models how messages spread through social networks of
LLM-powered agents. Marketing teams use it to **pre-test campaigns**. Researchers
use it to study **viral cascades**. Public health teams use it to simulate
**communication strategies**.

### How it works

```
1. Generate     → 10K agents in 5 communities (early adopters, consumers,
                  skeptics, experts, influencers) with realistic structure
                  (clustering, scale-free degree, bridge nodes)

2. Inject       → Your campaign / message / policy

3. Simulate     → Each agent perceives, remembers, evaluates, decides, acts
                  (12 actions: ignore, share, comment, adopt, reject…)

4. Detect       → Auto-detect viral cascades, polarization, echo chambers,
                  collapse, slow adoption

5. Visualize    → Real-time Cytoscape graph with zoom-based animation
                  (close-up / mid / overview tiers)

6. Decide       → Compare scenarios, run Monte Carlo sweeps, export results
```

### Why it's different

- **Cost-controlled.** A naive 10K-agent GPT-4 simulation costs ~$15,000.
  Prophet's 3-tier model (80% local SLM + 10% heuristic + 10% elite LLM)
  brings it to **under $5**.
- **Realistic networks.** Hybrid Watts-Strogatz + Barabási-Albert generator
  produces clustering + power-law influencers + cross-community bridges.
  Random graphs don't.
- **GraphRAG memory.** Each agent has episodic + semantic memory backed by
  pgvector. Most agent simulators have no memory at all.
- **Built-in cascade detection.** 5 emergent behaviors (viral, polarization,
  echo chamber, collapse, slow adoption) detected mathematically — not by
  eyeballing the graph.
- **Real-time visualization.** WebSocket-driven Cytoscape canvas at 30+ FPS
  with zoom-based animation tiers. Watch your campaign succeed or fail
  step-by-step.

---

## Quick Start

### Run with Docker

```bash
git clone https://github.com/your-org/prophet.git
cd prophet

# CPU environment (no GPU)
docker compose up -d

# Pull LLM model (first time only, ~4.7GB)
docker compose exec ollama ollama pull llama3.1:8b

# GPU environment (NVIDIA)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

| Service             | URL                          |
|---------------------|------------------------------|
| Frontend            | http://localhost:5173        |
| Backend API         | http://localhost:8000        |
| API Docs (Swagger)  | http://localhost:8000/docs   |
| Ollama              | http://localhost:11434       |
| PostgreSQL          | localhost:5433               |
| Valkey              | localhost:6379               |

Open `http://localhost:5173`, click **New Simulation**, pick a scenario
template, and click **Run All**. The graph spreads in real time.

### Local development

```bash
# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload
uv run pytest -v          # 861/863 tests passing

# Frontend
cd frontend
npm install
npm run dev
npx vitest run            # 373/373 tests passing
```

---

## Use Cases

### 🛍️ Marketing campaign pre-test

A CPG brand launches a sustainability-focused product. Prophet runs the
message through 5,000 agents (15% skeptics, 60% mainstream, 20% early
adopters, 5% influencers). The simulation reveals the message **polarizes**
the skeptical community at step 18 and adoption stalls at 12%. The brand
re-frames before spending the launch budget.

### 🏥 Public health communication

A health agency tests three vaccine messages against a 10K-agent virtual
population. Strategy B causes echo-chamber formation. Strategy C triggers
a positive viral cascade through influencer nodes. The agency picks Strategy
C and projects 3x adoption.

### 🏢 Internal corporate communications

A Fortune 500 announces a return-to-office mandate. Their comms team runs
the message against a synthetic employee population. Prophet predicts a
38% sentiment collapse in engineering communities. The company restructures
the announcement with carve-outs and cuts opposition by 60%.

### 🔬 Computational social science research

Open-source, reproducible alternative to OASIS. 10x cheaper. Runs on a
laptop. Built-in cascade detection. Designed for citation.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│  Frontend: React 18 + Cytoscape.js (10K-node real-time graph)  │
│  Recharts (timeline + metrics) | Zustand (state) | WebSocket   │
├────────────────────────────────────────────────────────────────┤
│  API: FastAPI (async) + WebSocket (55+ endpoints)              │
├──────────┬──────────┬──────────┬─────────────┬─────────────────┤
│  6-Layer │  Network │  Diffusion│  LLM Gateway│  Cascade        │
│  Agent   │  Hybrid  │  RecSys   │  3-Tier     │  Detector       │
│  Engine  │  WS+BA   │  Exposure │  Adapter    │  Auto-emergent  │
├──────────┴──────────┴──────────┴─────────────┴─────────────────┤
│  PostgreSQL 16 + pgvector  │  Valkey  │  Ollama / Claude / GPT │
└────────────────────────────────────────────────────────────────┘
```

### 6-Layer Agent Engine

```
Perception → Memory (GraphRAG) → Emotion → Cognition → Decision → Influence
```

- **12 action types:** ignore, view, search, like, save, comment, share,
  repost, follow, unfollow, adopt, mute
- **3-Tier inference:** Mass SLM (80%) → Heuristic (10%) → Elite LLM (10%)
- **GraphRAG memory:** episodic + semantic via pgvector
- **Configurable from UI** — no hardcoded models

### Hybrid Network Generator

- **Watts-Strogatz** (community clustering) + **Barabási-Albert** (influencer
  power-law) + **bridge edges** (cross-community)
- **5 community types:** Early Adopters, Consumers, Skeptics, Experts,
  Influencers
- **Dynamic edge evolution** per simulation step
- **Customizable templates** via UI

### Diffusion Engine

- **RecSys-inspired exposure model** (OASIS-inspired feed ranking)
- **5 emergent behavior detections:** Viral Cascade, Polarization, Echo
  Chamber, Collapse, Slow Adoption
- **Monte Carlo simulation** (N-run probability analysis)
- **Export JSON/CSV** for downstream analysis

---

## Performance

| Scenario                                  | Step time | Notes                          |
|-------------------------------------------|-----------|--------------------------------|
| 1,000 agents × 1 step (Tier 1/2 only)     | ~287ms    | Verified benchmark             |
| 1,000 agents × 1 step (with Tier 3 LLM)   | ~500ms    | `asyncio.gather` over LLM batch|
| 10,000 agents × 1 step (projected)        | ~1,500ms  | After Tier A+B perf fixes      |
| 365-step simulation (1K agents)           | ~2 min    | Real-time WebSocket updates    |

See [`docs/spec/17_PERFORMANCE_SPEC.md`](docs/spec/17_PERFORMANCE_SPEC.md) and
[`docs/spec/18_FRONTEND_PERFORMANCE_SPEC.md`](docs/spec/18_FRONTEND_PERFORMANCE_SPEC.md)
for the full performance audit (19 backend + 29 frontend findings).

---

## Tech Stack

| Layer            | Technology                                                  |
|------------------|-------------------------------------------------------------|
| Frontend         | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui         |
| Visualization    | Cytoscape.js, Recharts                                      |
| State / Server   | Zustand, TanStack Query, native WebSocket                   |
| Backend          | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2   |
| LLM              | Ollama (local SLM), Claude API, OpenAI API, Gemini API      |
| Database         | PostgreSQL 16 + pgvector                                    |
| Cache            | Valkey                                                       |
| Package mgmt     | `uv` (Python), `npm` (Node)                                 |
| Testing          | pytest, Vitest, Playwright                                  |

---

## Project Structure

```
Prophet/
├── CLAUDE.md              # Project instructions for AI assistants
├── DESIGN.md              # UI design master (Pencil integration)
├── README.md              # This file
│
├── docs/
│   ├── BUSINESS_REPORT.md         # Investor / stakeholder brief
│   ├── MARKETING_STRATEGY.md      # Launch & growth plan
│   ├── init/                      # Original requirements (read-only)
│   └── spec/                      # 18 core SPEC documents
│       ├── 00_ARCHITECTURE.md
│       ├── 01_AGENT_SPEC.md
│       ├── 02_NETWORK_SPEC.md
│       ├── 03_DIFFUSION_SPEC.md
│       ├── 04_SIMULATION_SPEC.md
│       ├── 05_LLM_SPEC.md
│       ├── 06_API_SPEC.md
│       ├── 07_FRONTEND_SPEC.md
│       ├── 08_DB_SPEC.md
│       ├── 09_HARNESS_SPEC.md
│       ├── 10_VALIDATION_SPEC.md
│       ├── 11_SKILLS_SPEC.md
│       ├── 15_DEV_WORKFLOW_SPEC.md
│       ├── 16_COMMUNITY_MGMT_SPEC.md
│       ├── 17_PERFORMANCE_SPEC.md
│       ├── 18_FRONTEND_PERFORMANCE_SPEC.md
│       ├── MASTER_SPEC.md
│       └── ui/                    # 16 UI screen specs
│
├── backend/                       # FastAPI backend
│   ├── app/
│   │   ├── api/                   # 55+ REST endpoints + WebSocket
│   │   ├── engine/
│   │   │   ├── agent/             # 6-Layer agent engine
│   │   │   ├── network/           # Hybrid network generator
│   │   │   ├── diffusion/         # Propagation, exposure, cascade
│   │   │   └── simulation/        # Step runner, orchestrator
│   │   ├── llm/                   # Ollama / Claude / OpenAI / Gemini
│   │   └── models/                # SQLAlchemy ORM
│   ├── harness/                   # F18–F30 test harness
│   ├── tests/                     # 861 GREEN tests
│   └── pyproject.toml             # uv-managed
│
├── frontend/                      # React 18 frontend
│   ├── src/
│   │   ├── pages/                 # 20 pages
│   │   ├── components/            # Graph, Control, Timeline, Metrics
│   │   ├── store/                 # Zustand state
│   │   ├── api/                   # API client
│   │   ├── hooks/                 # Custom hooks
│   │   ├── config/constants.ts    # All shared constants (no hardcoded literals)
│   │   └── __tests__/             # 373 GREEN tests
│   └── package.json
│
└── docker-compose.yml             # PostgreSQL + Valkey + Ollama + App
```

---

## SPEC Documents

Prophet is **SPEC-driven**: every feature has a written spec before any code
ships. Tests are written from the spec, not the implementation.

| #   | Document                  | Description                                         |
|-----|---------------------------|-----------------------------------------------------|
| 00  | ARCHITECTURE              | System architecture and directory layout            |
| 01  | AGENT_SPEC                | 6-Layer Agent Engine with 12 action types           |
| 02  | NETWORK_SPEC              | Hybrid Network Generator (WS + BA + bridges)        |
| 03  | DIFFUSION_SPEC            | RecSys exposure + propagation + cascade detection   |
| 04  | SIMULATION_SPEC           | Simulation Orchestrator with async locks            |
| 05  | LLM_SPEC                  | LLM Adapter + 3-tier batched inference              |
| 06  | API_SPEC                  | 55+ REST endpoints + WebSocket protocol             |
| 07  | FRONTEND_SPEC             | React 18 components + GAP-7 propagation animation   |
| 08  | DB_SPEC                   | PostgreSQL 16 + pgvector schema                     |
| 09  | HARNESS_SPEC              | F18–F30 test harness                                |
| 10  | VALIDATION_SPEC           | Validation methodology (Twitter15/16)               |
| 11  | SKILLS_SPEC               | Plugins & skills configuration                      |
| 15  | DEV_WORKFLOW_SPEC         | Model selection (Opus / Sonnet) + dev workflow      |
| 16  | COMMUNITY_MGMT_SPEC       | Runtime community management                        |
| 17  | PERFORMANCE_SPEC          | Backend perf optimization (19 findings)             |
| 18  | FRONTEND_PERFORMANCE_SPEC | Frontend perf optimization (29 findings)            |
| UI  | 16 UI screen SPECs        | Screen-level design specs (Pencil sync)             |

See [`docs/spec/MASTER_SPEC.md`](docs/spec/MASTER_SPEC.md) for the full index
and [`docs/spec/SPEC_CHECKLIST.md`](docs/spec/SPEC_CHECKLIST.md) for
implementation status.

---

## Roadmap

**Shipped (April 2026):**
- ✅ Phase 0–7: Core engine, network, diffusion, LLM, simulation, visualization
- ✅ Phase A–H: API integration, UI, real APIs, design tokens, DB, validation, harness, perf
- ✅ GAP-7: Real-time propagation animation (zoom-based LOD)
- ✅ Tier A+B performance optimizations (backend + frontend)
- ✅ Pause/Resume/Run-All controls verified by SPEC contract tests

**In progress:**
- 🟡 Cloud Starter tier (hosted, $99/month)
- 🟡 Scenario template marketplace
- 🟡 Validation studies vs. real campaigns

**Planned:**
- ⬜ Plugin SDK for custom agent layers
- ⬜ Integration with Segment / mParticle / HubSpot
- ⬜ Synthetic population marketplace (industry-specific)
- ⬜ Multi-language LLM agents (cross-cultural simulation)

---

## Contributing

Contributions are welcome! Prophet follows a SPEC-first development model:

1. Find or create a SPEC for the change in `docs/spec/`
2. Write tests against the SPEC contract first
3. Implement until tests pass
4. Submit PR with SPEC reference in the description

See [`CLAUDE.md`](CLAUDE.md) for the full contributor guide and coding rules
(no hardcoded domain literals, no `pip` — `uv` only, etc.).

### Running the test suite

```bash
# Backend
cd backend && uv run pytest -q

# Frontend
cd frontend && npx vitest run

# Type check
cd frontend && npx tsc --noEmit

# Lint
cd frontend && npx eslint .

# E2E
cd frontend && npx playwright test
```

---

## Documentation

- 📊 **[Business Report](docs/BUSINESS_REPORT.md)** — investor / stakeholder brief
- 📣 **[Marketing Strategy](docs/MARKETING_STRATEGY.md)** — launch & growth plan
- 📚 **[SPEC Index](docs/spec/MASTER_SPEC.md)** — all 18 core specs
- ✅ **[SPEC Checklist](docs/spec/SPEC_CHECKLIST.md)** — implementation status
- 🎨 **[Design System](DESIGN.md)** — UI tokens, components, Pencil integration
- 🤖 **[Contributor Guide](CLAUDE.md)** — coding rules, workflow, SPEC-gate

---

## License

MIT — see [LICENSE](LICENSE) file.

---

## Citation

If you use Prophet in academic research, please cite:

```bibtex
@software{prophet_mcasp_2026,
  title  = {Prophet (MCASP): Multi-Community Agent Simulation Platform},
  author = {Prophet Contributors},
  year   = {2026},
  url    = {https://github.com/your-org/prophet}
}
```

---

**Built with care. Tested obsessively. Open-sourced to make marketing less of a guess.**
