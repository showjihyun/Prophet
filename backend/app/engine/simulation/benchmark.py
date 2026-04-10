"""Scale benchmark harness.
SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#scale-targets
"""
import asyncio
import time
import tracemalloc
from dataclasses import dataclass
from uuid import uuid4

from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.engine.simulation.schema import SimulationConfig, CampaignConfig
from app.engine.network.schema import CommunityConfig


@dataclass
class BenchmarkResult:
    agent_count: int
    steps: int
    avg_step_ms: float
    max_step_ms: float
    memory_mb: float
    throughput_agents_per_sec: float
    community_breakdown: dict[str, int]


class ScaleBenchmark:
    """Run simulation benchmarks at various agent counts.
    SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#scale-targets
    """

    @staticmethod
    def _make_config(agent_count: int, steps: int = 5, seed: int = 42) -> SimulationConfig:
        """Create config distributing agents across 5 communities."""
        # Distribute: 30% consumer, 25% early_adopter, 20% skeptic, 15% influencer, 10% expert
        sizes = {
            "A": int(agent_count * 0.25),
            "B": int(agent_count * 0.30),
            "C": int(agent_count * 0.20),
            "D": int(agent_count * 0.10),
            "E": int(agent_count * 0.15),
        }
        # Adjust rounding to match exactly
        remainder = agent_count - sum(sizes.values())
        sizes["B"] += remainder

        return SimulationConfig(
            simulation_id=uuid4(),
            name=f"Benchmark {agent_count} agents",
            description="Scale benchmark",
            communities=[
                CommunityConfig(id="A", name="early_adopters", size=sizes["A"], agent_type="early_adopter"),
                CommunityConfig(id="B", name="consumers", size=sizes["B"], agent_type="consumer"),
                CommunityConfig(id="C", name="skeptics", size=sizes["C"], agent_type="skeptic"),
                CommunityConfig(id="D", name="experts", size=sizes["D"], agent_type="expert"),
                CommunityConfig(id="E", name="influencers", size=sizes["E"], agent_type="influencer"),
            ],
            campaign=CampaignConfig(
                name="Benchmark Campaign",
                channels=["sns"],
                message="benchmark test",
                target_communities=["all"],
                novelty=0.7,
                utility=0.6,
            ),
            max_steps=steps,
            random_seed=seed,
        )

    async def run(self, agent_count: int = 1000, steps: int = 5) -> BenchmarkResult:
        """Run a benchmark with the given agent count and steps.
        SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#scale-targets
        """
        tracemalloc.start()
        orch = SimulationOrchestrator()
        config = self._make_config(agent_count, steps)

        state = orch.create_simulation(config)
        await orch.start(state.simulation_id)

        step_times: list[float] = []
        for _ in range(steps):
            t0 = time.perf_counter()
            await orch.run_step(state.simulation_id)
            step_times.append((time.perf_counter() - t0) * 1000)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        avg_ms = sum(step_times) / len(step_times)
        max_ms = max(step_times)
        memory_mb = peak / 1024 / 1024
        throughput = agent_count / (avg_ms / 1000) if avg_ms > 0 else 0

        return BenchmarkResult(
            agent_count=agent_count,
            steps=steps,
            avg_step_ms=round(avg_ms, 1),
            max_step_ms=round(max_ms, 1),
            memory_mb=round(memory_mb, 1),
            throughput_agents_per_sec=round(throughput),
            community_breakdown={c.id: c.size for c in config.communities},
        )


__all__ = ["ScaleBenchmark", "BenchmarkResult"]
