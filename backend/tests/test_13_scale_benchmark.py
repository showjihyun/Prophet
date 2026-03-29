"""Scale benchmark and PettingZoo env wrapper tests.
Auto-generated from SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md
SPEC Version: 0.1.0
"""
import pytest

from app.engine.simulation.benchmark import ScaleBenchmark, BenchmarkResult
from app.engine.simulation.env_wrapper import ProphetEnv


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
