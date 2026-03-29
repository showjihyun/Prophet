# OASIS vs Prophet — Technical Comparison

A deep technical comparison between CAMEL-AI/OASIS and Prophet (MCASP).

---

## 1. Project Overview

| | OASIS (CAMEL-AI) | Prophet (MCASP) |
|---|---|---|
| **Purpose** | General social media simulator | Marketing campaign diffusion simulator |
| **GitHub** | github.com/camel-ai/oasis | github.com/showjihyun/Prophet |
| **Stars** | ~3,900 | New project |
| **License** | Apache 2.0 | — |
| **Python** | 3.10–3.11 | 3.12+ |
| **Package Manager** | Poetry | uv |
| **LLM Framework** | CAMEL-AI (0.2.78) | Self-built (adapter pattern) |
| **Agent Count** | Up to 1,000,000 | 200–10,000 (tested) |

---

## 2. Architecture Comparison

### OASIS Architecture

```
┌─────────────────────────────────────────────┐
│            PettingZoo-style Environment       │
│                                               │
│  ┌──────────────┐  ┌───────────────────────┐ │
│  │  Agent Graph  │  │   Platform (SQLite)   │ │
│  │  (igraph)     │  │   users/posts/likes   │ │
│  │              │  │   follows/mutes       │ │
│  └──────┬───────┘  │   recommendation      │ │
│         │          └───────────┬───────────┘ │
│  ┌──────▼───────┐            │              │
│  │  SocialAgent  │◄───────────┘              │
│  │  (ChatAgent)  │                           │
│  │  LLM → Tool   │  ┌──────────────────────┐ │
│  │  Calls         │  │  Recommendation      │ │
│  └───────────────┘  │  Engine              │ │
│                      │  (TwHIN/HotScore)    │ │
│                      └──────────────────────┘ │
└─────────────────────────────────────────────┘
```

### Prophet Architecture

