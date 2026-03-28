# Prophet (MCASP)

**Multi-Community Agent Simulation Platform**

A platform for pre-simulating the spread of marketing campaigns, policies, and messages in an AI-powered virtual society.
An agent-based social simulation engine combining LLM + GraphRAG + Viral Diffusion.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (React 18 + Cytoscape.js + Recharts)               │
├──────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI + WebSocket)                             │
├──────────────┬──────────────┬────────────┬───────────────────┤
│ Agent Engine │  Network Gen │  Diffusion │  LLM (SLM/LLM)   │
│  6-Layer     │  WS + BA     │  Cascade   │  3-Tier           │
├──────────────┴──────────────┴────────────┴───────────────────┤
│  PostgreSQL 16 + pgvector  │  Valkey  │  Ollama              │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 23+ (for frontend development)
- Python 3.12+ & uv (for backend development)

### Run with Docker

```bash
# CPU environment (no GPU)
docker compose up -d

# Pull LLM model (first time only, ~4.7GB)
docker compose exec ollama ollama pull llama3.1:8b

# GPU environment (NVIDIA)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Ollama | http://localhost:11434 |

### Local Development

```bash
# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Tests
cd backend
uv run pytest -v
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Visualization | Cytoscape.js (WebGL), Recharts |
| State Management | Zustand, TanStack Query, WebSocket |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async) |
| LLM | Ollama (SLM Tier 1), Claude API, OpenAI API |
| Database | PostgreSQL 16 + pgvector |
| Cache | Valkey |
| Package Manager | uv (Python), npm (Node) |

## Core Engines

### Agent 6-Layer Engine
```
Perception → Memory (GraphRAG) → Emotion → Cognition → Decision → Influence
```
- 12 action types: ignore, view, search, like, save, comment, share, repost, follow, unfollow, adopt, mute
- 3-Tier inference: Mass SLM (80%) → Heuristic (10%) → Elite LLM (10%)
- Configurable from UI Settings page (no hardcoded models)

### Hybrid Network Generator
- Watts-Strogatz (community clustering) + Barabasi-Albert (influencer power-law)
- Dynamic edge evolution per simulation step
- 5 community types: Early Adopters, Consumers, Skeptics, Experts, Influencers

### Social Diffusion Engine
- RecSys-inspired exposure model (OASIS-inspired feed ranking)
- 5 emergent behavior detections: Viral Cascade, Polarization, Echo Chamber, Collapse, Slow Adoption
- Monte Carlo simulation (N-run probability analysis)

## Project Structure

```
Prophet/
├── CLAUDE.md              # Claude Code project instructions
├── DESIGN.md              # UI design master (Pencil integration)
├── docs/spec/             # 14 core SPEC documents
│   └── ui/                # 12 UI screen SPECs
├── backend/               # FastAPI backend (71 Python files)
│   ├── app/engine/        # Agent, Network, Diffusion, Simulation
│   ├── app/llm/           # LLM Adapter (Ollama/Claude/OpenAI)
│   ├── app/api/           # 30 REST endpoints + WebSocket
│   └── tests/             # 424 GREEN tests
├── frontend/              # React 18 frontend (41 TS/TSX files)
│   ├── src/pages/         # 10 pages
│   ├── src/components/    # Graph, Timeline, Control, Metrics, Shared
│   └── src/store/         # Zustand state management
└── docker-compose.yml     # PostgreSQL + Valkey + Ollama + App
```

## SPEC Documents

| # | Document | Description |
|---|----------|-------------|
| 00 | ARCHITECTURE | System architecture and directory layout |
| 01 | AGENT_SPEC | 6-Layer Agent Engine with 12 action types |
| 02 | NETWORK_SPEC | Hybrid Network Generator (WS + BA) |
| 03 | DIFFUSION_SPEC | Social Diffusion Engine with RecSys |
| 04 | SIMULATION_SPEC | Simulation Orchestrator with async locks |
| 05 | LLM_SPEC | LLM Adapter + SLM Batch Inference |
| 06 | API_SPEC | FastAPI Endpoints + Settings API |
| 07 | FRONTEND_SPEC | React 18 Components + TanStack Query |
| 08 | DB_SPEC | PostgreSQL 16 + pgvector schema |
| 09 | HARNESS_SPEC | Test Harness F18-F30 |
| 10 | VALIDATION_SPEC | Validation Methodology (Twitter15/16) |
| 11 | SKILLS_SPEC | Plugins & skills configuration |
| UI | 12 UI SPECs | Screen-level design specs (Pencil sync) |

## License

See [LICENSE](LICENSE) file.
