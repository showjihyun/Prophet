# 06 — FastAPI Endpoint SPEC
Version: 0.2.0 | Status: REVIEW

---

## 1. Base URL & Versioning

```
Base URL: http://localhost:8000/api/v1
WebSocket: ws://localhost:8000/ws
Health:    http://localhost:8000/health
```

All endpoints return JSON. Errors follow RFC 7807 Problem Details format.

### Authentication

All endpoints except `/auth/*` and `/health` accept an optional `Authorization: Bearer <token>` header.
In development mode, authentication is optional. In production, unauthenticated requests return 401.

---

## 2. Simulation Endpoints

### POST /simulations
Create a new simulation run.

**Request:**
```json
{
  "name": "Q2 Smartphone Launch",
  "description": "Test campaign for Model X",
  "campaign": {
    "name": "Model X Launch",
    "budget": 5000000,
    "channels": ["sns", "influencer", "online_ads"],
    "message": "Revolutionary AI camera phone",
    "target_communities": ["all"],
    "controversy": 0.1,
    "novelty": 0.8,
    "utility": 0.7
  },
  "communities": [           // null = use defaults (5 communities, 1000 agents)
    {
      "id": "A",
      "name": "Early Adopters",
      "size": 100,
      "agent_type": "early_adopter",
      "personality_profile": {
        "openness": 0.8,
        "skepticism": 0.3,
        "trend_following": 0.7,
        "brand_loyalty": 0.4,
        "social_influence": 0.6
      }
    }
  ],
  "max_steps": 50,
  "default_llm_provider": "ollama",
  "random_seed": 42,
  "project_id": "uuid (optional)",
  "slm_llm_ratio": 0.5,
  "slm_model": "phi4",
  "budget_usd": 50.0
}
```

**Response 201:**
```json
{
  "simulation_id": "uuid",
  "status": "configured",
  "total_agents": 1000,
  "network_metrics": { "clustering_coefficient": 0.42, "avg_path_length": 4.8 },
  "created_at": "2026-03-27T00:00:00Z"
}
```

---

### GET /simulations
List all simulation runs.

**Query params:** `status`, `limit` (default 20), `offset`

**Response 200:** `{ "items": [SimulationSummary], "total": int }`

---

### GET /simulations/{simulation_id}
Get simulation details.

**Response 200:** Full SimulationRun object including current_step, status, config.

---

### POST /simulations/{simulation_id}/start
Start the simulation (begins automatic step loop).

**Response 200:** `{ "status": "running", "started_at": "..." }`

---

### POST /simulations/{simulation_id}/step
Execute exactly one step (manual control mode).

**Response 200:** `StepResult`

---

### POST /simulations/{simulation_id}/pause
Pause after current step completes.

**Response 200:** `{ "status": "paused", "current_step": int }`

---

### POST /simulations/{simulation_id}/resume
Resume from paused state.

**Response 200:** `{ "status": "running" }`

---

### POST /simulations/{simulation_id}/stop
Stop and mark as completed.

**Response 200:** `{ "status": "completed" }`

---

### GET /simulations/{simulation_id}/steps
Get step history.

**Query params:** `from_step`, `to_step`, `metrics` (comma-separated metric names)

**Response 200:**
```json
{
  "steps": [
    {
      "step": 1,
      "adoption_rate": 0.03,
      "mean_sentiment": 0.21,
      "diffusion_rate": 12,
      "emergent_events": [],
      "total_adoption": 30,
      "sentiment_variance": 0.08,
      "community_metrics": {
        "<community_id>": {
          "community_id": "uuid",
          "adoption_count": 15,
          "adoption_rate": 0.03,
          "mean_belief": 0.21,
          "dominant_action": "share",
          "new_propagation_count": 8,
          "sentiment_variance": 0.05,
          "active_agents": 500
        }
      },
      "action_distribution": {},
      "propagation_pairs": [
        { "source": "agent-id-1", "target": "agent-id-2", "action": "share", "probability": 0.85 },
        { "source": "agent-id-3", "target": "agent-id-4", "action": "comment", "probability": 0.42 }
      ],
      "llm_calls_this_step": 5,
      "step_duration_ms": 287
    }
  ]
}
```

---

### POST /simulations/{simulation_id}/inject-event
Inject an external event mid-simulation.

**Request:**
```json
{
  "event_type": "controversy",
  "content": "Battery explosion report",
  "controversy": 0.9,
  "target_communities": ["C"]
}
```

**Response 200:** `{ "event_id": "uuid", "effective_step": int }`

---

### POST /simulations/{simulation_id}/replay/{step}
Replay from a specific step (creates branch).

