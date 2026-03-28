"""Monte Carlo Runner — runs multiple simulation instances for statistical analysis.
SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector (Monte Carlo section)
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import replace
from uuid import uuid4

from app.engine.diffusion.schema import MonteCarloResult, RunSummary
from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.engine.simulation.schema import SimulationConfig

logger = logging.getLogger(__name__)


class MonteCarloRunner:
    """Runs multiple simulation instances and aggregates results.

    SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector

    Phase 6: synchronous asyncio version. Celery integration deferred.
    Each run creates a fresh SimulationState, runs to max_steps, collects stats.
    Aggregates: viral_probability, expected_reach, p5/p50/p95.
    """

    def __init__(self, llm_adapter=None) -> None:
        """SPEC: docs/spec/04_SIMULATION_SPEC.md"""
        self._llm_adapter = llm_adapter

    async def run(
        self,
        simulation_config: SimulationConfig,
        n_runs: int = 100,
        parallel: bool = True,
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector

        Each run:
            1. Create fresh SimulationState with unique seed
            2. Run to max_steps
            3. Collect final adoption stats

        Aggregate:
            - viral_probability: fraction of runs with viral cascade detected
            - expected_reach: mean final adoption across runs
            - p5/p50/p95: percentiles of final adoption
        """
        base_seed = simulation_config.random_seed or 42
        summaries: list[RunSummary] = []

        for run_id in range(n_runs):
            # Create unique config per run
            run_seed = base_seed + run_id * 1000
            run_config = replace(
                simulation_config,
                simulation_id=uuid4(),
                random_seed=run_seed,
            )

            orch = SimulationOrchestrator(llm_adapter=self._llm_adapter)
            state = orch.create_simulation(run_config)
            orch.start(state.simulation_id)

            viral_detected = False
            steps_completed = 0

            for step in range(run_config.max_steps):
                try:
                    result = await orch.run_step(state.simulation_id)
                    steps_completed = step + 1

                    # Check for viral cascade
                    if any(e.event_type == "viral_cascade" for e in result.emergent_events):
                        viral_detected = True
                except Exception as e:
                    logger.warning("Monte Carlo run %d failed at step %d: %s", run_id, step, e)
                    break

            # Get final state
            final_state = orch.get_state(state.simulation_id)
            final_adoption = sum(1 for a in final_state.agents if a.adopted)

            summaries.append(RunSummary(
                run_id=run_id,
                final_adoption=final_adoption,
                viral_detected=viral_detected,
                steps_completed=steps_completed,
            ))

        # Aggregate
        adoptions = [s.final_adoption for s in summaries]
        total_agents = sum(c.size for c in simulation_config.communities)

        viral_count = sum(1 for s in summaries if s.viral_detected)
        viral_probability = viral_count / n_runs if n_runs > 0 else 0.0

        expected_reach = statistics.mean(adoptions) if adoptions else 0.0

        sorted_adoptions = sorted(adoptions)
        n = len(sorted_adoptions)
        if n > 0:
            p5 = sorted_adoptions[max(0, int(n * 0.05))]
            p50 = sorted_adoptions[max(0, int(n * 0.50))]
            p95 = sorted_adoptions[max(0, min(n - 1, int(n * 0.95)))]
        else:
            p5 = p50 = p95 = 0.0

        # Community adoption (simplified: average across runs)
        community_adoption: dict[str, float] = {}
        for comm in simulation_config.communities:
            community_adoption[comm.id] = expected_reach / total_agents if total_agents > 0 else 0.0

        return MonteCarloResult(
            n_runs=n_runs,
            viral_probability=viral_probability,
            expected_reach=expected_reach,
            community_adoption=community_adoption,
            p5_reach=float(p5),
            p50_reach=float(p50),
            p95_reach=float(p95),
            run_summaries=summaries,
        )


__all__ = ["MonteCarloRunner"]
