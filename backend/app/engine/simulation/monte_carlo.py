"""Monte Carlo Runner — runs multiple simulation instances for statistical analysis.
SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector (Monte Carlo section)
"""
from __future__ import annotations

import asyncio
import logging
import statistics
from collections import defaultdict
from dataclasses import replace
from uuid import UUID, uuid4

from app.engine.diffusion.schema import MonteCarloResult, RunSummary
from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.engine.simulation.schema import SimulationConfig

logger = logging.getLogger(__name__)

# Max concurrent simulation runs to prevent memory exhaustion.
DEFAULT_MAX_CONCURRENCY = 3


class MonteCarloRunner:
    """Runs multiple simulation instances and aggregates results.

    SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector

    Each run creates a fresh SimulationState, runs to max_steps, collects stats.
    Parallel execution via asyncio.Semaphore with configurable concurrency.
    Aggregates: viral_probability, expected_reach, p5/p50/p95, per-community adoption.
    """

    def __init__(self, llm_adapter=None) -> None:
        """SPEC: docs/spec/04_SIMULATION_SPEC.md"""
        self._llm_adapter = llm_adapter

    async def _execute_single_run(
        self,
        run_id: int,
        run_config: SimulationConfig,
        semaphore: asyncio.Semaphore,
    ) -> tuple[RunSummary, dict[UUID, int], dict[UUID, int]]:
        """Execute a single Monte Carlo run under the semaphore concurrency limit.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector
        """
        async with semaphore:
            orch = SimulationOrchestrator(llm_adapter=self._llm_adapter)
            state = orch.create_simulation(run_config)
            # `orch.start()` is async — must be awaited. An earlier version
            # forgot the `await`, silently leaking a coroutine and leaving
            # the simulation in CONFIGURED state.
            await orch.start(state.simulation_id)

            viral_detected = False
            steps_completed = 0

            for step in range(run_config.max_steps):
                try:
                    result = await orch.run_step(state.simulation_id)
                    steps_completed = step + 1
                    if any(e.event_type == "viral_cascade" for e in result.emergent_events):
                        viral_detected = True
                except Exception as e:
                    logger.warning("Monte Carlo run %d failed at step %d: %s", run_id, step, e)
                    break

            final_state = orch.get_state(state.simulation_id)
            final_adoption = sum(1 for a in final_state.agents if a.adopted)

            # Per-community adoption for this run
            community_adopted: dict[UUID, int] = defaultdict(int)
            community_total: dict[UUID, int] = defaultdict(int)
            for a in final_state.agents:
                community_total[a.community_id] += 1
                if a.adopted:
                    community_adopted[a.community_id] += 1

            return RunSummary(
                run_id=run_id,
                final_adoption=final_adoption,
                viral_detected=viral_detected,
                steps_completed=steps_completed,
            ), community_adopted, community_total

    async def run(
        self,
        simulation_config: SimulationConfig,
        n_runs: int | None = None,
        parallel: bool = True,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation with parallel execution.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector

        Each run:
            1. Create fresh SimulationState with unique seed
            2. Run to max_steps
            3. Collect final adoption + per-community stats

        Aggregate:
            - viral_probability: fraction of runs with viral cascade detected
            - expected_reach: mean final adoption across runs
            - p5/p50/p95: percentiles of final adoption
            - community_adoption: real per-community mean adoption rate
        """
        if n_runs is None:
            n_runs = 10  # domain default
        base_seed = simulation_config.random_seed or 42

        concurrency = max_concurrency if parallel else 1
        semaphore = asyncio.Semaphore(concurrency)

        # Build run configs
        tasks = []
        for run_id in range(n_runs):
            run_seed = base_seed + run_id * 1000
            run_config = replace(
                simulation_config,
                simulation_id=uuid4(),
                random_seed=run_seed,
            )
            tasks.append(self._execute_single_run(run_id, run_config, semaphore))

        # Execute all runs concurrently (bounded by semaphore)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        summaries: list[RunSummary] = []
        all_community_adopted: dict[UUID, list[int]] = defaultdict(list)
        all_community_total: dict[UUID, int] = {}

        for r in results:
            if isinstance(r, Exception):
                logger.error("Monte Carlo run failed: %s", r)
                continue
            summary, comm_adopted, comm_total = r
            summaries.append(summary)
            for cid, count in comm_adopted.items():
                all_community_adopted[cid].append(count)
            for cid, count in comm_total.items():
                all_community_total[cid] = count  # same across runs

        # Aggregate
        adoptions = [s.final_adoption for s in summaries]
        total_agents = sum(c.size for c in simulation_config.communities)

        viral_count = sum(1 for s in summaries if s.viral_detected)
        viral_probability = viral_count / len(summaries) if summaries else 0.0

        expected_reach = statistics.mean(adoptions) if adoptions else 0.0

        sorted_adoptions = sorted(adoptions)
        n = len(sorted_adoptions)
        if n > 0:
            p5 = sorted_adoptions[max(0, int(n * 0.05))]
            p50 = sorted_adoptions[max(0, int(n * 0.50))]
            p95 = sorted_adoptions[max(0, min(n - 1, int(n * 0.95)))]
        else:
            p5 = p50 = p95 = 0.0

        # Per-community adoption: real mean across runs (not global average)
        community_adoption: dict[str, float] = {}
        for comm in simulation_config.communities:
            # community IDs may be UUID objects or strings depending on config source
            cid: UUID | str = comm.id
            if not isinstance(cid, UUID):
                try:
                    cid = UUID(str(cid))
                except (ValueError, AttributeError):
                    pass  # keep as-is
            adopted_counts = all_community_adopted.get(cid, [0])
            total = all_community_total.get(cid, comm.size)
            mean_adopted = statistics.mean(adopted_counts) if adopted_counts else 0.0
            community_adoption[str(comm.id)] = mean_adopted / total if total > 0 else 0.0

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