**Response 200:** `{ "replay_id": "uuid", "from_step": int }`

---

### GET /simulations/{simulation_id}/compare/{other_simulation_id}
Compare two simulation runs.

**Response 200:** `ScenarioComparison`

---

### POST /simulations/{simulation_id}/monte-carlo
Run Monte Carlo analysis.

**Request:**
```json
{ "n_runs": 100, "llm_enabled": false }
```

**Response 202:** `{ "job_id": "uuid", "status": "queued" }`

> **구현 참고:** 현재 Monte Carlo는 `asyncio.create_task` (in-process)로 실행됨. Celery + Valkey 큐 통합은 Scale Phase에서 예정.

---

### GET /simulations/{simulation_id}/monte-carlo/{job_id}
Get Monte Carlo job status and results.

**Response 200 (running):**
```json
{
  "job_id": "uuid",
  "status": "running",
  "n_runs": 100,
  "completed_runs": 42,
  "started_at": "2026-03-27T10:00:00Z"
}
```

**Response 200 (completed):**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "n_runs": 100,
  "viral_probability": 0.73,
  "expected_reach": 642,
  "p5_reach": 210,
  "p50_reach": 650,
  "p95_reach": 890,
  "community_adoption": {
    "A": 0.92, "B": 0.71, "C": 0.35, "D": 0.80, "E": 0.88
  },
  "started_at": "2026-03-27T10:00:00Z",
  "completed_at": "2026-03-27T10:01:23Z"
}
```

**Response 200 (failed):**
```json
{
  "job_id": "uuid",
  "status": "failed",
  "error_message": "Worker timeout after 300s"
}
```

---

### POST /simulations/{simulation_id}/engine-control
Adjust SLM/LLM ratio at runtime (simulation must be PAUSED).

**Request:**
```json
{
  "slm_llm_ratio": 0.7,
  "slm_model": "phi4",
  "budget_usd": 50.0
}
```

**Response 200:**
```json
{
  "tier_distribution": {
    "tier1_count": 600,
    "tier2_count": 200,
    "tier3_count": 200,
    "estimated_cost_per_step": 2.40,
    "estimated_latency_ms": 1200
  },
  "impact_assessment": {
    "cost_efficiency": "$2.40 per step",
    "reasoning_depth": "질적 분석 (Qualitative)",
    "simulation_velocity": "~1.2s per step",
    "prediction_type": "Hybrid"
  }
}
```

---

### POST /simulations/recommend-engine
Budget-based auto engine recommendation (Prophet-unique feature).

**Request:**
```json
{
  "agent_count": 100000,
  "budget_usd": 100.0,
  "max_steps": 50
}
```

**Response 200:**
```json
{
  "recommended_ratio": 0.05,
  "recommended_slm_model": "gemma2:2b",
  "tier_distribution": {
    "tier1_count": 95000,
    "tier2_count": 4000,
    "tier3_count": 1000
  },
  "estimated_total_cost": 89.50,
  "estimated_total_time": "4m 30s",
  "mode": "SLM 모드"
}
```

---

### POST /simulations/{simulation_id}/run-all
Run all remaining steps to completion and return summary report.

**Response 200:**
```json
{
  "simulation_id": "uuid",
  "status": "completed",
  "total_steps": 50,
  "final_adoption_rate": 0.72,
  "final_mean_sentiment": 0.58,
  "community_summary": [],
  "emergent_events_count": 3,
  "duration_ms": 14320
}
```

---

### GET /simulations/{simulation_id}/export
Export simulation data as JSON or CSV.

**Query params:** `format` (`json` | `csv`, default `json`)

**Response:** File download with `Content-Disposition` header.

---

### POST /simulations/{simulation_id}/group-chat
Create a group chat session between agents.

**Request:**
```json
{
  "agent_ids": ["uuid1", "uuid2", "uuid3"],
  "topic": "Campaign discussion"
}
```

**Response 201:** `{ "group_id": "uuid", "participants": int }`

---

### GET /simulations/{simulation_id}/group-chat/{group_id}
Get group chat messages.

**Response 200:** `{ "group_id": "uuid", "messages": [ChatMessage] }`

---

### POST /simulations/{simulation_id}/group-chat/{group_id}/message
Add a message to group chat (researcher intervention).

**Request:** `{ "content": "What do you think about the campaign?" }`

**Response 200:** `{ "messages": [ChatMessage] }`

---

## 3. Agent Endpoints

### GET /simulations/{simulation_id}/agents
List agents with current state.

**Query params:** `community_id`, `action`, `adopted`, `limit`, `offset`

**Response 200:** `{ "items": [AgentSummary], "total": int }`

---

### GET /simulations/{simulation_id}/agents/{agent_id}
Get full agent state at current step.

**Response 200:** Full `AgentState` + `memories` (last 10) + influence_score.

---

### PATCH /simulations/{simulation_id}/agents/{agent_id}
Modify agent (simulation must be PAUSED).

**Request:**
```json
{
  "personality": { "skepticism": 0.8 },
  "emotion": { "trust": 0.2 },
  "belief": -0.5
}
```

**Response 200:** Updated `AgentState`

---

### GET /simulations/{simulation_id}/agents/{agent_id}/memory
Get agent memory records.

**Query params:** `memory_type`, `limit`

**Response 200:** `{ "memories": [MemoryRecord] }`

---

### POST /simulations/{simulation_id}/agents/{agent_id}/interview
Interview an agent mid-simulation (Tier 3 LLM).

**Request:**
```json
{
  "question": "What is your current opinion about the campaign?"
}
```

**Response 200:**
```json
{
  "agent_id": "uuid",
  "response": "I'm skeptical about the claims...",
  "emotion_state": { "trust": 0.3, "interest": 0.6 },
  "belief": 0.25
}
```

---

## 4. Network Endpoints

### GET /simulations/{simulation_id}/network
Get network graph data (for visualization).

**Query params:** `format` (`cytoscape` | `d3` | `raw`)

**Response 200 (cytoscape format):**
```json
{
  "nodes": [
    {
      "data": {
        "id": "agent_uuid",
        "label": "Agent 42",
        "community": "A",
        "agent_type": "early_adopter",
        "influence_score": 0.82,
        "emotion_state": { "interest": 0.7, "trust": 0.5 },
        "action": "share",
        "adopted": true
      }
    }
  ],
  "edges": [
    {
      "data": {
        "id": "edge_uuid_uuid",
        "source": "agent_uuid_1",
        "target": "agent_uuid_2",
        "weight": 0.65,
        "is_bridge": false
      }
    }
  ]
}
```

---

### GET /simulations/{simulation_id}/network/metrics
Current network metrics.

**Response 200:** `NetworkMetrics`

---

## 5. Community Endpoints

### GET /simulations/{simulation_id}/communities
List all communities with current metrics.

**Response 200:**
```json
{
  "communities": [
    {
      "community_id": "uuid",
      "name": "early_adopters",
      "size": 100,
      "adoption_rate": 0.32,
      "mean_belief": 0.65,
      "sentiment_variance": 0.12,
      "dominant_action": "share"
    }
  ]
}
```

### 5.2 Community Configuration (Template) Endpoints

Communities can be configured as templates before simulation creation.

### GET /communities/templates
List available community templates.

**Response 200:**
```json
{
  "templates": [
    {
      "template_id": "uuid",
      "name": "Early Adopters",
      "agent_type": "early_adopter",
      "default_size": 100,
      "description": "Tech-savvy, high openness, trend-following"
    }
  ]
}
```

### POST /communities/templates
Create a community template.

**Request:**
```json
{
  "name": "Custom Community",
  "agent_type": "consumer",
  "default_size": 200,
  "description": "Custom consumer segment",
  "personality_profile": {
    "openness": 0.6,
    "skepticism": 0.4,
    "trend_following": 0.5,
    "brand_loyalty": 0.3,
    "social_influence": 0.4
  }
}
```

**Response 201:** Template object with template_id.

### PUT /communities/templates/{template_id}
Update a community template.

### DELETE /communities/templates/{template_id}
Delete a community template.

---

### 5.3 Conversation Thread Endpoints

Threads are derived from simulation agent state — not stored entities.

### GET /simulations/{simulation_id}/communities/{community_id}/threads
List synthetic conversation threads for a community.

**Response 200:**
```json
{
  "threads": [
    {
      "thread_id": "A-thread-0",
      "topic": "Viral spread of the campaign message in community A",
      "participant_count": 4,
      "message_count": 6,
      "avg_sentiment": 0.31
    }
  ]
}
```

### GET /simulations/{simulation_id}/communities/{community_id}/threads/{thread_id}
Return messages for a specific thread.

**Response 200:**
```json
{
  "thread_id": "A-thread-0",
  "topic": "...",
  "participant_count": 4,
  "message_count": 6,
  "avg_sentiment": 0.31,
  "messages": [
    {
      "message_id": "t0-m0",
      "agent_id": "Agent-A1A2B",
      "community_id": "A",
      "stance": "Progressive",
      "content": "The campaign message resonates strongly...",
      "reactions": { "agree": 12, "disagree": 3, "nuanced": 5 },
      "is_reply": false,
      "reply_to_id": null
    }
  ]
}
```

---

## 6. LLM Dashboard Endpoints

### GET /simulations/{simulation_id}/llm/stats
LLM usage statistics for the simulation.

**Response 200:**
```json
{
  "total_calls": 342,
  "cached_calls": 128,
  "provider_breakdown": { "ollama": 280, "claude": 62 },
  "avg_latency_ms": 234,
  "total_tokens": 45200,
  "tier_breakdown": { "1": 8200, "2": 1500, "3": 342 }
}
```

---

### GET /simulations/{simulation_id}/llm/calls
Recent LLM call logs.

**Query params:** `step`, `agent_id`, `provider`, `limit`

**Response 200:** `{ "calls": [LLMCallLog] }`

---

### GET /simulations/{simulation_id}/llm/impact
Get current engine impact assessment (4 indicators).

**Response 200:**
```json
{
  "slm_llm_ratio": 0.5,
  "tier_distribution": { "tier1": 800, "tier2": 100, "tier3": 100 },
  "impact": {
    "cost_efficiency": "$0.45 per step",
    "reasoning_depth": "균형 (Balanced)",
    "simulation_velocity": "~2s per step",
    "prediction_type": "Hybrid"
  },
  "slm_model": "phi4",
  "slm_batch_throughput": "450 agents/sec"
}
```

---

## 7. Settings Endpoints

### GET /api/v1/settings
Get current system settings.

**Response 200:**
```json
{
  "llm": {
    "default_provider": "ollama",
    "ollama_base_url": "http://localhost:11434",
    "ollama_default_model": "llama3.1:8b",
    "slm_model": "llama3.1:8b",
    "ollama_embed_model": "llama3.1:8b",
    "anthropic_model": "claude-sonnet-4-6",
    "anthropic_api_key_set": true,
    "openai_model": "gpt-4o",
    "openai_api_key_set": false
  },
  "simulation": {
    "slm_llm_ratio": 0.5,
    "llm_tier3_ratio": 0.1,
    "llm_cache_ttl": 3600
  }
}
```

### PUT /api/v1/settings
Update system settings.

**Request:**
```json
{
  "llm": {
    "default_provider": "ollama",
    "ollama_base_url": "http://localhost:11434",
    "ollama_default_model": "llama3.1:8b",
    "slm_model": "llama3.1:8b",
    "ollama_embed_model": "llama3.1:8b",
    "anthropic_api_key": "sk-ant-...",
    "anthropic_model": "claude-sonnet-4-6",
    "openai_api_key": "sk-...",
    "openai_model": "gpt-4o"
  },
  "simulation": {
    "slm_llm_ratio": 0.5,
    "llm_tier3_ratio": 0.1,
    "llm_cache_ttl": 3600
  }
}
```

**Response 200:** `{ "status": "ok" }`

### GET /api/v1/settings/ollama-models
List available Ollama models (calls Ollama /api/tags).

**Response 200:**
```json
{
  "models": ["llama3.1:8b", "llama3:latest", "llava:latest"]
}
```

### POST /api/v1/settings/test-ollama
Test Ollama connection.

**Response 200:**
```json
{ "status": "ok", "model": "llama3.1:8b", "latency_ms": 234 }
```

**Response 200 (error):**
```json
{ "status": "error", "message": "Connection refused" }
```

---

## 8. WebSocket — /ws/{simulation_id}

**Connection:** `ws://localhost:8000/ws/{simulation_id}`

