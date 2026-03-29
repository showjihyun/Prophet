"""Validation pipeline for comparing simulated cascades with real-world data.
SPEC: docs/spec/10_VALIDATION_SPEC.md
"""
from app.engine.validation.twitter_dataset import (
    CascadeTree,
    TwitterDatasetLoader,
    ValidationMetrics,
)
from app.engine.validation.comparator import CascadeComparator, SimulatedCascade
from app.engine.validation.synthetic import (
    generate_exponential_cascade,
    generate_scurve_cascade,
    generate_collapse_cascade,
    validate_exponential_shape,
    validate_scurve_inflection,
    validate_collapse,
)
from app.engine.validation.tier_comparison import TierComparisonReport, SLMQualityValidator
from app.engine.validation.cascade_bridge import steps_to_cascades

__all__ = [
    "CascadeTree",
    "TwitterDatasetLoader",
    "ValidationMetrics",
    "CascadeComparator",
    "SimulatedCascade",
    # VAL-01–03
    "generate_exponential_cascade",
    "generate_scurve_cascade",
    "generate_collapse_cascade",
    "validate_exponential_shape",
    "validate_scurve_inflection",
    "validate_collapse",
    # VAL-04–05
    "TierComparisonReport",
    "SLMQualityValidator",
    # VAL-07–08
    "steps_to_cascades",
]
