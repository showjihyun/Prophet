"""Engine Controller — user-adjustable SLM/LLM ratio at runtime.
SPEC: docs/spec/05_LLM_SPEC.md#71-user-engine-control-slmllm-ratio
"""
from __future__ import annotations

from app.config import settings as _settings
from app.llm.schema import TierDistribution, EngineImpactReport

# Average cost per Tier 3 LLM call (USD)
_AVG_COST_PER_TIER3_CALL = _settings.llm_avg_cost_per_tier3_call

# Tier 1 SLM latency per agent (ms)
_TIER1_LATENCY_MS = _settings.llm_tier1_latency_ms

# Tier 3 LLM latency per agent (ms)
_TIER3_LATENCY_MS = _settings.llm_tier3_latency_ms


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b at parameter t in [0, 1]."""
    return a + (b - a) * t


class EngineController:
    """Prophet-unique feature: user adjusts SLM/LLM ratio at runtime.

    SPEC: docs/spec/05_LLM_SPEC.md#71-user-engine-control-slmllm-ratio

    Not available in OASIS.

    Ratio → Tier mapping (linear interpolation between anchor points):
        ratio=0.0  → Tier1=95%, Tier2=4%, Tier3=1%   (lowest cost)
        ratio=0.5  → Tier1=80%, Tier2=10%, Tier3=10%  (recommended default)
        ratio=1.0  → Tier1=50%, Tier2=20%, Tier3=30%  (highest quality)
    """

    # Anchor points: (ratio, tier1_pct, tier2_pct, tier3_pct)
    _ANCHORS = [
        (0.0, 0.95, 0.04, 0.01),
        (0.5, 0.80, 0.10, 0.10),
        (1.0, 0.50, 0.20, 0.30),
    ]

    def _interpolate_percentages(
        self, ratio: float
    ) -> tuple[float, float, float]:
        """Linearly interpolate tier percentages from anchor points."""
        ratio = max(0.0, min(1.0, ratio))

        # Find which segment we're in
        if ratio <= 0.5:
            t = ratio / 0.5  # 0..1 within first segment
            p1 = self._ANCHORS[0]
            p2 = self._ANCHORS[1]
        else:
            t = (ratio - 0.5) / 0.5  # 0..1 within second segment
            p1 = self._ANCHORS[1]
            p2 = self._ANCHORS[2]

        tier1_pct = _lerp(p1[1], p2[1], t)
        tier2_pct = _lerp(p1[2], p2[2], t)
        tier3_pct = _lerp(p1[3], p2[3], t)

        return tier1_pct, tier2_pct, tier3_pct

    def compute_tier_distribution(
        self,
        total_agents: int,
        slm_llm_ratio: float,
        budget_usd: float | None = None,
        tier1_model: str | None = None,
        tier3_model: str | None = None,
    ) -> TierDistribution:
        """Map user preference to concrete tier assignment.

        SPEC: docs/spec/05_LLM_SPEC.md#71-user-engine-control-slmllm-ratio

        If budget_usd provided, auto-calculates max feasible ratio.
        """
        ratio = max(0.0, min(1.0, slm_llm_ratio))

        # Budget constraint: reduce ratio if estimated cost exceeds budget
        if budget_usd is not None and budget_usd >= 0:
            # Iteratively reduce ratio until cost is within budget
            while ratio > 0.0:
                _, _, t3_pct = self._interpolate_percentages(ratio)
                tier3_count = max(0, round(total_agents * t3_pct))
                estimated_cost = tier3_count * _AVG_COST_PER_TIER3_CALL
                if estimated_cost <= budget_usd:
                    break
                ratio = max(0.0, ratio - 0.05)

        tier1_pct, tier2_pct, tier3_pct = self._interpolate_percentages(ratio)

        tier3_count = max(0, round(total_agents * tier3_pct))
        tier2_count = max(0, round(total_agents * tier2_pct))
        tier1_count = max(0, total_agents - tier3_count - tier2_count)

        estimated_cost = tier3_count * _AVG_COST_PER_TIER3_CALL
        # Weighted average latency estimate
        if total_agents > 0:
            estimated_latency = (
                tier1_count * _TIER1_LATENCY_MS
                + tier2_count * 0.0  # Tier 2 is heuristic, near-zero
                + tier3_count * _TIER3_LATENCY_MS
            ) / total_agents
        else:
            estimated_latency = 0.0

        return TierDistribution(
            tier1_count=tier1_count,
            tier2_count=tier2_count,
            tier3_count=tier3_count,
            tier1_model=tier1_model or _settings.slm_model,
            tier3_model=tier3_model or _settings.anthropic_default_model,
            estimated_cost_per_step=round(estimated_cost, 4),
            estimated_latency_ms=round(estimated_latency, 1),
        )

    def get_impact_assessment(
        self,
        distribution: TierDistribution,
    ) -> EngineImpactReport:
        """Returns 4 indicators for user dashboard.

        SPEC: docs/spec/05_LLM_SPEC.md#71-user-engine-control-slmllm-ratio
        """
        total = distribution.tier1_count + distribution.tier2_count + distribution.tier3_count
        tier3_ratio = distribution.tier3_count / total if total > 0 else 0.0

        # Cost efficiency
        cost = distribution.estimated_cost_per_step
        cost_efficiency = f"${cost:.2f} per step"

        # Reasoning depth
        if tier3_ratio <= 0.05:
            reasoning_depth = "Quantitative Analysis"
        elif tier3_ratio <= 0.15:
            reasoning_depth = "Balanced"
        else:
            reasoning_depth = "Qualitative Analysis"

        # Simulation velocity
        latency = distribution.estimated_latency_ms
        if latency < 1000:
            simulation_velocity = f"~{latency:.0f}ms per step"
        else:
            simulation_velocity = f"~{latency / 1000:.1f}s per step"

        # Prediction type
        if tier3_ratio <= 0.05:
            prediction_type = "Quantitative"
        elif tier3_ratio <= 0.15:
            prediction_type = "Hybrid"
        else:
            prediction_type = "Qualitative"

        return EngineImpactReport(
            cost_efficiency=cost_efficiency,
            reasoning_depth=reasoning_depth,
            simulation_velocity=simulation_velocity,
            prediction_type=prediction_type,
        )


__all__ = ["EngineController"]