**Server → Client messages:**
```typescript
// Step completed
{ type: "step_result", data: StepResult }

// Emergent behavior detected
{ type: "emergent_event", data: EmergentEvent }

// Simulation status changed
{ type: "status_change", data: { status: SimulationStatus, step: number } }

// Single agent update (for hover detail)
{ type: "agent_update", data: AgentState }
```

**Client → Server messages:**
```typescript
{ type: "pause" }
{ type: "resume" }
{ type: "inject_event", data: EnvironmentEvent }
{ type: "subscribe_agent", data: { agent_id: string } }   // get per-tick agent updates
{ type: "unsubscribe_agent", data: { agent_id: string } }
```

---

## 9. Error Response Format

```json
{
  "type": "https://prophet.io/errors/simulation-not-found",
  "title": "Simulation Not Found",
  "status": 404,
  "detail": "Simulation uuid=abc123 does not exist",
  "instance": "/api/v1/simulations/abc123"
}
```

**Error codes:**

| Status | Code | Trigger |
|--------|------|---------|
| 400 | `invalid-config` | Invalid simulation config |
| 404 | `not-found` | Resource not found |
| 409 | `simulation-running` | Action not allowed in current status |
| 409 | `agent-modify-requires-pause` | Modify agent while simulation running |
| 422 | `validation-error` | Request body validation failure |
| 503 | `llm-unavailable` | All LLM providers unreachable |

