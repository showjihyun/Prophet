# 13 — Scale & Validation SPEC
Version: 0.1.0 | Status: DRAFT

---

## 1. Scale Targets (G1, G3, G11)

| Tier | Agents | Step Time | Infrastructure |
|------|--------|-----------|---------------|
| Dev | 200 | <2s | Single laptop, Ollama CPU |
| Staging | 1,000 | <5s | Single server, Ollama GPU |
| Production | 10,000 | <30s | Docker Compose, vLLM optional |
| Enterprise | 100,000+ | <5min | Distributed (future) |

### Action Batching (G11)
CommunityOrchestrator.tick() must batch agent ticks:
```python
BATCH_SIZE = 32  # process 32 agents per SLM batch call
```

### Benchmark Harness
```python
class ScaleBenchmark:
    async def run(self, agent_count: int, steps: int) -> BenchmarkResult:
        """Run simulation and measure step_time, memory_mb, throughput."""

@dataclass
class BenchmarkResult:
    agent_count: int
    steps: int
    avg_step_ms: float
    max_step_ms: float
    memory_mb: float
    throughput_agents_per_sec: float
```

---

## 2. Validation (G2)

Reference: `10_VALIDATION_SPEC.md`

Phase 1 (synthetic): Already defined.
Phase 2 (Twitter15/16): Dataset download + comparison pipeline.
Phase 3 (real marketing data): Post-SaaS launch.

---

## 3. Agent Extensions (G6, G8)

### Group Chat Action (G6)

```python
class AgentAction(str, Enum):
    ...
    GROUP_CHAT = "group_chat"    # multi-agent discussion

@dataclass
class GroupChat:
    group_id: UUID
    members: list[UUID]
    topic: str
    messages: list[GroupMessage]

@dataclass
class GroupMessage:
    agent_id: UUID
    content: str
    step: int
    sentiment: float
```

### Interview Action (G8)

```python
class AgentInterviewer:
    async def interview(
        self,
        agent: AgentState,
        question: str,
        llm_adapter: LLMAdapter,
    ) -> InterviewResponse:
        """Query an agent mid-simulation about their beliefs/decisions."""

@dataclass
class InterviewResponse:
    agent_id: UUID
    question: str
    answer: str
    belief: float
    confidence: float
    reasoning: str
```

### API Endpoints

```
POST /api/v1/simulations/{id}/group-chat    → create group discussion
GET  /api/v1/simulations/{id}/group-chat/{gid} → get messages
POST /api/v1/simulations/{id}/agents/{aid}/interview → ask agent a question
```