```
┌─────────────────────────────────────────────────────┐
│          SimulationOrchestrator                       │
│                                                       │
│  Phase 1: Intra-Community (parallel)                 │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐          │
│  │Community A│ │Community B│ │Community C│ ...       │
│  │Orchestrator│ │Orchestrator│ │Orchestrator│          │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘          │
│        │              │              │               │
│  Phase 2: Cross-Community Bridge                     │
│  ┌──────────────────────────────────────────┐        │
│  │          BridgePropagator               │        │
│  │          (trust_factor=0.6)             │        │
│  └──────────────────────────────────────────┘        │
│        │                                             │
│  Phase 3: Global Aggregation                         │
│  ┌──────────────────────────────────────────┐        │
│  │  CascadeDetector + MetricCollector       │        │
│  └──────────────────────────────────────────┘        │
│                                                       │
│  Agent: 6-Layer Pipeline                             │
│  Perception → Memory → Emotion → Cognition →         │
│  Decision → Influence                                │
│                                                       │
│  LLM: 3-Tier (SLM 80% → Heuristic 10% → LLM 10%)  │
└─────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack Comparison

| Component | OASIS | Prophet | Winner |
|-----------|-------|---------|--------|
| **Language** | Python 3.10-3.11 | Python 3.12+ | Prophet (newer) |
| **LLM Framework** | CAMEL-AI (external dep) | Self-built adapter | Prophet (no vendor lock) |
| **LLM Provider** | OpenAI (GPT-4o-mini) | Ollama (local) + Claude + OpenAI | Prophet (local-first) |
| **Inference** | All agents → LLM (100%) | 3-Tier: SLM 80% / Heuristic 10% / LLM 10% | **Prophet** (90% cost savings) |
| **Database** | SQLite | PostgreSQL 16 + pgvector | Prophet (production-grade) |
| **Cache** | None | Valkey (LLM response cache) | Prophet |
| **Graph Engine** | igraph | NetworkX | Tie (both mature) |
| **Network Model** | Follow-based (random P=0.2) | Watts-Strogatz + Barabasi-Albert hybrid | **Prophet** (research-grade) |
| **Frontend** | None (CLI/script) | React 18 + Cytoscape.js + Recharts | **Prophet** |
| **API** | Python script interface | FastAPI 30 endpoints + WebSocket | **Prophet** |
| **Deployment** | pip install | Docker Compose (5 services) | **Prophet** |
| **Package Mgr** | Poetry | uv | Prophet (faster) |

---

## 4. Agent System Comparison

| Feature | OASIS | Prophet | Notes |
|---------|-------|---------|-------|
| **Agent Architecture** | Single LLM call (ChatAgent) | 6-Layer pipeline | Prophet is more structured |
| **Decision Making** | LLM function calling → action | Perception → Memory → Emotion → Cognition → Decision | Prophet has explicit cognitive model |
| **Action Space** | 23 actions (SNS-specific) | 12 actions (marketing-focused) | OASIS has more SNS detail |
| **Emotion Model** | None (implicit in LLM) | Explicit 4-dim vector (interest, trust, skepticism, excitement) | **Prophet** |
| **Personality** | Text profile (LLM interprets) | 5-dim numeric vector (openness, skepticism, trend, loyalty, influence) | **Prophet** (measurable) |
| **Memory** | CAMEL ChatAgent memory (conversation history) | GraphRAG + pgvector (episodic/semantic/social) | **Prophet** |
| **Time Model** | 24-dim activity vector (3 min/step) | Variable temporal model (5 min → 4 hour adaptive) | **Prophet** (adaptive) |
| **Influence Model** | None (LLM decides) | Explicit formula: P(i→j) = influence * trust * emotion * msg_strength | **Prophet** (predictable) |

---

## 5. Diffusion & Propagation

| Feature | OASIS | Prophet | Notes |
|---------|-------|---------|-------|
| **Diffusion Model** | Emergent (no math model) | Mathematical cascade equation | **Prophet** |
| **Content Exposure** | RecSys (TwHIN-BERT, HotScore) | RecSys-inspired feed ranking (5 weights) | OASIS is more platform-specific |
| **Cascade Detection** | None (post-hoc analysis) | Automatic: Viral, Polarization, Echo Chamber, Collapse, Slow Adoption | **Prophet** |
| **Negative Cascade** | LLM self-decides | Explicit: P_neg = skepticism * controversy * influencer_effect | **Prophet** |
| **Expert Intervention** | ManualAction (manual injection) | Expert Agent type + Tier 3 LLM analysis | **Prophet** |
| **Monte Carlo** | Not built-in | N-run probability analysis (viral_probability, p5/p50/p95) | **Prophet** |
| **Community Structure** | Follow-graph (no explicit communities) | 5 typed communities + CommunityOrchestrator | **Prophet** |
| **Cross-community** | Through follow edges | Explicit bridge propagator (trust_factor=0.6) | **Prophet** |

---

## 6. Cost & Performance

| Metric | OASIS | Prophet | Advantage |
|--------|-------|---------|-----------|
| **LLM Cost / 1000 agents / step** | ~$2-5 (all LLM) | ~$0.10-0.50 (90% SLM) | **Prophet 10-50x cheaper** |
| **1000 agents step time** | ~10-60s (API latency) | <2s (local SLM) | **Prophet 5-30x faster** |
| **GPU Requirement** | None (cloud API) | Optional (Ollama CPU/GPU) | Tie |
| **Max Agents (tested)** | 1,000,000 (claimed, 27x A100) | 200 (E2E verified) | OASIS (scale) |
| **Validation** | Twitter15/16 (NRMSE ~30%) | Not yet validated | **OASIS** |

---

## 7. Features OASIS Has That Prophet Lacks

| Feature | OASIS Implementation | Prophet Status | Priority |
|---------|---------------------|----------------|----------|
| **Platform Fidelity** | Twitter + Reddit exact simulation | Platform-agnostic | LOW (by design) |
| **23 SNS Actions** | sign_up, repost, follow, mute, search, trending, etc. | 12 marketing-focused actions | LOW |
| **Group Chat** | create_group, join, send, listen | Not implemented | MED |
| **Content Moderation** | report_post action | Not implemented | LOW |
| **Interview Action** | Agent interrogation API | Not implemented | MED |
| **TwHIN-BERT RecSys** | Real Twitter recommendation model | Weighted formula (simpler) | MED |
| **Neo4j Integration** | Graph database for relationships | NetworkX in-memory | MED |
| **Scalable Inference** | vLLM distributed inference | Ollama single-node | HIGH |
| **1M Agent Scale** | Tested (with 27 A100s) | ~200 agents tested | HIGH |
| **Data Validation** | Twitter15/16 NRMSE 30% | Not validated | HIGH |
| **Sentence Transformers** | HuggingFace embeddings | Ollama embeddings | LOW |

---

## 8. Features Prophet Has That OASIS Lacks

| Feature | Prophet Implementation | OASIS Status |
|---------|----------------------|--------------|
| **3-Tier Cost Control** | SLM 80% / Heuristic 10% / LLM 10% | All agents use LLM (100%) |
| **Cascade Detection** | 5 auto-detected patterns | None (manual analysis) |
| **Marketing Metrics** | viral_probability, adoption_rate, sentiment | None |
| **Community Orchestrator** | 3-Phase parallel execution | Flat agent loop |
| **Explicit Emotion Model** | 4-dim vector per agent | Implicit in LLM |
| **Explicit Personality** | 5-dim numeric vector | Text profile |
| **Network Science** | WS + BA hybrid with validation | Random follow (P=0.2) |
| **Real-time UI** | React 18 + Cytoscape.js + WebSocket | No frontend |
| **REST API** | 30 endpoints + Swagger | Python script only |
| **SLM/LLM Slider** | User adjusts ratio at runtime | Fixed (all LLM) |
| **Personality Drift** | Agents evolve over simulation | Static profiles |
| **Monte Carlo** | N-run probability analysis | Not built-in |
| **Dark-first Design** | Geist + Instrument Serif + Tailwind | No UI |
| **Pencil Integration** | MCP-connected design system | None |
| **Docker Deployment** | 5-service Docker Compose | pip install only |
| **Settings UI** | LLM config from browser | Code-only config |

---

## 9. Recommended Enhancements for Prophet

Based on OASIS's strengths, Prophet should consider:

### HIGH Priority

| Enhancement | Why | Effort |
|-------------|-----|--------|
| **Scale Testing (10K+ agents)** | OASIS claims 1M. Prophet tested 200. Need to prove 10K works. | MED |
| **Validation against real data** | OASIS validated with Twitter15/16. Prophet has no validation. | HIGH |
| **vLLM / batch inference** | Ollama single-node is bottleneck at scale. | MED |

### MEDIUM Priority

| Enhancement | Why | Effort |
|-------------|-----|--------|
| **Group Chat / Multi-agent discussion** | OASIS has this. Useful for policy simulation. | MED |
| **Interview Action** | Query agents mid-simulation. Research tool. | LOW |
| **TwHIN-BERT or similar RecSys** | More realistic than weighted formula. | MED |
| **Neo4j or graph DB option** | NetworkX in-memory limits scale. | HIGH |

### LOW Priority (by design choice)

| Enhancement | Why | Effort |
|-------------|-----|--------|
| Platform-specific simulation | Prophet is intentionally platform-agnostic. | — |
| 23 SNS actions | 12 marketing actions are sufficient. | — |
| Content moderation | Not core to marketing simulation. | — |

---

## 10. Conclusion

**Prophet is better than OASIS at:**
- Cost efficiency (10-50x cheaper per simulation)
- Predictability (mathematical models vs emergent-only)
- Marketing analytics (cascade detection, Monte Carlo, KPIs)
- User experience (full-stack web app vs CLI scripts)
- Community modeling (typed communities, bridge propagation)
- Agent cognitive model (6-layer vs single LLM call)

**OASIS is better than Prophet at:**
- Scale (1M agents vs 200 tested)
- Validation (real-world data comparison)
- Platform fidelity (Twitter/Reddit exact simulation)
- Action diversity (23 vs 12 actions)
- Distributed inference (vLLM cluster)

**Bottom line:** Prophet is a more sophisticated simulation engine for marketing use cases. OASIS is a broader social media simulator validated at scale. Prophet's biggest gaps are scale testing and real-world validation, not architecture or features.
