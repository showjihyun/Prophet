# Prophet (MCASP)

**Multi-Community Agent Simulation Platform**

AI 기반 가상 사회에서 마케팅 캠페인/정책/메시지의 확산을 사전 시뮬레이션하는 플랫폼.
LLM + GraphRAG + Viral Diffusion을 결합한 Agent 기반 사회 시뮬레이션 엔진.

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
- Node.js 23+ (frontend 개발 시)
- Python 3.12+ & uv (backend 개발 시)

### Docker로 실행

```bash
# CPU 환경 (GPU 없는 머신)
docker compose up -d

# GPU 환경 (NVIDIA)
docker compose --profile gpu up -d
```

| 서비스 | URL |
|--------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Ollama | http://localhost:11434 |

### 로컬 개발

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
| State | Zustand, TanStack Query, WebSocket |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async) |
| LLM | Ollama (SLM Tier 1), Claude API, OpenAI API |
| Database | PostgreSQL 16 + pgvector |
| Cache | Valkey |
| Package | uv (Python), npm (Node) |

## Core Engines

### Agent 6-Layer Engine
```
Perception → Memory (GraphRAG) → Emotion → Cognition → Decision → Influence
```
- 12 action types (ignore, view, search, like, save, comment, share, repost, follow, unfollow, adopt, mute)
- 3-Tier inference: Mass SLM (80%) → Heuristic (10%) → Elite LLM (10%)

### Hybrid Network Generator
- Watts-Strogatz (community clustering) + Barabasi-Albert (influencer power-law)
- Dynamic edge evolution per simulation step

### Social Diffusion Engine
- RecSys-inspired exposure model (OASIS concept)
- 5 emergent behavior detection: Viral, Polarization, Echo Chamber, Collapse, Slow Adoption
- Monte Carlo simulation (N-run probability analysis)

## Project Structure

```
Prophet/
├── CLAUDE.md              # Claude Code 프로젝트 지침
├── DESIGN.md              # UI 디자인 총괄 (Pencil 연동)
├── docs/spec/             # 19 SPEC 문서
│   └── ui/                # 5 UI 화면 SPEC
├── backend/               # FastAPI (70 Python files)
│   ├── app/engine/        # Agent, Network, Diffusion, Simulation
│   ├── app/llm/           # LLM Adapter (Ollama/Claude/OpenAI)
│   ├── app/api/           # 26 REST endpoints + WebSocket
│   └── tests/             # 411 tests
├── frontend/              # React 18 (34 TS/TSX files)
│   ├── src/pages/         # 7 pages
│   ├── src/components/    # Graph, Timeline, Control, Metrics
│   └── src/store/         # Zustand
└── docker-compose.yml     # PostgreSQL + Valkey + Ollama + App
```

## SPEC Documents

| # | Document | Description |
|---|----------|-------------|
| 00 | ARCHITECTURE | System architecture |
| 01 | AGENT_SPEC | 6-Layer Agent Engine |
| 02 | NETWORK_SPEC | Hybrid Network Generator |
| 03 | DIFFUSION_SPEC | Social Diffusion Engine |
| 04 | SIMULATION_SPEC | Simulation Orchestrator |
| 05 | LLM_SPEC | LLM Adapter + SLM Batch |
| 06 | API_SPEC | FastAPI Endpoints |
| 07 | FRONTEND_SPEC | React 18 Components |
| 08 | DB_SPEC | PostgreSQL + pgvector |
| 09 | HARNESS_SPEC | Test Harness F18-F30 |
| 10 | VALIDATION_SPEC | Validation Methodology |

## License

See [LICENSE](LICENSE) file.
