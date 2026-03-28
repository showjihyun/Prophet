"""
Auto-generated from SPEC: docs/spec/05_LLM_SPEC.md#71-user-engine-control-slmllm-ratio
SPEC Version: 0.1.1
Generated BEFORE implementation verification — tests define the contract.
"""
import pytest

from app.llm.engine_control import EngineController
from app.llm.schema import TierDistribution, EngineImpactReport


@pytest.mark.phase5
class TestComputeTierDistribution:
    """SPEC: 05_LLM_SPEC.md#71-user-engine-control-slmllm-ratio — tier mapping"""

    def test_ratio_0_all_slm(self):
        """ratio=0.0 → Tier1=95%, Tier2=4%, Tier3=1%."""
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(total_agents=1000, slm_llm_ratio=0.0)
        assert isinstance(dist, TierDistribution)
        assert dist.tier1_count == 950
        assert dist.tier2_count == 40
        assert dist.tier3_count == 10
        assert dist.tier1_count + dist.tier2_count + dist.tier3_count == 1000

    def test_ratio_0_5_balanced(self):
        """ratio=0.5 → Tier1=80%, Tier2=10%, Tier3=10%."""
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(total_agents=1000, slm_llm_ratio=0.5)
        assert dist.tier1_count == 800
        assert dist.tier2_count == 100
        assert dist.tier3_count == 100

    def test_ratio_1_max_llm(self):
        """ratio=1.0 → Tier1=50%, Tier2=20%, Tier3=30%."""
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(total_agents=1000, slm_llm_ratio=1.0)
        assert dist.tier1_count == 500
        assert dist.tier2_count == 200
        assert dist.tier3_count == 300

    def test_total_agents_preserved(self):
        """Sum of all tiers must equal total_agents."""
        ctrl = EngineController()
        for ratio in [0.0, 0.25, 0.5, 0.75, 1.0]:
            dist = ctrl.compute_tier_distribution(total_agents=100, slm_llm_ratio=ratio)
            assert dist.tier1_count + dist.tier2_count + dist.tier3_count == 100

    def test_ratio_clamped_below_zero(self):
        """Negative ratio clamped to 0.0."""
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(total_agents=100, slm_llm_ratio=-0.5)
        assert dist.tier3_count == 1  # same as ratio=0.0 for 100 agents

    def test_ratio_clamped_above_one(self):
        """Ratio > 1.0 clamped to 1.0."""
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(total_agents=100, slm_llm_ratio=1.5)
        assert dist.tier3_count == 30  # same as ratio=1.0

    def test_zero_agents(self):
        """Zero agents → all counts zero."""
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(total_agents=0, slm_llm_ratio=0.5)
        assert dist.tier1_count == 0
        assert dist.tier2_count == 0
        assert dist.tier3_count == 0

    def test_has_model_names(self):
        """Distribution includes model names."""
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(total_agents=100, slm_llm_ratio=0.5)
        assert isinstance(dist.tier1_model, str)
        assert isinstance(dist.tier3_model, str)

    def test_estimated_cost_increases_with_ratio(self):
        """Higher ratio → higher cost."""
        ctrl = EngineController()
        d_low = ctrl.compute_tier_distribution(1000, 0.0)
        d_high = ctrl.compute_tier_distribution(1000, 1.0)
        assert d_high.estimated_cost_per_step > d_low.estimated_cost_per_step

    def test_budget_constraint_reduces_ratio(self):
        """When budget is tight, ratio is reduced to fit."""
        ctrl = EngineController()
        # Unconstrained
        d_free = ctrl.compute_tier_distribution(1000, 1.0)
        # Very tight budget
        d_budget = ctrl.compute_tier_distribution(1000, 1.0, budget_usd=0.01)
        assert d_budget.tier3_count <= d_free.tier3_count

    def test_interpolation_midpoints(self):
        """ratio=0.25 should be between 0.0 and 0.5 anchor points."""
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(total_agents=1000, slm_llm_ratio=0.25)
        # Between 95% and 80% for tier1
        assert 800 <= dist.tier1_count <= 950
        # Between 1% and 10% for tier3
        assert 10 <= dist.tier3_count <= 100


@pytest.mark.phase5
class TestGetImpactAssessment:
    """SPEC: 05_LLM_SPEC.md#71-user-engine-control-slmllm-ratio — dashboard indicators"""

    def test_returns_impact_report(self):
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(1000, 0.5)
        report = ctrl.get_impact_assessment(dist)
        assert isinstance(report, EngineImpactReport)

    def test_has_all_fields(self):
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(1000, 0.5)
        report = ctrl.get_impact_assessment(dist)
        assert isinstance(report.cost_efficiency, str)
        assert isinstance(report.reasoning_depth, str)
        assert isinstance(report.simulation_velocity, str)
        assert isinstance(report.prediction_type, str)

    def test_cost_efficiency_contains_dollar(self):
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(1000, 0.5)
        report = ctrl.get_impact_assessment(dist)
        assert "$" in report.cost_efficiency

    def test_low_ratio_quantitative(self):
        """Low tier3 ratio → Quantitative prediction."""
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(1000, 0.0)
        report = ctrl.get_impact_assessment(dist)
        assert report.prediction_type == "Quantitative"

    def test_high_ratio_qualitative(self):
        """High tier3 ratio → Qualitative prediction."""
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(1000, 1.0)
        report = ctrl.get_impact_assessment(dist)
        assert report.prediction_type == "Qualitative"

    def test_medium_ratio_hybrid(self):
        """Medium tier3 ratio → Hybrid prediction."""
        ctrl = EngineController()
        dist = ctrl.compute_tier_distribution(1000, 0.5)
        report = ctrl.get_impact_assessment(dist)
        assert report.prediction_type == "Hybrid"
