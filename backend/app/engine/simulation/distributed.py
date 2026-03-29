"""Ray-based distributed simulation execution.
SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md

Distributes CommunityOrchestrator.tick() across Ray workers.
Falls back to local asyncio.gather if Ray is not available.

Start Ray: ray start --head
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Ray is optional — graceful degradation
try:
    import ray
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False


@dataclass
class DistributedConfig:
    """Configuration for distributed execution."""
    enabled: bool = False           # explicitly opt-in
    num_workers: int = 4            # Ray workers per community
    use_gpu: bool = False
    ray_address: str = "auto"       # "auto" connects to existing cluster
    fallback_to_local: bool = True  # if Ray unavailable, use local asyncio


class DistributedRunner:
    """Distributes simulation step execution across Ray workers.

    SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md

    Architecture:
        SimulationOrchestrator.run_step()
            +-- DistributedRunner.execute_communities()
            |   +-- [Ray Worker 1] CommunityOrchestrator(Alpha).tick()
            |   +-- [Ray Worker 2] CommunityOrchestrator(Beta).tick()
            |   +-- [Ray Worker 3] CommunityOrchestrator(Gamma).tick()
            |   +-- [Ray Worker 4] CommunityOrchestrator(Delta).tick()
            |   +-- [Ray Worker 5] CommunityOrchestrator(Bridge).tick()
            +-- BridgePropagator + Global aggregation (local)
    """

    def __init__(self, config: DistributedConfig | None = None):
        self._config = config or DistributedConfig()
        self._initialized = False

    def is_available(self) -> bool:
        """Check if Ray is available and configured."""
        if not self._config.enabled:
            return False
        if not RAY_AVAILABLE:
            logger.warning("Ray not installed. Install with: uv add ray")
            return False
        return True

    def initialize(self) -> bool:
        """Initialize Ray connection.
        Returns True if Ray initialized, False if falling back to local.
        """
        if not self.is_available():
            if self._config.fallback_to_local:
                logger.info("Ray unavailable, using local asyncio execution")
                return False
            raise RuntimeError("Ray required but not available")

        try:
            if not ray.is_initialized():
                ray.init(address=self._config.ray_address, ignore_reinit_error=True)
            self._initialized = True
            logger.info(f"Ray initialized: {ray.cluster_resources()}")
            return True
        except Exception as e:
            logger.warning(f"Ray init failed: {e}. Falling back to local.")
            return False

    async def execute_communities(
        self,
        community_orchestrators: list[Any],
        step: int,
        campaign_events: list[Any],
    ) -> list[Any]:
        """Execute community ticks, using Ray if available, asyncio otherwise.

        Args:
            community_orchestrators: list of CommunityOrchestrator instances
            step: current simulation step
            campaign_events: campaign events for this step

        Returns:
            list of CommunityTickResult
        """
        if self._initialized and RAY_AVAILABLE:
            return await self._execute_ray(community_orchestrators, step, campaign_events)
        else:
            return await self._execute_local(community_orchestrators, step, campaign_events)

    async def _execute_local(self, orchs: list[Any], step: int, events: list[Any]) -> list[Any]:
        """Local asyncio.gather execution (default fallback)."""
        return list(await asyncio.gather(*[
            o.tick(step, events) for o in orchs
        ]))

    async def _execute_ray(self, orchs: list[Any], step: int, events: list[Any]) -> list[Any]:
        """Ray distributed execution.

        Each community is submitted as a Ray remote task.
        Ray handles scheduling across available workers/GPUs.
        """
        @ray.remote
        def _tick_community(orch_data: dict[str, Any], step: int, events: list[Any]) -> Any:
            """Ray remote function for community tick.
            Note: CommunityOrchestrator must be serializable.
            """
            import asyncio as _asyncio
            loop = _asyncio.new_event_loop()
            try:
                from app.engine.simulation.community_orchestrator import CommunityOrchestrator
                orch = CommunityOrchestrator(**orch_data)
                return loop.run_until_complete(orch.tick(step, events))
            finally:
                loop.close()

        # Submit tasks to Ray
        futures = []
        for orch in orchs:
            # Serialize orchestrator state for Ray
            orch_data = {
                "community_id": orch.community_id,
                "community_config": orch.community_config,
                "agents": orch.agents,
                "subgraph": orch.subgraph,
                "agent_node_map": orch.agent_node_map,
            }
            futures.append(_tick_community.remote(orch_data, step, events))

        # Gather results
        results = ray.get(futures)
        return list(results)

    def shutdown(self) -> None:
        """Shutdown Ray connection."""
        if self._initialized and RAY_AVAILABLE and ray.is_initialized():
            ray.shutdown()
            self._initialized = False


def get_distributed_runner(config: DistributedConfig | None = None) -> DistributedRunner:
    """Get a configured DistributedRunner.

    Usage:
        runner = get_distributed_runner(DistributedConfig(enabled=True))
        if runner.initialize():
            results = await runner.execute_communities(orchs, step, events)
        else:
            # automatic local fallback
            results = await runner.execute_communities(orchs, step, events)
    """
    return DistributedRunner(config)
