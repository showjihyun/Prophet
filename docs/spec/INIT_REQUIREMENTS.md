# INIT REQUIREMENTS — 원본 기획서 통합 SPEC
Version: 0.1.0 | Status: BASELINE | Date: 2026-03-27

> 이 문서는 `docs/init/` 의 5개 원본 기획 문서를 **누락 없이** 정제하여 통합한 것입니다.
> 모든 SPEC 문서(`01~09`)는 이 문서를 원천(source of truth)으로 삼아 작성되었으며,
> 구현 과정에서 원본 의도와 불일치가 발생하면 이 문서를 기준으로 판단합니다.

---

## 전략 결정 (Post-analysis)

> Prophet의 자체 **6-Layer 엔진 + Viral Cascade Algorithm**을 유지하되,
> OASIS의 **RecSys 개념**과 **시간 모델**을 차용하는 **하이브리드 전략**이 최적.

| 구분 | Prophet 고유 (유지) | OASIS 차용 |
|------|-------------------|-----------|
| **엔진** | 6-Layer Agent Architecture | — |
| **확산** | Viral Cascade Algorithm | — |
| **비용** | 3-Tier LLM 비용 제어 | — |
| **감지** | Cascade Detection (수학적 예측) | — |
| **메트릭** | 마케팅 KPI (viral_probability 등) | — |
| **노출** | — | RecSys-style Feed Ranking |
| **시간** | — | Variable-duration Temporal Model |
| **추론** | — | SLM 기반 Mass Inference (Phi-4/Llama-3/Gemma-2B) |
| **액션** | 6종 → 12종 확장 | +SEARCH, SAVE, REPOST, FOLLOW, UNFOLLOW, MUTE |
| **사용자 제어** | SLM/LLM 비율 슬라이더 (Prophet 고유 UX) | — |
| **예산 추천** | 예산 입력 → 자동 엔진 비율 추천 | — |

**핵심 경쟁력:** 마케팅 SaaS 포지셔닝에서 비용 제어(3-Tier), 수학적 예측(Cascade Detection), 마케팅 메트릭이 OASIS에는 없는 Prophet 고유의 강점.

**추가 결정 (2026-03-27):**
- Tier 1을 Rule Engine에서 **SLM (Mass SLM)**으로 교체 — 모든 에이전트가 언어적 판단 수행
- Action Space를 6종에서 **12종**으로 확장 — SNS 행동 현실성 향상
- 사용자 **SLM/LLM 비율 슬라이더** + **예산 기반 자동 추천** 추가 — Prophet 고유 UX

---

## 원본 문서 매핑

| # | 원본 파일 | 이 문서의 섹션 |
|---|---------|-------------|
| 1 | `prophet_요구사항 초안.txt` | §1–§7 전체 PRD |
| 2 | `마케팅 사례 적용.txt` | §8 마케팅 시나리오 |
| 3 | `MCASP의 현실성을 결정하는 핵심은 Agent Influence Network 생성 알고리즘.txt` | §9 네트워크 생성 알고리즘 |
| 4 | `Social Diffusion Engine (Viral Cascade Algorithm).txt` | §10 확산 엔진 |
| 5 | `차세대 Agent Memory + Behavior Architecture 모델 설계.txt` | §11 에이전트 아키텍처 |
| 6 | `OASIS 분석.txt` | §8.15 경쟁 환경 (보강) |
| 7 | `에이전트 엔진 및 확산 엔진 비교 분석.md` | 전략 결정 섹션 + §12 핵심 기술 |
| 8 | `Prophet의 3-Tier Viral Cascade 설계 보완 설계안.txt` | 전략 결정 섹션 (SLM Tier) |
| 9 | `OASIS 에 Prophet 결합 전략.txt` | 전략 결정 섹션 (하이브리드 근거) |

---

# Part I — 통합 PRD

*원본: `prophet_요구사항 초안.txt`*

