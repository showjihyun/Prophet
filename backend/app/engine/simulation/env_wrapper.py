"""PettingZoo-compatible environment wrapper.
SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md
Inspired by OASIS's PettingZoo-style `env = oasis.make(); env.step(actions)`
"""
import asyncio
from dataclasses import dataclass
from uuid import UUID
from typing import Any

from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.engine.simulation.schema import SimulationConfig, StepResult


class ProphetEnv:
    """PettingZoo-style wrapper for Prophet simulations.

    SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md

    Usage:
        env = ProphetEnv(config)
        env.reset()

        for step in range(max_steps):
            observations = env.observe()
            result = env.step()  # auto-advances all agents

            if env.done:
                break

        env.close()
    """

    def __init__(self, config: SimulationConfig):
        self._config = config
        self._orch = SimulationOrchestrator()
        self._sim_id: UUID | None = None
        self._current_step = 0
        self._max_steps = config.max_steps
        self._done = False
        self._last_result: StepResult | None = None

    def reset(self) -> dict[str, Any]:
        """Reset environment to initial state. Returns initial observation."""
        state = self._orch.create_simulation(self._config)
        self._sim_id = state.simulation_id
        self._orch.start(self._sim_id)
        self._current_step = 0
        self._done = False
        self._last_result = None
        return self._get_observation()

    def step(self, actions: dict[str, str] | None = None) -> tuple[dict, float, bool, dict]:
        """Execute one step. Returns (observation, reward, done, info).

        Args:
            actions: Optional override actions per agent. If None, agents decide autonomously.

        Returns:
            observation: dict with agent states and metrics
            reward: adoption_rate delta (proxy reward)
            done: True if max_steps reached
            info: StepResult metadata
        """
        if self._done or self._sim_id is None:
            raise RuntimeError("Environment is done or not reset. Call reset() first.")

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self._orch.run_step(self._sim_id))
        finally:
            loop.close()

        prev_adoption = self._last_result.adoption_rate if self._last_result else 0.0
        reward = result.adoption_rate - prev_adoption

        self._last_result = result
        self._current_step += 1
        self._done = self._current_step >= self._max_steps

        observation = self._get_observation()
        info = {
            "step": self._current_step,
            "total_adoption": result.total_adoption,
            "diffusion_rate": result.diffusion_rate,
            "emergent_events": [e.event_type for e in result.emergent_events],
            "action_distribution": result.action_distribution,
        }

        return observation, reward, self._done, info

    def observe(self) -> dict[str, Any]:
        """Get current observation without advancing."""
        return self._get_observation()

    def close(self) -> None:
        """Clean up simulation state."""
        if self._sim_id:
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self._orch.delete_simulation(self._sim_id))
                loop.close()
            except Exception:
                pass
        self._sim_id = None
        self._done = True

    @property
    def done(self) -> bool:
        return self._done

    @property
    def current_step(self) -> int:
        return self._current_step

    @property
    def agents(self) -> list:
        """List of agent IDs in the simulation."""
        if self._sim_id is None:
            return []
        state = self._orch.get_state(self._sim_id)
        return [a.agent_id for a in state.agents]

    def _get_observation(self) -> dict[str, Any]:
        if self._sim_id is None:
            return {}
        state = self._orch.get_state(self._sim_id)
        return {
            "step": self._current_step,
            "agent_count": len(state.agents),
            "adoption_rate": self._last_result.adoption_rate if self._last_result else 0.0,
            "mean_sentiment": self._last_result.mean_sentiment if self._last_result else 0.0,
            "done": self._done,
        }


__all__ = ["ProphetEnv"]
