"""Synthetic cascade generation and shape validation utilities.
SPEC: docs/spec/10_VALIDATION_SPEC.md#val-01-through-val-03
"""
import math


def generate_exponential_cascade(
    steps: int = 20,
    base_rate: float = 0.05,
    growth: float = 1.3,
) -> list[float]:
    """Generate adoption counts following an exponential growth pattern.

    SPEC: docs/spec/10_VALIDATION_SPEC.md#val-01

    Returns:
        List of adoption counts per step (monotonically increasing, accelerating).
    """
    result: list[float] = []
    current = base_rate
    for _ in range(steps):
        result.append(current)
        current *= growth
    return result


def generate_scurve_cascade(
    steps: int = 30,
    midpoint: int = 15,
    steepness: float = 0.5,
) -> list[float]:
    """Generate adoption counts following a logistic (S-curve) pattern.

    SPEC: docs/spec/10_VALIDATION_SPEC.md#val-02

    Args:
        steps: Number of simulation steps.
        midpoint: Step index where adoption reaches 50% of max (inflection point).
        steepness: Controls how sharply the curve rises around the midpoint.

    Returns:
        List of adoption values in [0, 1] following logistic growth.
    """
    result: list[float] = []
    for t in range(steps):
        val = 1.0 / (1.0 + math.exp(-steepness * (t - midpoint)))
        result.append(val)
    return result


def generate_collapse_cascade(
    steps: int = 20,
    peak_step: int = 10,
    drop_rate: float = 0.4,
) -> list[float]:
    """Generate a cascade that rises then collapses after peak_step.

    SPEC: docs/spec/10_VALIDATION_SPEC.md#val-03

    Args:
        steps: Total number of simulation steps.
        peak_step: Step at which adoption peaks before collapse.
        drop_rate: Multiplicative decay per step after peak.

    Returns:
        List of adoption counts: rises linearly to peak then decays.
    """
    result: list[float] = []
    peak_value = float(peak_step + 1)
    for t in range(steps):
        if t <= peak_step:
            result.append(float(t + 1))
        else:
            steps_after = t - peak_step
            result.append(peak_value * ((1.0 - drop_rate) ** steps_after))
    return result


def validate_exponential_shape(
    adoption_curve: list[float],
    tolerance: float = 0.10,
) -> bool:
    """Check whether a curve is exponential within the given tolerance.

    SPEC: docs/spec/10_VALIDATION_SPEC.md#val-01

    A curve is considered exponential if:
    - It is monotonically non-decreasing.
    - It shows acceleration: the second half grows faster than the first half.
    - At least (1 - tolerance) fraction of consecutive pairs are non-decreasing.

    Args:
        adoption_curve: List of adoption values.
        tolerance: Allowed fraction of non-monotonic steps (default 0.10).

    Returns:
        True if the curve is exponential within tolerance.
    """
    if len(adoption_curve) < 3:
        return False

    n = len(adoption_curve)

    # Check monotonically non-decreasing within tolerance
    violations = sum(
        1 for i in range(1, n) if adoption_curve[i] < adoption_curve[i - 1]
    )
    if violations / (n - 1) > tolerance:
        return False

    # Check acceleration: growth in second half > growth in first half
    mid = n // 2
    first_half_growth = adoption_curve[mid - 1] - adoption_curve[0]
    second_half_growth = adoption_curve[-1] - adoption_curve[mid]

    return second_half_growth > first_half_growth


def validate_scurve_inflection(
    adoption_curve: list[float],
    expected_midpoint: int,
    tolerance: int = 2,
) -> bool:
    """Find the inflection point of the curve and check it is near expected_midpoint.

    SPEC: docs/spec/10_VALIDATION_SPEC.md#val-02

    The inflection point is where the second derivative changes sign (acceleration
    switches from positive to negative), i.e. the step with maximum first derivative.

    Args:
        adoption_curve: List of adoption values.
        expected_midpoint: Expected index of the inflection point.
        tolerance: Maximum allowed distance from expected_midpoint (default 2).

    Returns:
        True if the detected inflection point is within tolerance of expected_midpoint.
    """
    if len(adoption_curve) < 3:
        return False

    # First derivative
    first_deriv = [
        adoption_curve[i + 1] - adoption_curve[i]
        for i in range(len(adoption_curve) - 1)
    ]

    # Inflection point = index with maximum first derivative
    max_idx = max(range(len(first_deriv)), key=lambda i: first_deriv[i])

    return abs(max_idx - expected_midpoint) <= tolerance


def validate_collapse(
    adoption_curve: list[float],
    event_step: int,
    min_drop: float = 0.20,
) -> bool:
    """Check whether adoption drops by at least min_drop within 3 steps after event_step.

    SPEC: docs/spec/10_VALIDATION_SPEC.md#val-03

    Args:
        adoption_curve: List of adoption values.
        event_step: The step at which the collapse-triggering event occurs.
        min_drop: Minimum required fractional drop (default 0.20, i.e. 20%).

    Returns:
        True if adoption drops > min_drop within 3 steps after event_step.
    """
    if event_step < 0 or event_step >= len(adoption_curve):
        return False

    baseline = adoption_curve[event_step]
    if baseline <= 0:
        return False

    window_end = min(event_step + 4, len(adoption_curve))  # 3 steps after event_step
    for i in range(event_step + 1, window_end):
        drop = (baseline - adoption_curve[i]) / baseline
        if drop >= min_drop:
            return True

    return False


__all__ = [
    "generate_exponential_cascade",
    "generate_scurve_cascade",
    "generate_collapse_cascade",
    "validate_exponential_shape",
    "validate_scurve_inflection",
    "validate_collapse",
]