---

## §1. 프로젝트 개요

**프로젝트 명:** Multi-Community Agent Simulation Platform (MCASP)
**코드 네임:** Prophet
**목표:** 범용 Agent 기반 시뮬레이터 구축

- Multi-community 구조, GraphRAG 관계 시각화, Timeline 기반 분석
- 실시간 개입, Scenario 반복 실험, Emergent Behavior 탐지
- On-Premise + External LLM 지원, 하네스 엔지니어링 기반 모듈화

---

## §2. 사용자 / 타겟

| 사용자 | 목적 |
|--------|------|
| 연구자 / 데이터 과학자 | 사회 행동 분석, Emergent Behavior 연구 |
| 마케팅 / 정책 기획자 | 캠페인/정책 시뮬레이션, 전략 효과 분석 |
| 교육자 | Agent 기반 실험 학습 |
| 개발자 / 엔지니어 | Agent/Scenario/LLM 모듈 테스트 및 확장 |

---

## §3. 핵심 기능

### §3.1 시뮬레이션 엔진

- Step 단위 실행
- Agent 행동 모델: Personality, Emotion, Memory, Expert Insight
- Cross-community Interaction
- Emergent Behavior Detection

### §3.2 Multi-Community 구조 (원본 PRD 기준 3 커뮤니티)

| Community | Agent 수 | 특징 |
|-----------|----------|------|
| A | 100 | 소규모, 초기 실험용 |
| B | 500 | 대규모, 평균적 사회 행동 |
| C | 30 | 전문가/연구자 Agent, 심층 분석 제공 |

> **참고:** 마케팅 시나리오(§8)에서는 5 커뮤니티(A~E, 총 1000 Agent)로 확장됨.
> 커뮤니티 수와 Agent 수는 설정 가능해야 함.

- Community별 Metric, GraphRAG Edge Weight 반영

### §3.3 GraphRAG 시각화

- **Node:** Agent / Event / Expert
- **Node Color:** Community / Emotion
- **Node Size:** 영향력
- **Edge Weight:** Interaction / Influence
- **Interactive Hover:** Memory / Expert Insight

### §3.4 Timeline / Metric Dashboard

- Step별 Metric
- Emergent Behavior 표시
- 실시간 개입: Pause → Agent 수정 → Resume

### §3.5 실시간 개입

- Agent Personality / Emotion / Community 수정
- Scenario Step 재실행 가능

---

## §4. LLM 기능 통합

| 기능 | 설명 |
|------|------|
| On-Premise + External LLM | HuggingFace/LLaMA + OpenAI/Claude/Gemini API |
| Agent별 LLM 선택 | 일부 Agent → External, 나머지 → On-Premise |
| Prompt Context 구성 | Agent Memory + Personality + Community 상태 |
| LLM 결과 캐싱 | 반복 시나리오 최적화 |
| Hybrid Mode | 일부 Step On-Premise, 일부 Step External |
| Quota & Rate Management | External LLM 안정적 호출 |

> **구현 결정:** On-Premise = Ollama (로컬), External = Claude API + OpenAI API.
> Gemini 는 초기 구현 범위에서 제외 (추후 Adapter 추가 가능).

---

## §5. 하네스 기능 (F18–F30)

| ID | 기능 | 설명 |
|----|------|------|
| F18 | Unit Test Hooks | Agent, Community, Engine 단위 테스트 가능 |
| F19 | Mock Environment | 실제 시나리오 없이 행동 테스트 |
| F20 | Event / Agent Replay | Step별 Replay 가능 |
| F21 | Metric Logging API | Step별 Metric/Agent 행동/LLM 기록 |
| F22 | Module Hot-Swap | Agent/Community/LLM 모듈 교체 가능 |
| F23 | Scenario Comparison | 시나리오 간 Metric/Behavior 비교 |
| F24 | Simulation Sandbox Mode | 안전한 테스트 환경 제공 |
| F25 | Debug Visualization | Agent 의사결정 + LLM Prompt/Response 시각화 |
| F26 | API / Integration Hooks | 외부 데이터/LLM/Event Stream 연결 |
| F27 | Performance Monitor | CPU/GPU/Memory 모니터링 |
| F28 | Failure Recovery | Agent/LLM 호출 실패 시 Retry/Fallback |
| F29 | Configurable Agent Behavior | Personality/Emotion/Memory 동적 수정 |
| F30 | Hybrid Execution Mode | On-Premise + External LLM Step 단위 혼합 |

