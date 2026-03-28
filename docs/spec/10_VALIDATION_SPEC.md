# 10 — Validation SPEC
Version: 0.1.0 | Status: DRAFT

---

## 1. Overview

Prophet의 시뮬레이션 결과가 현실 SNS 데이터와 얼마나 정렬되는지 검증하는 방법론.
OASIS 프로젝트가 Twitter15/Twitter16 데이터셋으로 검증한 방법론을 참조하되,
Prophet의 마케팅 SaaS 포지셔닝에 맞는 추가 메트릭을 정의한다.

---

## 2. Reference: OASIS Validation Results

OASIS (CAMEL-AI) 검증 실적 (참고 기준):

| 항목 | 값 |
|------|-----|
| 데이터셋 | Twitter15 / Twitter16 (198개 실제 전파 사례, 9개 카테고리) |
| 측정 메트릭 | Scale (참여 규모), Depth (전파 깊이), Max Breadth (최대 폭) |
| 결과 | NRMSE ~30% (현실 데이터와 정렬) |
| 한계 | 시뮬레이션 Depth가 현실 대비 일관되게 낮음 |

---

## 3. Prophet Validation Metrics

### 3.1 확산 정확도 메트릭 (OASIS 참조)

| Metric | 정의 | 목표 |
|--------|------|------|
| **Scale** | 캠페인에 참여한 총 에이전트 수 | NRMSE ≤ 35% vs 실데이터 |
| **Depth** | 확산 트리의 최대 깊이 (최초 노출 → N차 전파) | NRMSE ≤ 40% |
| **Max Breadth** | 한 Step에서 가장 많이 확산된 폭 | NRMSE ≤ 35% |

### 3.2 마케팅 특화 메트릭 (Prophet 고유)

| Metric | 정의 | 검증 방법 |
|--------|------|----------|
| **Viral Probability** | Monte Carlo N회 중 바이럴 발생 비율 | 실제 캠페인 viral 여부와 비교 |
| **Adoption Curve Shape** | 시간 대비 채택률 곡선 형태 | S-curve / exponential / linear 분류 정확도 |
| **Community Segmentation** | 커뮤니티별 채택률 분포 | 실제 세그먼트별 전환율과 상관분석 |
| **Sentiment Trajectory** | 시간 대비 감성 변화 곡선 | 실제 SNS 감성분석 데이터와 비교 |
| **Expert Opinion Sensitivity** | 전문가 리뷰 투입 전후 채택률 변화 | A/B 시뮬레이션 비교 |
| **Cascade Detection Accuracy** | 자동 감지된 바이럴/폴라리제이션 이벤트 | 실제 발생 이벤트와 F1 score |

---

## 4. Validation Dataset Strategy

### Phase 1: 합성 데이터 검증 (Phase 2–4 완료 후)

- 알려진 확산 패턴 (exponential, S-curve, collapse) 을 수동 생성
- Prophet 시뮬레이션 결과가 해당 패턴을 재현하는지 확인
- 목적: 엔진 로직 검증 (데이터 정합성이 아닌 동작 정합성)

### Phase 2: 공개 데이터셋 검증

| 데이터셋 | 출처 | 용도 |
|---------|------|------|
| Twitter15 / Twitter16 | OASIS 논문 참조 | 정보 확산 Scale/Depth/Breadth 비교 |
| Reddit Submissions | Pushshift Archive | 커뮤니티별 콘텐츠 확산 패턴 |
| Weibo Rumor Dataset | 학술 공개 | 부정 캐스케이드 (Collapse) 검증 |

### Phase 3: 실제 마케팅 데이터 검증 (SaaS 이후)

- 파트너 기업의 실제 캠페인 데이터로 회고 검증
- 과거 캠페인 결과와 Prophet 시뮬레이션 결과 비교
- NDA 기반 비공개 검증

---

## 5. SLM vs Rule Engine 품질 비교 검증

Tier 1을 Rule Engine에서 SLM으로 교체한 효과를 정량화:

```python
class SLMQualityValidator:
    async def compare_tier_quality(
        self,
        simulation_config: SimulationConfig,
        n_runs: int = 10,
    ) -> TierComparisonReport:
        """
        동일 시나리오를 3가지 모드로 실행하여 비교:
            Mode A: 100% Rule Engine (기존 방식)
            Mode B: 80% SLM + 20% LLM (Prophet 2.0 기본)
            Mode C: 100% LLM (OASIS 방식, 비용 기준)

        비교 항목:
            - 최종 adoption_rate 차이
            - Emergent behavior 감지 일치율
            - Cascade 타이밍 차이
            - 비용 (Mode A=$0, B=$$, C=$$$$)
            - 행동 다양성 (entropy of action distribution)
        """

@dataclass
class TierComparisonReport:
    adoption_rate_by_mode: dict[str, float]
    emergent_event_match_rate: float   # Mode B vs Mode C
    cost_ratio: dict[str, float]       # relative to Mode C
    behavior_entropy: dict[str, float]
    recommendation: str                # "Mode B achieves 90% of Mode C quality at 10% cost"
```

---

## 6. Harness Integration

```bash
# Run validation suite
uv run pytest backend/tests/validation/ -v -m "validation"

# Compare SLM vs Rule Engine quality
uv run pytest backend/tests/validation/test_tier_comparison.py -v

# Run against Twitter15 dataset (requires data download)
uv run pytest backend/tests/validation/test_twitter15.py -v -m "external_data"
```

---

## 7. Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| VAL-01 | Synthetic exponential cascade reproduced | Curve shape matches within 10% |
| VAL-02 | Synthetic S-curve adoption reproduced | Inflection point within ±2 steps |
| VAL-03 | Collapse after negative event | Adoption drops > 20% within 3 steps |
| VAL-04 | SLM mode vs LLM mode adoption rate | Difference < 15% |
| VAL-05 | SLM mode vs LLM mode emergent event match | F1 > 0.7 |
| VAL-06 | Monte Carlo viral_probability reproducible | StdDev < 0.05 across runs |
| VAL-07 | Twitter15 Scale NRMSE (when data available) | ≤ 35% |
| VAL-08 | Twitter15 Depth NRMSE (when data available) | ≤ 40% |
