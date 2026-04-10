"""F20 Event/Agent Replay.
SPEC: docs/spec/09_HARNESS_SPEC.md#f20-eventagent-replay
"""
from __future__ import annotations

from dataclasses import replace
from typing import AsyncIterator
from uuid import UUID, uuid4

from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.engine.simulation.schema import AgentModification, SimulationConfig, SimulationStatus, StepResult


class ReplayRunner:
    """Replays a simulation from a stored step, optionally with modifications.

    SPEC: docs/spec/09_HARNESS_SPEC.md#f20-eventagent-replay

    Original run data is not modified.
    Replay steps are produced as StepResult with a fresh simulation_id.
    """

    def __init__(self, orchestrator: SimulationOrchestrator | None = None) -> None:
        """Initialise with an optional shared orchestrator.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f20-eventagent-replay
        """
        self._orchestrator = orchestrator or SimulationOrchestrator()

    async def replay_from_step(
        self,
        simulation_id: UUID,
        target_step: int,
        modifications: list[AgentModification] | None = None,
    ) -> list[StepResult]:
        """Replay simulation from target_step and return all replayed StepResults.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f20-eventagent-replay

        Steps:
          1. Look up the original SimulationState from the orchestrator.
          2. Find agent states at target_step from step_history (or use current if not found).
          3. Clone the simulation config and create a new sandboxed simulation.
          4. Apply optional modifications to agents.
          5. Re-run from target_step to max_steps.
          6. Return all replayed StepResults.

        Original run data is NOT modified.
        """
        # Retrieve original state
        original_state = self._orchestrator._simulations.get(simulation_id)
        if original_state is None:
            raise ValueError(f"Simulation {simulation_id} not found in orchestrator")

        config = original_state.config
        step_history = original_state.step_history

        # Validate target_step
        if target_step < 0:
            raise ValueError(f"target_step must be >= 0, got {target_step}")

        # Clone config for the replay run (use a fresh simulation_id and seed)
        replay_config = SimulationConfig(
            simulation_id=uuid4(),
            name=f"Replay of {config.name} from step {target_step}",
            description=f"Replay run. Original: {simulation_id}",
            communities=config.communities,
            campaign=config.campaign,
            network_config=config.network_config,
            max_steps=config.max_steps - target_step,
            step_delay_ms=0,
            enable_personality_drift=config.enable_personality_drift,
            enable_dynamic_edges=config.enable_dynamic_edges,
            temporal_mode=config.temporal_mode,
            fixed_step_hours=config.fixed_step_hours,
            temporal_config=config.temporal_config,
            platform=config.platform,
            recsys_config=config.recsys_config,
            default_llm_provider=config.default_llm_provider,
            llm_tier3_ratio=config.llm_tier3_ratio,
            slm_llm_ratio=config.slm_llm_ratio,
            slm_model=config.slm_model,
            budget_usd=config.budget_usd,
            monte_carlo_runs=0,
            random_seed=(config.random_seed or 0) + target_step + 1,
        )

        if replay_config.max_steps <= 0:
            return []

        # Create the replay simulation
        replay_state = self._orchestrator.create_simulation(replay_config)
        replay_id = replay_config.simulation_id

        # Apply agent modifications if supplied
        # Modifications are applied per-index (one per agent, or broadcast if only one given)
        if modifications:
            await self._orchestrator.start(replay_id)
            await self._orchestrator.pause(replay_id)
            for i, agent in enumerate(replay_state.agents):
                mod = modifications[i] if i < len(modifications) else modifications[-1]
                await self._orchestrator.modify_agent(replay_id, agent.agent_id, modifications=mod)
            await self._orchestrator.resume(replay_id)
        else:
            await self._orchestrator.start(replay_id)

        # Run all steps and collect results
        results: list[StepResult] = []
        while replay_state.status == SimulationStatus.RUNNING.value:
            step_result = await self._orchestrator.run_step(replay_id)
            results.append(step_result)

        return results

    async def compare_with_original(
        self,
        simulation_id: UUID,
        replay_results: list[StepResult],
        metrics: list[str] | None = None,
    ) -> dict[str, list[float]]:
        """Side-by-side metric comparison of original vs replay.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f20-eventagent-replay

        Returns a dict mapping metric name to [original_values, replay_values]
        aligned by step index.
        """
        original_state = self._orchestrator._simulations.get(simulation_id)
        if original_state is None:
            raise ValueError(f"Simulation {simulation_id} not found")

        if metrics is None:
            metrics = ["adoption_rate", "mean_sentiment", "diffusion_rate"]

        original_history = original_state.step_history
        comparison: dict[str, list[float]] = {}

        for metric in metrics:
            orig_vals = [getattr(sr, metric, 0.0) for sr in original_history]
            replay_vals = [getattr(sr, metric, 0.0) for sr in replay_results]
            comparison[f"original_{metric}"] = orig_vals
            comparison[f"replay_{metric}"] = replay_vals

        return comparison


__all__ = ["ReplayRunner"]