---

## §6. 비기능 요구사항

| ID | 요구사항 | 설명 |
|----|---------|------|
| NF01 | 성능 | 1000+ Agent, Step 실행 1초 이하 |
| NF02 | 확장성 | Agent/Community/Scenario/LLM 모듈 교체 가능 |
| NF03 | UI/UX | Web 기반 Dashboard |
| NF04 | 실시간성 | Agent/Scenario 변경 → 즉시 시뮬레이션 반영 |
| NF05 | 테스트 용이성 | 하네스 단위 테스트 및 Mock 환경 지원 |
| NF06 | 범용성 | 마케팅, 정책, 교육 등 다양한 시나리오 적용 |
| NF07 | 신뢰성 | 실패/재시도/Failover 처리 |
| NF08 | 보안 (선택) | On-Premise 환경 접근 권한, API Key 관리 |

> **구현 결정:** NF03 — Streamlit/Dash 대신 **React 18 + FastAPI** 채택.

---

## §7. UI 요구사항

- **Graph Panel:** Agent/Community + Emergent Cluster
- **Timeline Panel:** Step Metric + Emergent Behavior
- **Control Panel:** Play / Pause / Step / Scenario
- **Agent Detail Hover:** Memory, Expert Insight, Personality/Emotion
- **Community Filters:** 특정 Community Highlight
- **Interactive Modification:** Personality, Emotion, Community 변경
- **LLM Dashboard:** Prompt Preview, Quota, Step별 Response

---

# Part II — 마케팅 캠페인 확산 시나리오

*원본: `마케팅 사례 적용.txt`*

---

## §8. Marketing Campaign Diffusion Simulation

### §8.1 목적

기업 또는 기관이 마케팅 캠페인, 제품 출시, 메시지 전략이 사회 집단에서 어떻게 확산되는지 **사전에 시뮬레이션**하는 플랫폼.

- 기존 마케팅 툴 → 단순 SNS analytics
- MCASP → **가상 사회에서 캠페인을 먼저 실행**

### §8.2 Multi-Community 구성 (마케팅 시나리오)

| Community | Agent 수 | 특징 |
|-----------|----------|------|
| A | 100 | 얼리어답터 |
| B | 500 | 일반 소비자 |
| C | 200 | 회의적인 소비자 |
| D | 30 | 전문가/리뷰어 |
| E | 170 | 인플루언서 네트워크 |

**총 Agent: 1000개**

### §8.3 Agent 행동 모델

#### Personality

```
openness
skepticism
trend_following
brand_loyalty
social_influence
```

#### Emotional State

```
interest
trust
skepticism
excitement
```

#### Memory

Agent는 다음을 기억:
- 광고 exposure
- 친구 추천
- 전문가 리뷰
- 과거 브랜드 경험

### §8.4 캠페인 이벤트 (Campaign Input)

기업은 시뮬레이션 시작 전에 이벤트를 설정:

```
campaign_name: "New Smartphone Launch"
budget: 5M
channels:
  - SNS
  - Influencer
  - Online Ads
message: "AI camera phone"
```

### §8.5 시뮬레이션 진행 단계

