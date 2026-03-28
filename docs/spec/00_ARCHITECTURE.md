# 00 — System Architecture
Version: 0.1.0 | Status: DRAFT

---

## 1. Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    React 18 SPA                              │   │
│   │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐  │   │
│   │  │ Graph Panel  │ │Timeline Panel│ │  Control Panel     │  │   │
│   │  │ (Cytoscape)  │ │  (Recharts)  │ │ Play/Pause/Step    │  │   │
│   │  └──────────────┘ └──────────────┘ └────────────────────┘  │   │
│   │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐  │   │
│   │  │ Agent Detail │ │LLM Dashboard │ │  Scenario Config   │  │   │
│   │  │   Hover      │ │Prompt/Quota  │ │  Campaign Input    │  │   │
│   │  └──────────────┘ └──────────────┘ └────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────────┘   │
│              │ REST (TanStack Query)    │ WebSocket                  │
└──────────────┼──────────────────────────┼─────────────────────────── ┘
               │                          │
┌──────────────▼──────────────────────────▼─────────────────────────── ┐
│                          API LAYER (FastAPI)                          │
│                                                                       │
│   ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐    │
│   │  /simulations   │  │  /agents        │  │  /campaigns      │    │
│   │  /steps         │  │  /communities   │  │  /scenarios      │    │
│   │  /metrics       │  │  /networks      │  │  /llm/dashboard  │    │
│   └────────┬────────┘  └────────┬────────┘  └────────┬─────────┘    │
│            │                    │                     │              │
│   ┌────────▼────────────────────▼─────────────────────▼─────────┐   │
│   │                  Simulation Orchestrator                      │   │
│   │     Step Loop → Event Bus → Agent Update → Metric Collect    │   │
│   └──────┬──────────┬──────────────┬──────────────┬─────────────┘   │
└──────────┼──────────┼──────────────┼──────────────┼──────────────── ┘
           │          │              │              │
┌──────────▼─┐  ┌─────▼──────┐  ┌───▼──────┐  ┌───▼──────────────┐
│   AGENT    │  │  NETWORK   │  │DIFFUSION │  │   LLM ADAPTER    │
│   ENGINE   │  │ GENERATOR  │  │  ENGINE  │  │                  │
│            │  │            │  │          │  │  ┌─────────────┐ │
│ Perception │  │Watts-      │  │Exposure  │  │  │   Ollama    │ │
│ Memory     │  │Strogatz    │  │Cognition │  │  │  (local)    │ │
│ Emotion    │  │+           │  │Decision  │  │  └─────────────┘ │
│ Cognition  │  │Barabási-   │  │Propagate │  │  ┌─────────────┐ │
│ Decision   │  │Albert      │  │Cascade   │  │  │   Claude    │ │
│ Action     │  │Hybrid      │  │Detect    │  │  │     API     │ │
│ Influence  │  │            │  │          │  │  └─────────────┘ │
└────────────┘  └────────────┘  └──────────┘  │  ┌─────────────┐ │
                                               │  │  OpenAI     │ │
                                               │  │     API     │ │
                                               │  └─────────────┘ │
                                               └──────────────────┘
           │                              │
┌──────────▼──────────────────────────────▼──────────────────────────┐
│                        DATA LAYER                                    │
│                                                                      │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │              PostgreSQL 16                                  │    │
│   │   ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │    │
│   │   │ simulations  │  │    agents    │  │ agent_memories │  │    │
│   │   │ communities  │  │ agent_states │  │ (pgvector)     │  │    │
│   │   │ campaigns    │  │ network_edge │  │                │  │    │
│   │   │ sim_steps    │  │ llm_calls    │  │ embedding vec  │  │    │
│   │   └──────────────┘  └──────────────┘  └────────────────┘  │    │
│   └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│   ┌──────────────────────┐   ┌─────────────────────────────────┐    │
│   │   Valkey             │   │   NetworkX (in-process)          │    │
│   │   LLM response cache │   │   Runtime social graph G(V,E)   │    │
│   │   Session state      │   │   Rebuilt per simulation run    │    │
│   └──────────────────────┘   └─────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Request Flow — Simulation Step

