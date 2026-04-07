"""SLM Quality Validator — compares Tier 1/2 vs Tier 3 outputs.
SPEC: docs/spec/10_VALIDATION_SPEC.md#val-04-val-05
"""
from dataclasses import dataclass, field

from app.engine.simulation.schema import StepResult


@dataclass
class TierComparisonReport:
    """Result of SLM vs LLM tier comparison.

    SPEC: docs/spec/10_VALIDATION_SPEC.md#val-04-val-05
    """
    adoption_rate_slm: float
    adoption_rate_llm: float
    adoption_diff: float
    emergent_events_slm: list[str] = field(default_factory=list)
    emergent_events_llm: list[str] = field(default_factory=list)
    emergent_f1: float = 0.0
    pass_val04: bool = False
    pass_val05: bool = False


class SLMQualityValidator:
    """Validates that SLM (Tier 1/2) outputs are comparable to LLM (Tier 3) outputs.

    SPEC: docs/spec/10_VALIDATION_SPEC.md#val-04-val-05

    VAL-04: Adoption rate difference between SLM and LLM runs must be < 0.15.
    VAL-05: F1 score for emergent event types must be > 0.70.
    """

    def compare_tier_quality(
        self,
        slm_steps: list[StepResult],
        llm_steps: list[StepResult],
    ) -> TierComparisonReport:
        """Compare SLM and LLM simulation outputs.

        SPEC: docs/spec/10_VALIDATION_SPEC.md#val-04-val-05

        Args:
            slm_steps: Step results from an SLM-driven simulation.
            llm_steps: Step results from an LLM-driven simulation.

        Returns:
            TierComparisonReport with VAL-04 and VAL-05 pass/fail.
        """
        # --- adoption rate at final step ---
        slm_adoption = slm_steps[-1].adoption_rate if slm_steps else 0.0
        llm_adoption = llm_steps[-1].adoption_rate if llm_steps else 0.0
        adoption_diff = abs(slm_adoption - llm_adoption)

        # --- emergent event types ---
        slm_event_types = [e.event_type for step in slm_steps for e in step.emergent_events]
        llm_event_types = [e.event_type for step in llm_steps for e in step.emergent_events]

        emergent_f1 = self._compute_f1(slm_event_types, llm_event_types)

        # --- VAL-04 / VAL-05 pass criteria ---
        pass_val04 = adoption_diff < 0.15
        pass_val05 = emergent_f1 > 0.7

        return TierComparisonReport(
            adoption_rate_slm=slm_adoption,
            adoption_rate_llm=llm_adoption,
            adoption_diff=adoption_diff,
            emergent_events_slm=slm_event_types,
            emergent_events_llm=llm_event_types,
            emergent_f1=emergent_f1,
            pass_val04=pass_val04,
            pass_val05=pass_val05,
        )

    @staticmethod
    def _compute_f1(predicted: list[str], actual: list[str]) -> float:
        """Compute token-level F1 score between two multisets of event type strings.

        Treats each list as a bag-of-tokens.  Precision = |intersection| / |predicted|,
        Recall = |intersection| / |actual|.  F1 = harmonic mean.

        Returns 1.0 if both lists are empty (perfect agreement on no events).
        Returns 0.0 if one list is empty and the other is not.
        """
        if not predicted and not actual:
            return 1.0
        if not predicted or not actual:
            return 0.0

        # Multiset intersection
        from collections import Counter
        pred_counter = Counter(predicted)
        actual_counter = Counter(actual)
        intersection = sum((pred_counter & actual_counter).values())

        precision = intersection / len(predicted)
        recall = intersection / len(actual)

        if precision + recall == 0:
            return 0.0

        return 2 * precision * recall / (precision + recall)


__all__ = [
    "TierComparisonReport",
    "SLMQualityValidator",
]