| Step | 내용 | 행동 |
|------|------|------|
| 1 | 기업 캠페인 시작 | SNS exposure, ad exposure, influencer post |
| 2 | Agent 반응 | ignore, like, share, comment, purchase intent |
| 3 | Agent간 영향 | friend recommendation, discussion, argument, community diffusion |
| 4 | 전문가 Agent 분석 | tech reviewer, market analyst, researcher → LLM 기반 분석 |

전문가 분석 예:
- "Camera quality appears competitive"
- "Battery life may be weak"

이 분석은 다시 Agent 행동에 영향.

### §8.6 확산 모델

확산 결정 요소:
```
influence_score
trust_network
community_structure
emotion_state
```

확산 함수:
```
share_probability = influence * trust * excitement
```

### §8.7 Emergent Behavior

| 현상 | 패턴 |
|------|------|
| Viral Explosion | Influencer → Early adopter → General consumers |
| Backlash | Expert negative review → skepticism 증가 → campaign failure |
| Polarization | Community A: positive, Community C: negative |

### §8.8 GraphRAG 시각화

**Node:** Agent, Community, Campaign Event, Expert Opinion
**Edge:** influence, discussion, trust, information flow

그래프 예:
```
Influencer → Community A
Community A → Community B
Expert review → Community C
```

### §8.9 Timeline 분석

```
t1: campaign launch
t3: influencer share
t5: viral growth
t8: expert criticism
t12: diffusion slowdown
```

Dashboard 항목:
- adoption rate
- sentiment
- community adoption
- viral clusters

### §8.10 기업에게 제공되는 결과

| 질문 | 측정값 |
|------|--------|
| 캠페인이 viral 되는가? | viral probability |
| 어떤 community가 핵심인가? | key influencer cluster |
| 전문가 의견 영향 | expert opinion sensitivity |
| 메시지 변경 효과 | AI camera vs battery life messaging |

### §8.11 실시간 개입 (마케팅 시나리오)

사용자는 시뮬레이션 중 다음 변경 가능:
- campaign message 변경
- budget 증가
- influencer 추가
- negative PR 대응

### §8.12 반복 시뮬레이션 (Monte Carlo)

```
scenario run: 100
```

결과:
- success probability
- diffusion speed
- community adoption

### §8.13 SaaS 모델

| Tier | Agent 수 | 기능 |
|------|----------|------|
| Starter | 200 | 기본 시뮬레이션 |
| Pro | 1000 | Multi-community |
| Enterprise | Custom | Custom dataset, On-Premise, LLM integration |

### §8.14 고객 타겟

| 고객 | 사용 |
|------|------|
| 브랜드 | 제품 출시 |
| 광고회사 | 캠페인 전략 |
| 정부 | 정책 홍보 |
| 게임회사 | 커뮤니티 반응 |
| 영화사 | 마케팅 전략 |

### §8.15 경쟁 환경

유사 플랫폼:
- **Miro Fish** — 시각적 소셜 그래프 탐색
- **OASIS** — 대규모 사회 시뮬레이션

**MCASP 차별점:** 마케팅용으로 만든 플랫폼은 거의 없음. SaaS 사업 가능성 충분.

---

# Part III — Agent Influence Network 생성 알고리즘

*원본: `MCASP의 현실성을 결정하는 핵심은 Agent Influence Network 생성 알고리즘.txt`*

---

## §9. Hybrid Network Generator

### §9.1 현실 SNS 네트워크 특징 3가지

#### 특징 1 — 소수의 슈퍼 인플루언서 (Power-law distribution)

```
followers distribution
  90% : < 100 followers
  9%  : 100 ~ 10k
  1%  : > 100k
```

#### 특징 2 — Community Cluster

```
gaming community, tech community, fashion community
→ clustered network
```

#### 특징 3 — Short path (Small-world)

```
average path length ≈ 4~6
```

### §9.2 참고 네트워크 이론

