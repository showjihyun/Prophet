"""Scale benchmark and PettingZoo env wrapper tests.
Auto-generated from SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md
SPEC Version: 0.1.0
"""
import pytest

from app.engine.simulation.benchmark import ScaleBenchmark, BenchmarkResult
from app.engine.simulation.env_wrapper import ProphetEnv
from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.engine.simulation.schema import SimulationConfig
from app.engine.network.schema import CommunityConfig
from app.engine.simulation.community_orchestrator import CommunityOrchestrator


@pytest.mark.phase8
@pytest.mark.benchmark
class TestScaleBenchmark:
    """SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#scale-targets"""

    @pytest.mark.asyncio
    async def test_200_agents_under_5s(self):
        result = await ScaleBenchmark().run(200, 3)
        assert result.avg_step_ms < 5000
        assert result.agent_count == 200

    @pytest.mark.asyncio
    async def test_benchmark_result_fields(self):
        result = await ScaleBenchmark().run(50, 2)
        assert result.throughput_agents_per_sec > 0
        assert result.memory_mb > 0


class TestBatchSizeEnforcement:
    """SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#action-batching"""

    def test_community_orchestrator_batch_size_is_32(self):
        """Verify CommunityOrchestrator.BATCH_SIZE == 32 per SPEC G11."""
        assert CommunityOrchestrator.BATCH_SIZE == 32

    def test_batch_size_is_class_attribute(self):
        """BATCH_SIZE must be a class-level constant, not instance-level."""
        assert hasattr(CommunityOrchestrator, "BATCH_SIZE")
        assert isinstance(CommunityOrchestrator.BATCH_SIZE, int)


class TestScaleTiers:
    """SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#scale-targets — Dev/Staging tier smoke tests."""

    def test_dev_tier_200_agents_create(self):
        """Dev tier: create 200-agent simulation (no run). SPEC target <2s."""
        import time
        config = ScaleBenchmark._make_config(200, steps=1)
        orch = SimulationOrchestrator()
        t0 = time.perf_counter()
        state = orch.create_simulation(config)
        elapsed = time.perf_counter() - t0
        assert len(state.agents) == 200
        assert elapsed < 2.0, f"Dev tier create took {elapsed:.2f}s, expected <2s"

    @pytest.mark.asyncio
    async def test_dev_tier_200_agents_one_step(self):
        """Dev tier: create + 1 step for 200 agents. SPEC target <2s total."""
        import time
        config = ScaleBenchmark._make_config(200, steps=1)
        orch = SimulationOrchestrator()
        t0 = time.perf_counter()
        state = orch.create_simulation(config)
        orch.start(state.simulation_id)
        await orch.run_step(state.simulation_id)
        elapsed = time.perf_counter() - t0
        assert elapsed < 2.0, f"Dev tier create+1step took {elapsed:.2f}s, expected <2s"

    def test_10k_agents_create(self):
        """10K agent smoke test: verify simulation can be created (not run).
        SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#scale-targets (Production tier)
        """
        from uuid import uuid4
        from app.engine.simulation.schema import CampaignConfig
        config = SimulationConfig(
            simulation_id=uuid4(),
            name="10K Smoke Test",
            description="10K agent creation smoke test",
            communities=[
                CommunityConfig(id=str(i), name=f"c{i}", size=2000, agent_type="consumer")
                for i in range(5)
            ],
            campaign=CampaignConfig(
                name="Smoke Campaign",
                channels=["sns"],
                message="smoke test",
                target_communities=["all"],
                novelty=0.5,
                utility=0.5,
            ),
            max_steps=1,
            random_seed=42,
        )
        orch = SimulationOrchestrator()
        state = orch.create_simulation(config)
        assert len(state.agents) == 10000


@pytest.mark.phase8
class TestProphetEnv:
    """SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md"""

    def test_reset_returns_observation(self):
        config = ScaleBenchmark._make_config(20, 3)
        env = ProphetEnv(config)
        obs = env.reset()
        assert obs["agent_count"] == 20
        assert not env.done

    def test_step_returns_tuple(self):
        config = ScaleBenchmark._make_config(20, 3)
        env = ProphetEnv(config)
        env.reset()
        obs, reward, done, info = env.step()
        assert "step" in info
        assert isinstance(reward, float)
        env.close()

    def test_done_after_max_steps(self):
        config = ScaleBenchmark._make_config(10, 2)
        env = ProphetEnv(config)
        env.reset()
        env.step()
        env.step()
        assert env.done
        env.close()

    def test_close_cleans_up(self):
        config = ScaleBenchmark._make_config(10, 2)
        env = ProphetEnv(config)
        env.reset()
        env.close()
        assert env.done