```
User clicks "Step" in React UI
        │
        ▼ POST /simulations/{id}/step
FastAPI SimulationRouter
        │
        ▼
SimulationOrchestrator.run_step(sim_id, step_num)
        │
        ├──► NetworkGraph.get_active_edges()
        │
        ├──► DiffusionEngine.compute_exposure(agents, graph)
        │         └── ExposureModel → agent exposure scores
        │
        ├──► for each Agent (parallel, asyncio):
        │         AgentEngine.tick(agent, context)
        │              ├── PerceptionLayer.observe(events)
        │              ├── MemoryLayer.retrieve(top_k=10)
        │              ├── EmotionLayer.update(signals)
        │              ├── CognitionLayer.evaluate()   ← rule / heuristic / LLM
        │              ├── DecisionLayer.choose_action()
        │              └── InfluenceLayer.propagate()
        │
        ├──► DiffusionEngine.cascade_detection(step_results)
        │
        ├──► MetricCollector.record(step_num, results)
        │         └── INSERT INTO sim_steps, agent_states
        │
        └──► WebSocket.broadcast(step_summary)
                  └── React UI updates Graph + Timeline
```

---

## 3. 3-Tier Inference Decision (SLM + LLM Hybrid)

```
Agent.tick() → CognitionLayer
        │
        ├── Tier 1: Mass SLM (~80% agents)
        │     Model: Phi-4 / Llama-3-8B (Q4) / Gemma-2B (local Ollama)
        │     Batch inference for efficiency
        │     Input: Contextual Packet (source info + emotion + summary)
        │     Output: structured JSON (evaluation_score, action, reasoning)
        │     Latency: ~50ms per agent (batched: ~5ms/agent)
        │
        ├── Tier 2: Semantic Router (~10% agents)
        │     pgvector similarity check on agent memories
        │     Detects "meaningful change" requiring deeper analysis
        │     No LLM call — vector DB + heuristic scoring
        │     Latency: ~10ms
        │
        └── Tier 3: Elite LLM (≤10% agents per step)
              Model: Claude / GPT-4o / larger Ollama model
              Triggered for: influencers, experts, critical decision points
              Full prompt with agent state + memories + perception
              ├── Ollama large model (default)
              ├── Claude (if agent.llm_provider == "claude")
              └── OpenAI (if agent.llm_provider == "openai")
              Latency: 100-500ms
```

---

## 4. Directory Layout