| 이론 | 적용 |
|------|------|
| Scale-Free Network | 인플루언서 power-law 분포 |
| Small-World Network | 커뮤니티 내부 높은 클러스터링 + 짧은 경로 |
| Preferential Attachment | 인기 있는 노드에 더 연결되는 구조 |

이 3가지를 **Hybrid Network Generator**로 결합.

### §9.3 Hybrid Network Architecture

```
Global Network
   ├─ Community A
   ├─ Community B
   ├─ Community C
   └─ Influencer Layer
```

| Layer | 역할 |
|-------|------|
| Influencer | diffusion accelerator |
| Community | local interaction |
| Cross-community | bridge |

### §9.4 Network Generation Algorithm — 5단계

```
1. create communities
2. generate internal network
3. create influencer layer
4. add cross-community edges
5. compute trust weight
```

### §9.5 Community Network 생성 (Watts-Strogatz)

```
모델: Watts-Strogatz small world
파라미터:
  N = community size
  K = neighbors (default: 6)
  p = rewiring probability (default: 0.1)
```

```python
import networkx as nx
G = nx.watts_strogatz_graph(n=100, k=6, p=0.1)
```

효과: 높은 clustering + 짧은 path

### §9.6 Influencer Layer 생성 (Barabási-Albert)

```
모델: Barabasi-Albert preferential attachment
```

```python
G = nx.barabasi_albert_graph(n=1000, m=3)
```

특징: few nodes have massive influence

### §9.7 Hybrid Merge

```
Community graph + Influencer graph → Hierarchical network
```

### §9.8 Cross-Community Edge 생성

```
생성 방법: random bridge edges
확률: P_cross = 0.02
```

예: tech influencer → gaming community

### §9.9 Edge Weight 계산

```
W_ij = trust_ij * interaction_freq
```

#### Trust 모델

```
trust_ij = similarity(personality) + interaction_history
```

#### Personality Similarity

```
P_i = [interest_tech, interest_fashion, skepticism, trend_following]
similarity = cosine(P_i, P_j)
```

#### Interaction Frequency

```
interaction_freq = (activity_i + activity_j) / 2
```

### §9.10 Influence Score

```
I_i = followers * credibility * activity
정규화: 0 ~ 1
```

### §9.11 Final Diffusion Weight

```
P(i → j) = I_i * W_ij * emotion_factor
```

### §9.12 Network Metrics 검증 기준

| Metric | 유효 범위 |
|--------|----------|
| Degree distribution | power law |
| Clustering coefficient | 0.2 ~ 0.6 |
| Average path length | 4 ~ 6 |

### §9.13 Python Prototype (원본 코드)

```python
import networkx as nx

def generate_social_network(
    total_agents=1000,
    community_sizes=[100,500,200,200]
):
    G = nx.Graph()
    start = 0
    communities = []

    for size in community_sizes:
        sub = nx.watts_strogatz_graph(size, 6, 0.1)
        mapping = {i:i+start for i in range(size)}
        sub = nx.relabel_nodes(sub, mapping)
        G = nx.compose(G, sub)
        communities.append(list(mapping.values()))
        start += size

    influencers = nx.barabasi_albert_graph(total_agents, 3)
    G = nx.compose(G, influencers)

    return G
```

### §9.14 Dynamic Network Evolution

SNS 네트워크는 고정이 아님:
- follow / unfollow / community shift
- trust drop → edge weight 감소
- campaign viral → new edges
- 시간 변화: G(t)

### §9.15 Emergent Influence 예시

- micro influencer → viral cascade
- expert criticism → collapse

---

# Part IV — Social Diffusion Engine (Viral Cascade Algorithm)

*원본: `Social Diffusion Engine (Viral Cascade Algorithm).txt`*

---

## §10. Social Diffusion Engine

### §10.1 목표 — 4가지 현상 재현

| 현상 | 설명 |
|------|------|
| Viral Cascade | 콘텐츠가 폭발적으로 확산 |
| Slow Adoption | 천천히 확산 |
| Polarization | 커뮤니티 간 의견 충돌 |
| Collapse | 부정적 리뷰로 확산 중단 |

