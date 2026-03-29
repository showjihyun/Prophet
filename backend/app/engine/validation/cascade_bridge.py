"""Bridge simulation results to cascade comparison format.
SPEC: docs/spec/10_VALIDATION_SPEC.md#val-07-val-08
"""
from app.engine.simulation.schema import StepResult
from app.engine.validation.comparator import SimulatedCascade


def steps_to_cascades(
    steps: list[StepResult],
    cascade_id: str = "sim",
) -> SimulatedCascade:
    """Convert a list of StepResult objects into a SimulatedCascade for comparison.

    SPEC: docs/spec/10_VALIDATION_SPEC.md#val-07-val-08

    Mapping:
        scale       = max total_adoption across all steps
        depth       = len(steps)  (number of propagation steps)
        max_breadth = max diffusion_rate across steps (approximation of breadth)

    Args:
        steps: Ordered list of simulation step results.
        cascade_id: Identifier string for the resulting SimulatedCascade.

    Returns:
        SimulatedCascade ready for use with CascadeComparator.
    """
    if not steps:
        return SimulatedCascade(
            cascade_id=cascade_id,
            scale=0,
            depth=0,
            max_breadth=0,
        )

    scale = max(s.total_adoption for s in steps)
    depth = len(steps)
    max_breadth = int(max(s.diffusion_rate for s in steps))

    return SimulatedCascade(
        cascade_id=cascade_id,
        scale=scale,
        depth=depth,
        max_breadth=max_breadth,
    )


__all__ = ["steps_to_cascades"]
