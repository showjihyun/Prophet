"""F24 Simulation Sandbox — isolated test environment.
SPEC: docs/spec/09_HARNESS_SPEC.md#f24-simulation-sandbox
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import replace
from typing import AsyncIterator
from uuid import UUID

from app.engine.agent.perception import EnvironmentEvent
from app.engine.agent.schema import AgentState
from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.engine.simulation.schema import (
    AgentModification,
    CampaignConfig,
    CommunityConfig,
    SimulationConfig,
    SimulationRun,
    SimulationStatus,
    StepResult,
)
from app.engine.network.schema import NetworkConfig


def _default_config(seed: int = 42) -> SimulationConfig:
    """Build a minimal default SimulationConfig for sandbox use."""
    return SimulationConfig(
        name="Sandbox Simulation",
        description="Ephemeral sandbox for harness testing",
        communities=[
            CommunityConfig(
                id="sandbox_community",
                name="Sandbox Community",
                size=20,
                agent_type="consumer",
                personality_profile={
                    "openness": 0.5,
                    "skepticism": 0.3,
                    "trend_following": 0.5,
                    "brand_loyalty": 0.4,
                    "social_influence": 0.4,
                },
            )
        ],
        campaign=CampaignConfig(
            name="Sandbox Campaign",
            budget=500.0,
            channels=["sns"],
            message="Sandbox test message",
            target_communities=["all"],
            start_step=0,
            novelty=0.5,
            controversy=0.0,
            utility=0.5,
        ),
        network_config=NetworkConfig(
            ws_k_neighbors=4,
            ws_rewire_prob=0.1,
            ba_m_edges=2,
            cross_community_prob=0.0,
        ),
        max_steps=10,
        step_delay_ms=0,
        enable_personality_drift=False,
        enable_dynamic_edges=False,
        random_seed=seed,
        monte_carlo_runs=0,
    )


class SimulationSandbox:
    """Isolated simulation environment for harness testing.

    SPEC: docs/spec/09_HARNESS_SPEC.md#f24-simulation-sandbox

    Uses an in-process SimulationOrchestrator with optional mock LLM.
    Auto-tears down when the context manager exits.

    Usage::

        async with SimulationSandbox.create(seed=42) as sandbox:
            result = await sandbox.run_steps(5)
            assert result.adoption_rate >= 0.0
    """

    def __init__(
        self,
        orchestrator: SimulationOrchestrator,
        simulation_id: UUID,
    ) -> None:
        self._orchestrator = orchestrator
        self._simulation_id = simulation_id

    @classmethod
    @asynccontextmanager
    async def create(
        cls,
        config: SimulationConfig | None = None,
        mock_llm: bool = True,
        seed: int = 42,
    ) -> AsyncIterator["SimulationSandbox"]:
        """Async context manager that creates an isolated simulation sandbox.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f24-simulation-sandbox

        Args:
            config:   SimulationConfig to use. Defaults to a minimal 20-agent config.
            mock_llm: If True, uses MockLLMAdapter instead of a real LLM.
            seed:     Random seed for reproducibility (default 42).
        """
        llm_adapter = None
        if mock_llm:
            from harness.mocks.mock_environment import MockLLMAdapter
            llm_adapter = MockLLMAdapter()

        orchestrator = SimulationOrchestrator(llm_adapter=llm_adapter)

        resolved_config = config if config is not None else _default_config(seed)
        # Override seed if not set in the provided config
        if config is not None and config.random_seed is None:
            from dataclasses import replace as dc_replace
            resolved_config = dc_replace(resolved_config, random_seed=seed)

        state = orchestrator.create_simulation(resolved_config)
        orchestrator.start(resolved_config.simulation_id)

        sandbox = cls(orchestrator=orchestrator, simulation_id=resolved_config.simulation_id)
        try:
            yield sandbox
        finally:
            # Tear down: remove simulation from orchestrator memory
            orchestrator._simulations.pop(resolved_config.simulation_id, None)
            orchestrator._locks.pop(resolved_config.simulation_id, None)

    async def run_steps(self, n: int) -> StepResult:
        """Run n simulation steps and return the last StepResult.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f24-simulation-sandbox

        Raises:
            ValueError: if n <= 0.
        """
        if n <= 0:
            raise ValueError(f"n must be > 0, got {n}")

        state = self._orchestrator._simulations[self._simulation_id]
        last_result: StepResult | None = None

        for _ in range(n):
            if state.status != SimulationStatus.RUNNING.value:
                break
            last_result = await self._orchestrator.run_step(self._simulation_id)

        if last_result is None:
            raise RuntimeError("No steps were executed (simulation may have already completed)")

        return last_result

    async def run_to_completion(self) -> SimulationRun:
        """Run the simulation to completion and return a SimulationRun handle.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f24-simulation-sandbox
        """
        state = self._orchestrator._simulations[self._simulation_id]
        while state.status == SimulationStatus.RUNNING.value:
            await self._orchestrator.run_step(self._simulation_id)

        return SimulationRun(
            simulation_id=self._simulation_id,
            status=state.status,
            current_step=state.current_step,
            config=state.config,
        )

    async def get_agent(self, agent_id: UUID) -> AgentState:
        """Return the current AgentState for the given agent_id.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f24-simulation-sandbox

        Raises:
            ValueError: if agent_id not found.
        """
        state = self._orchestrator._simulations[self._simulation_id]
        for agent in state.agents:
            if agent.agent_id == agent_id:
                return agent
        raise ValueError(f"Agent {agent_id} not found in sandbox simulation")

    async def modify_agent(self, agent_id: UUID, mod: AgentModification) -> None:
        """Modify an agent in the sandbox (pauses and resumes automatically).

        SPEC: docs/spec/09_HARNESS_SPEC.md#f24-simulation-sandbox
        """
        state = self._orchestrator._simulations[self._simulation_id]
        was_running = state.status == SimulationStatus.RUNNING.value

        if was_running:
            await self._orchestrator.pause(self._simulation_id)

        await self._orchestrator.modify_agent(
            self._simulation_id, agent_id, modifications=mod
        )

        if was_running:
            await self._orchestrator.resume(self._simulation_id)

    async def inject_event(self, event: EnvironmentEvent) -> None:
        """Inject an external EnvironmentEvent into the running sandbox simulation.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f24-simulation-sandbox
        """
        self._orchestrator.inject_event(self._simulation_id, event=event)


__all__ = ["SimulationSandbox"]