### §10.2 참고 연구

- Viral Marketing for the Real World
- Independent Cascade Model
- Linear Threshold Model
- MCASP는 이들을 **LLM 기반 Agent와 결합한 Hybrid Diffusion Engine**

### §10.3 Diffusion Engine 파이프라인

```
Content Event
      │
      ▼
Exposure Model
      │
      ▼
Cognitive Evaluation
      │
      ▼
Behavior Decision
      │
      ▼
Social Propagation
      │
      ▼
Cascade Detection
```

### §10.4 Agent State

```
A_i = { emotion, belief, exposure_history, social_links }

Emotion vector:
  E_i = [interest, trust, skepticism, excitement]

Belief:
  B_i = [-1, 1]   (-1 = strong negative, +1 = strong positive)
```

### §10.5 Exposure Model

콘텐츠 접촉 경로:
- social feed
- expert review
- advertisement
- community discussion

```
P_exposure(i) = Σ influence_j * W_ij

feed ranking:
  rank_score = recency + social_weight + relevance
```

### §10.6 Cognitive Evaluation

```
S_i = interest + trust - skepticism + community_bias
memory_weight = Σ relevant_memory
evaluation_i = S_i + memory_weight
```

### §10.7 Behavior Decision

Agent 행동 종류:
```
ignore, view, like, comment, share, adopt
```

확률:
```
P(action) = softmax(evaluation_i + social_pressure)
social_pressure = Σ W_ij * action_j
```

### §10.8 Propagation Model

```
P(i → j) = influence_i * trust_ij * emotional_factor * message_strength

emotion_factor = excitement - skepticism

message_strength:
  novelty + controversy + utility
```

### §10.9 Cascade Growth Model

```
확산 수: N(t)
확산 속도: R(t) = dN/dt
viral 조건: R(t) > threshold
cascade size: C = total adoption
```

### §10.10 Community Interaction

```
Community bias: bias_k
확산 수정: P(i → j) = P(i → j) * bias_k
community conflict: sentiment_variance → polarization
```

### §10.11 Expert Intervention

Expert agent 유형:
- reviewer
- scientist
- journalist

LLM reasoning prompt 예:
```
"Analyze product quality based on current feedback"
```

Expert opinion: O_k
Agent 감정 수정:
```
E_i(t+1) = E_i(t) + α * O_k
```

### §10.12 Negative Cascade

부정 확산 (예: battery explosion rumor):
```
P_neg(i → j) = skepticism * controversy * influencer_effect
```

### §10.13 Emergent Behavior Detection

| 현상 | 감지 조건 |
|------|----------|
| Viral | cascade_size > threshold |
| Polarization | sentiment_variance > threshold |
| Echo Chamber | community_internal_links >> external_links |

### §10.14 Diffusion Equation

```
dA/dt = β * influence * trust * emotion * network_structure

Cascade growth:
  A(t+1) = A(t) + diffusion_rate - decay
```

### §10.15 Monte Carlo Simulation

```
동일 캠페인 100~1000 run
결과: viral probability, expected reach, community adoption
```

### §10.16 Simulation Loop

```python
for t in timeline:
    exposure()
    cognition()
    decision()
    propagate()
    update_emotion()
    detect_cascade()
```

### §10.17 MCASP vs 기존 확산 모델

| 모델 | 특징 |
|------|------|
| Independent Cascade | 확률 확산 |
| Linear Threshold | 임계치 확산 |
| **MCASP** | **LLM cognition + emotion dynamics + community bias + network diffusion** |

핵심 결합:
```
Network Science + Behavioral Economics + LLM Cognition
= AI 기반 Social Simulation Diffusion Model
```

### §10.18 Python Prototype 구조

