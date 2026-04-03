"""F23 Scenario Comparison.
SPEC: docs/spec/09_HARNESS_SPEC.md#f23-scenario-comparison
"""
from __future__ import annotations

from uuid import UUID

from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.engine.simulation.schema import ScenarioComparison, StepResult


_DEFAULT_METRICS = ["adoption_rate", "mean_sentiment", "diffusion_rate", "total_adoption"]


class ScenarioComparator:
    """Compares two simulation runs side-by-side.

    SPEC: docs/spec/09_HARNESS_SPEC.md#f23-scenario-comparison
    """

    def __init__(self, orchestrator: SimulationOrchestrator | None = None) -> None:
        """Initialise with an optional shared orchestrator.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f23-scenario-comparison
        """
        self._orchestrator = orchestrator or SimulationOrchestrator()

    def compare(
        self,
        sim_id_a: UUID,
        sim_id_b: UUID,
        metrics: list[str] | None = None,
    ) -> ScenarioComparison:
        """Diff two simulation runs and return a ScenarioComparison.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f23-scenario-comparison

        Compares step_history of both simulations across the requested metrics.
        If the two runs have different lengths, comparison uses the shorter run's length.

        Returns:
            ScenarioComparison with per-metric difference lists, winner, and summary.
        """
        state_a = self._orchestrator._simulations.get(sim_id_a)
        if state_a is None:
            raise ValueError(f"Simulation {sim_id_a} not found")

        state_b = self._orchestrator._simulations.get(sim_id_b)
        if state_b is None:
            raise ValueError(f"Simulation {sim_id_b} not found")

        history_a = state_a.step_history
        history_b = state_b.step_history

        if metrics is None:
            metrics = _DEFAULT_METRICS

        # Compute per-metric diffs (value_b - value_a for each step)
        min_steps = min(len(history_a), len(history_b))
        metric_diffs: dict[str, list[float]] = {}
        for metric in metrics:
            diffs: list[float] = []
            for i in range(min_steps):
                val_a = float(getattr(history_a[i], metric, 0.0))
                val_b = float(getattr(history_b[i], metric, 0.0))
                diffs.append(val_b - val_a)
            metric_diffs[metric] = diffs

        # Final adoption diff
        final_a = history_a[-1].adoption_rate if history_a else 0.0
        final_b = history_b[-1].adoption_rate if history_b else 0.0
        final_adoption_diff = final_b - final_a

        # Emergent event types in each run (last step only for brevity)
        events_a: set[str] = set()
        events_b: set[str] = set()
        for sr in history_a:
            events_a.update(e.event_type for e in sr.emergent_events)
        for sr in history_b:
            events_b.update(e.event_type for e in sr.emergent_events)

        emergent_event_diff: list[str] = sorted(events_a.symmetric_difference(events_b))

        # Determine winner: higher final adoption_rate wins
        winner: UUID | None = None
        if final_a > final_b:
            winner = sim_id_a
        elif final_b > final_a:
            winner = sim_id_b

        summary = (
            f"Sim A final adoption: {final_a:.3f}, "
            f"Sim B final adoption: {final_b:.3f}, "
            f"diff: {final_adoption_diff:+.3f}, "
            f"winner: {'A' if winner == sim_id_a else 'B' if winner == sim_id_b else 'tie'}"
        )

        return ScenarioComparison(
            sim_a=sim_id_a,
            sim_b=sim_id_b,
            metric_diffs=metric_diffs,
            final_adoption_diff=final_adoption_diff,
            emergent_event_diff=emergent_event_diff,
            winner=winner,
            summary=summary,
        )


__all__ = ["ScenarioComparator"]
