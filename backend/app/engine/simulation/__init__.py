"""Simulation Orchestrator — public API exports.
SPEC: docs/spec/04_SIMULATION_SPEC.md
"""
from app.engine.simulation.schema import (
    SimulationStatus,
    SimulationConfig,
    CampaignConfig,
    TemporalConfig,
    AgentModification,
    CommunityStepMetrics,
    StepResult,
    ScenarioComparison,
    SimulationRun,
)
from app.engine.simulation.orchestrator import SimulationOrchestrator, SimulationState
from app.engine.simulation.step_runner import StepRunner
from app.engine.simulation.metric_collector import MetricCollector
from app.engine.simulation.monte_carlo import MonteCarloRunner
from app.engine.simulation.event_activation import EventDrivenActivation
from app.engine.simulation.exceptions import (
    SimulationStepError,
    SimulationCapacityError,
    InvalidStateTransitionError,
    InvalidStateError,
    StepNotFoundError,
    DBPersistenceError,
)

__all__ = [
    # Schema
    "SimulationStatus",
    "SimulationConfig",
    "CampaignConfig",
    "TemporalConfig",
    "AgentModification",
    "CommunityStepMetrics",
    "StepResult",
    "ScenarioComparison",
    "SimulationRun",
    # Core
    "SimulationOrchestrator",
    "SimulationState",
    "StepRunner",
    "MetricCollector",
    "MonteCarloRunner",
    # Exceptions
    "SimulationStepError",
    "SimulationCapacityError",
    "InvalidStateTransitionError",
    "InvalidStateError",
    "StepNotFoundError",
    "DBPersistenceError",
    # Event-driven activation
    "EventDrivenActivation",
]