```
diffusion/
   exposure_model.py
   cognition_model.py
   propagation_model.py
   cascade_detector.py
   sentiment_model.py
```

Propagation 예:
```python
def propagate(agent_i, agent_j):
    influence = agent_i.influence
    trust = trust_matrix[i][j]
    emotion = agent_i.emotion["excitement"] - agent_j.emotion["skepticism"]
    p = influence * trust * emotion
    return random.random() < p
```

### §10.19 유사 연구 비교

- NetLogo — 성숙한 ABM 프레임워크, LLM/GraphRAG 없음
- Stanford Smallville — 현실적 LLM 에이전트, 확산 모델 없음

**MCASP:** LLM + GraphRAG + Viral Diffusion 결합 시스템은 거의 없음.

---

# Part V — 차세대 Agent Memory + Behavior Architecture

*원본: `차세대 Agent Memory + Behavior Architecture 모델 설계.txt`*

---

## §11. Agent Architecture

### §11.1 설계 목표

- 1000+ Agent 스케일
- Multi-community 사회 모델
- LLM 비용 최소화
- Emergent behavior 생성
- GraphRAG 기반 기억

참고 연구: "Generative Agents: Interactive Simulacra of Human Behavior" (Stanford)

### §11.2 기존 Stanford Generative Agent 구조와 문제점

```
Stanford 구조:
  Observation → Memory Stream → Reflection → Planning → Action

문제점:
  1. LLM 호출이 너무 많음
  2. 사회 네트워크 모델 없음
  3. 영향력 모델 없음
  4. 확산 모델 없음
```

### §11.3 MCASP Agent Architecture — 6 Layer

```
Perception Layer
        ↓
Memory Layer (GraphRAG)
        ↓
Emotion & Cognition Layer
        ↓
Decision Layer
        ↓
Action Layer
        ↓
Social Influence Layer
```

### §11.4 Agent Memory — 3가지 타입

#### Episodic Memory (경험 기억)

```
M_episode = { event, timestamp, emotional_weight }
예: "t=12 influencer mentioned product"
    "t=15 friend recommended phone"
```

#### Semantic Memory (지식 기억)

```
M_semantic = { concept, belief_strength }
예: "brand reputation", "product features"
```

#### Social Memory (관계 기억)

```
M_social = { agent_id, trust_score, influence_weight }
```

### §11.5 GraphRAG Memory

Memory는 그래프로 저장 = **Social Knowledge Graph**

**Node:** agent, event, belief, community
**Edge:** experienced, trusts, discussed, influenced

예:
```
Agent_24 → experienced → campaign_ad
Agent_24 → trusts → Agent_8
Agent_8 → influenced → Agent_24
```

### §11.6 Memory Retrieval

Agent 행동 전에 Memory 검색:

```
Score = α * recency
      + β * relevance
      + γ * emotion
      + δ * social_weight

TopK = 10
```

### §11.7 Emotion Model

```
E_i = [interest, trust, skepticism, excitement]

업데이트:
  E_i(t+1) = E_i(t) + social_signal + media_signal + expert_signal - decay
```

### §11.8 Cognition Layer — Hybrid Cognition

Stanford 모델: 전부 LLM 사용
MCASP: **Rule Engine + Influence Model + LLM reasoning**

#### Rule Engine (빠른 판단)

```
if trust(friend) > 0.7 → share_probability += 0.2
```

#### Influence Model

```
social_pressure = Σ influence_j * trust_ij
```

#### LLM Reasoning (복잡한 판단)

```
예: "Should I recommend this product?"
LLM 호출: 10~20% agent only
```

### §11.9 Decision Model

행동:
```
ignore, like, share, comment, purchase
```

확률:
```
P(action) = softmax(interest + social_pressure + emotion + memory_weight)
```

### §11.10 Social Influence Model

```
그래프: G(V, E)
Edge weight: W_ij = trust_ij * interaction_freq
확산: P(i → j) = influence_i * trust_ij * emotion_factor
```

