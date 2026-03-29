"""Tests for Ray distributed execution.
Auto-generated from SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md
SPEC Version: 0.1.0

Ray is optional — tests verify graceful degradation.
"""
import pytest

from app.engine.simulation.distributed import (
    DistributedRunner,
    DistributedConfig,
    RAY_AVAILABLE,
    get_distributed_runner,
)


@pytest.mark.phase8
class TestDistributedRunner:
    """SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md"""

    def test_disabled_by_default(self):
        runner = DistributedRunner()
        assert not runner.is_available()

    def test_enabled_without_ray_falls_back(self):
        runner = DistributedRunner(DistributedConfig(enabled=True, fallback_to_local=True))
        result = runner.initialize()
        # If Ray not installed, should return False (fallback)
        if not RAY_AVAILABLE:
            assert result is False

    def test_config_defaults(self):
        config = DistributedConfig()
        assert config.enabled is False
        assert config.num_workers == 4
        assert config.fallback_to_local is True
        assert config.ray_address == "auto"

    def test_config_custom(self):
        config = DistributedConfig(
            enabled=True,
            num_workers=8,
            use_gpu=True,
            ray_address="ray://cluster:10001",
            fallback_to_local=False,
        )
        assert config.enabled is True
        assert config.num_workers == 8
        assert config.use_gpu is True
        assert config.ray_address == "ray://cluster:10001"
        assert config.fallback_to_local is False

    def test_get_distributed_runner_factory(self):
        runner = get_distributed_runner()
        assert isinstance(runner, DistributedRunner)
        assert not runner.is_available()

    def test_get_distributed_runner_with_config(self):
        config = DistributedConfig(enabled=True)
        runner = get_distributed_runner(config)
        assert isinstance(runner, DistributedRunner)

    @pytest.mark.asyncio
    async def test_local_fallback_execution(self):
        """Even without Ray, execute_communities works via local asyncio."""
        from app.engine.simulation.benchmark import ScaleBenchmark
        from app.engine.simulation.orchestrator import SimulationOrchestrator

        config = ScaleBenchmark._make_config(20, 2)
        orch = SimulationOrchestrator()
        state = orch.create_simulation(config)
        orch.start(state.simulation_id)

        # Should work with local fallback
        result = await orch.run_step(state.simulation_id)
        assert result.step >= 0

    def test_shutdown_noop_when_not_initialized(self):
        runner = DistributedRunner()
        runner.shutdown()  # should not raise

    def test_enabled_without_ray_no_fallback_raises(self):
        """When fallback disabled and Ray unavailable, should raise."""
        if RAY_AVAILABLE:
            pytest.skip("Ray is installed, cannot test unavailable path")
        runner = DistributedRunner(
            DistributedConfig(enabled=True, fallback_to_local=False)
        )
        with pytest.raises(RuntimeError, match="Ray required but not available"):
            runner.initialize()