---

## 9. Project & Scenario Endpoints

Projects group related simulation scenarios. Each scenario maps to a simulation run.

### POST /projects
Create a new project.

**Request:**
```json
{
  "name": "Q2 Smartphone Launch",
  "description": "Multi-scenario campaign analysis"
}
```

**Response 201:**
```json
{
  "project_id": "uuid",
  "name": "Q2 Smartphone Launch",
  "description": "...",
  "status": "active",
  "created_at": "2026-03-30T..."
}
```

### GET /projects
List all projects.

**Response 200:** `ProjectSummary[]` (array directly, no wrapper)
```json
[
  {
    "project_id": "uuid",
    "name": "Q2 Smartphone Launch",
    "description": "...",
    "scenario_count": 3,
    "status": "active",
    "created_at": "..."
  }
]
```

### GET /projects/{project_id}
Get project detail with scenario list.

**Response 200:**
```json
{
  "project_id": "uuid",
  "name": "...",
  "description": "...",
  "status": "active",
  "scenarios": [
    {
      "scenario_id": "uuid",
      "name": "Default Scenario",
      "description": "...",
      "status": "draft",
      "simulation_id": "uuid | null",
      "config": { ... },
      "created_at": "..."
    }
  ],
  "created_at": "..."
}
```

### POST /projects/{project_id}/scenarios
Create a new scenario under a project.

