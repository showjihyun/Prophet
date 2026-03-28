# 06 — FastAPI Endpoint SPEC
Version: 0.1.0 | Status: DRAFT

---

## 1. Base URL & Versioning

```
Base URL: http://localhost:8000/api/v1
WebSocket: ws://localhost:8000/ws
```

All endpoints return JSON. Errors follow RFC 7807 Problem Details format.

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
  "communities": null,      // null = use defaults (5 communities, 1000 agents)
  "max_steps": 50,
  "default_llm_provider": "ollama",
  "random_seed": 42
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
      "emergent_events": []
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

## 10. Acceptance Criteria (Harness Tests)

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
