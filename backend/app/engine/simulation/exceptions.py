"""Simulation-specific exceptions.
SPEC: docs/spec/04_SIMULATION_SPEC.md#error-specification
"""


class SimulationStepError(RuntimeError):
    """Step loop async task crashes.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#error-specification
    """


class SimulationCapacityError(RuntimeError):
    """Max concurrent simulations (3) exceeded.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#error-specification
    """


class InvalidStateTransitionError(ValueError):
    """Invalid state transition (e.g., COMPLETED -> RUNNING).
    SPEC: docs/spec/04_SIMULATION_SPEC.md#error-specification
    """


class InvalidStateError(ValueError):
    """Operation not allowed in current state (e.g., modify_agent while RUNNING).
    SPEC: docs/spec/04_SIMULATION_SPEC.md#error-specification
    """


class StepNotFoundError(ValueError):
    """replay_step target step not persisted.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#error-specification
    """


class DBPersistenceError(RuntimeError):
    """DB persistence failure during step.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#error-specification
    """


__all__ = [
    "SimulationStepError",
    "SimulationCapacityError",
    "InvalidStateTransitionError",
    "InvalidStateError",
    "StepNotFoundError",
    "DBPersistenceError",
]