**Request:**
```json
{
  "name": "Viral Campaign",
  "description": "High-controversy test",
  "config": {
    "campaign": { ... },
    "max_steps": 50,
    "slm_llm_ratio": 0.5
  }
}
```

**Response 201:**
```json
{
  "scenario_id": "uuid",
  "name": "Viral Campaign",
  "status": "draft",
  "created_at": "..."
}
```

### POST /projects/{project_id}/scenarios/{scenario_id}/run
Run a scenario (creates a simulation and starts it).

**Response 200:**
```json
{
  "simulation_id": "uuid",
  "status": "running"
}
```

### PATCH /projects/{project_id}
Update project name/description.

**Request:**
```json
{
  "name": "Updated Name",
  "description": "Updated description"
}
```

**Response 200:** Updated `ProjectSummary`

---

### DELETE /projects/{project_id}
Delete project and all its scenarios.

**Response 204:** No content.

---

### DELETE /projects/{project_id}/scenarios/{scenario_id}
Delete a scenario.

**Response 204:** No content.

---

## 10. Settings Sub-Endpoints

### GET /api/v1/settings/platforms
List available platform plugins.

**Response 200:** `{ "platforms": [] }`

---

### GET /api/v1/settings/recsys
List available RecSys algorithms.

**Response 200:** `{ "algorithms": [] }`

---

## 11. Authentication Endpoints

### POST /api/v1/auth/register
Register a new user.

**Request:**
```json
{ "username": "researcher1", "password": "securepass" }
```

**Response 201:**
```json
{ "user_id": "uuid", "username": "researcher1" }
```

---

### POST /api/v1/auth/login
Login and receive JWT token.

**Request:**
```json
{ "username": "researcher1", "password": "securepass" }
```

**Response 200:**
```json
{ "token": "eyJhbG...", "user_id": "uuid", "username": "researcher1" }
```

---

### GET /api/v1/auth/me
Get current authenticated user info.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{ "user_id": "uuid", "username": "researcher1" }
```

---

## 12. Health Endpoint

### GET /health
Health check (no `/api/v1` prefix).

**Response 200:**
```json
{ "status": "ok", "version": "0.1.0" }
```

---

## 13. Acceptance Criteria (Harness Tests)

| ID | Test | Expected |
|----|------|----------|
| API-01 | POST /simulations with valid config | 201 + simulation_id |
| API-02 | POST /simulations/{id}/step when CONFIGURED | 409 (must start first) |
| API-03 | GET /simulations/{id}/network in cytoscape format | Valid nodes + edges |
| API-04 | PATCH agent while simulation RUNNING | 409 error |
| API-05 | WebSocket step_result arrives within 500ms | Real-time requirement |
| API-06 | GET /simulations with status filter | Returns only matching status |
| API-07 | POST monte-carlo returns 202 immediately | Async job |
| API-08 | Inject event → reflected in next step metrics | `mean_sentiment` changes |