### §11.11 Behavior Loop (Agent 행동 루프)

```
1. perceive environment
2. retrieve memory
3. update emotion
4. compute social pressure
5. run cognition
6. choose action
7. update memory
```

### §11.12 Memory Reflection (Stanford reflection 개선)

조건:
```
if repeated_event > threshold
```

LLM reflection 예:
```
"I notice many friends recommending this product"
→ belief_strength++
```

### §11.13 Agent Personality Drift

시간에 따른 성격 변화:
```
P_i(t+1) = P_i(t) + learning_rate * experience
예: skeptic → adopter
```

### §11.14 Collective Behavior (집단 행동)

```
community_pressure = avg_adoption_rate
→ trend_following 영향
```

### §11.15 LLM 비용 절감 구조 — 3 Tier

```
Tier 1: Rule Engine          (80~90% agents)
Tier 2: Heuristic Reasoning  (~10% agents)
Tier 3: LLM Reasoning        (<10% agents)
```

### §11.16 1000 Agent 확장 구조

성능 전략:
```
parallel simulation
async LLM
memory caching
graph partition
```

### §11.17 Python 구조 (원본 제안)

```
agent/
   agent_core.py
   emotion_model.py
   cognition_engine.py
   memory_graph.py
   decision_model.py
   influence_model.py
```

### §11.18 Stanford vs MCASP 비교

| 요소 | Stanford | MCASP |
|------|----------|-------|
| memory | text | **graph** |
| cognition | LLM | **hybrid** |
| social network | 없음 | **있음** |
| diffusion | 없음 | **있음** |
| community | 없음 | **있음** |

---

# Part VI — 핵심 기술 요약 및 성공 기준

## §12. MCASP 성패를 좌우하는 3대 핵심 기술

```
1. Agent Memory Architecture  (GraphRAG 기반 3-type 메모리)
2. Influence Network Generation (Small-world + Scale-free + Community 결합)
3. Diffusion Model             (LLM cognition + emotion + community bias)
```

이 세 가지가 결합되면:
- 단순 SaaS가 아니라 **AI 기반 가상 사회 실험실**
- 세계적으로 거의 없는 카테고리
- 충분한 SaaS 사업 가능성

---

## §13. SPEC 문서 매핑 (이 문서 → 구현 SPEC)

| 이 문서 섹션 | 구현 SPEC | 비고 |
|-------------|----------|------|
| §3.1 시뮬레이션 엔진 | `04_SIMULATION_SPEC.md` | |
| §3.2 Multi-Community | `02_NETWORK_SPEC.md` | 5 커뮤니티 확장 반영 |
| §3.3 GraphRAG 시각화 | `07_FRONTEND_SPEC.md` | Cytoscape.js |
| §3.4 Timeline | `07_FRONTEND_SPEC.md` | Recharts |
| §3.5 실시간 개입 | `04_SIMULATION_SPEC.md`, `06_API_SPEC.md` | WebSocket |
| §4 LLM 통합 | `05_LLM_SPEC.md` | Ollama + Claude + OpenAI |
| §5 하네스 F18–F30 | `09_HARNESS_SPEC.md` | |
| §6 비기능 요구사항 | `MASTER_SPEC.md` §4 | |
| §7 UI 요구사항 | `07_FRONTEND_SPEC.md` | React 18 |
| §8 마케팅 시나리오 | `03_DIFFUSION_SPEC.md`, `04_SIMULATION_SPEC.md` | 기본 시나리오 |
| §9 네트워크 알고리즘 | `02_NETWORK_SPEC.md` | WS + BA Hybrid |
| §10 확산 엔진 | `03_DIFFUSION_SPEC.md` | |
| §11 Agent 아키텍처 | `01_AGENT_SPEC.md` | 6-Layer |
| §12 핵심 기술 | `MASTER_SPEC.md` §1 | |