```
Prophet/
├── docs/
│   ├── init/                      # Original requirements (read-only reference)
│   └── spec/                      # SPEC documents (this directory)
│
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app entrypoint
│   │   ├── config.py              # Settings (env vars)
│   │   ├── database.py            # SQLAlchemy async engine
│   │   │
│   │   ├── api/                   # Route handlers
│   │   │   ├── simulations.py
│   │   │   ├── agents.py
│   │   │   ├── communities.py
│   │   │   ├── campaigns.py
│   │   │   └── ws.py              # WebSocket
│   │   │
│   │   ├── engine/                # Core simulation engines
│   │   │   ├── agent/
│   │   │   │   ├── agent_core.py
│   │   │   │   ├── perception.py
│   │   │   │   ├── memory_layer.py
│   │   │   │   ├── emotion_model.py
│   │   │   │   ├── cognition_engine.py
│   │   │   │   ├── decision_model.py
│   │   │   │   └── influence_model.py
│   │   │   │
│   │   │   ├── network/
│   │   │   │   ├── generator.py
│   │   │   │   ├── community_graph.py
│   │   │   │   └── influencer_layer.py
│   │   │   │
│   │   │   ├── diffusion/
│   │   │   │   ├── exposure_model.py
│   │   │   │   ├── cognition_model.py
│   │   │   │   ├── propagation_model.py
│   │   │   │   ├── cascade_detector.py
│   │   │   │   └── sentiment_model.py
│   │   │   │
│   │   │   └── simulation/
│   │   │       ├── orchestrator.py
│   │   │       ├── step_runner.py
│   │   │       ├── metric_collector.py
│   │   │       └── monte_carlo.py
│   │   │
│   │   ├── llm/
│   │   │   ├── adapter.py         # LLMAdapter interface
│   │   │   ├── ollama_client.py
│   │   │   ├── claude_client.py
│   │   │   ├── openai_client.py
│   │   │   ├── prompt_builder.py
│   │   │   └── cache.py           # Valkey-backed LLM cache
│   │   │
│   │   └── models/                # SQLAlchemy ORM models
│   │       ├── simulation.py
│   │       ├── agent.py
│   │       ├── community.py
│   │       ├── campaign.py
│   │       └── memory.py          # pgvector memory model
│   │
│   ├── harness/                   # F18–F30 test harness
│   │   ├── fixtures/
│   │   ├── mocks/
│   │   └── runners/
│   │
│   ├── tests/
│   ├── migrations/                # Alembic migrations
│   ├── pyproject.toml
│   └── .env.example
│
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── SimulationPage.tsx
    │   │   ├── CampaignSetupPage.tsx
    │   │   └── AnalyticsPage.tsx
    │   │
    │   ├── components/
    │   │   ├── graph/
    │   │   │   ├── GraphPanel.tsx
    │   │   │   └── AgentNode.tsx
    │   │   ├── timeline/
    │   │   │   └── TimelinePanel.tsx
    │   │   ├── control/
    │   │   │   └── ControlPanel.tsx
    │   │   └── llm/
    │   │       └── LLMDashboard.tsx
    │   │
    │   ├── store/                 # Zustand stores
    │   ├── hooks/                 # Custom hooks + TanStack Query
    │   ├── api/                   # API client
    │   └── types/                 # TypeScript types
    │
    ├── package.json
    └── vite.config.ts
```

---

## 5. Package Management — uv

**`pip` 사용 금지. 모든 패키지 관리는 `uv`로만 수행.**

### 백엔드 초기 세팅

```bash
# uv 설치 (미설치 시)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 프로젝트 초기화
cd backend
uv init --python 3.12

# 의존성 추가
uv add fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic
uv add networkx numpy scipy
uv add anthropic openai ollama
uv add valkey celery
uv add pgvector

# 개발 의존성 추가
uv add --dev pytest pytest-asyncio pytest-cov httpx
uv add --dev aiosqlite   # MockDatabase용

# 환경 동기화 (lock 파일 기준)
uv sync

# 스크립트 실행 (pip run 대신)
uv run uvicorn app.main:app --reload
uv run pytest
uv run alembic upgrade head
```

### 금지 사항

```bash
# ❌ 절대 사용 금지
pip install ...
pip3 install ...
python -m pip install ...

# ✅ 올바른 방법
uv add ...
uv sync
uv run ...
```

### pyproject.toml 구조

```toml
[project]
name = "prophet-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "sqlalchemy[asyncio]>=2.0",
    # ... (uv add로 자동 관리)
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    # ...
]
```

- 의존성 파일: `pyproject.toml` + `uv.lock`
- `requirements.txt` 생성 금지
- `.venv/`는 uv가 자동 관리 (git ignore 대상)

---

## 6. Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://prophet:secret@localhost:5432/prophet
VALKEY_URL=valkey://localhost:6379/0

# LLM Providers
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.2

ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_DEFAULT_MODEL=claude-sonnet-4-6

OPENAI_API_KEY=sk-...
OPENAI_DEFAULT_MODEL=gpt-4o

# Simulation Defaults
DEFAULT_LLM_PROVIDER=ollama
LLM_TIER3_RATIO=0.1          # Max 10% agents use LLM per step
LLM_CACHE_TTL=3600           # Valkey cache TTL in seconds
```
