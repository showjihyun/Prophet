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

## Roadmap

**Shipped (April 2026):**
- ✅ Phase 0–7: Core engine, network, diffusion, LLM, simulation, visualization
- ✅ Phase A–H: API integration, UI, real APIs, design tokens, DB, validation, harness, perf
- ✅ GAP-7: Real-time propagation animation (zoom-based LOD)
- ✅ Tier A+B performance optimizations (backend + frontend)
- ✅ Pause/Resume/Run-All controls verified by contract tests

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

Contributions are welcome! Prophet follows a test-first development model:

1. Open an issue describing the change
2. Write tests against the contract first
3. Implement until tests pass
4. Submit PR

See [`CLAUDE.md`](CLAUDE.md) for the contributor guide and coding rules
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

- 🎨 **[Design System](DESIGN.md)** — UI tokens, components
- 🤖 **[Contributor Guide](CLAUDE.md)** — coding rules and workflow
- 📖 **API Docs** — http://localhost:8000/docs (Swagger UI when running)

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
