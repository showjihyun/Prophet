"""Event-Driven Agent Activation.
SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#event-driven-activation
"""
import random
from uuid import UUID

from app.engine.agent.schema import AgentState


class EventDrivenActivation:
    """Only activate agents that have pending events.

    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#event-driven-activation

    Activation criteria (OR):
      1. Agent has exposure_score > 0
      2. Agent is a propagation target
      3. Agent is subject to an intervention
      4. Random activation at base_activation_rate for idle agents
    """

    def get_active_agents(
        self,
        all_agents: list[AgentState],
        exposure_scores: dict[UUID, float] | None = None,
        propagation_targets: set[UUID] | None = None,
        interventions: set[UUID] | None = None,
        base_activation_rate: float = 0.10,
        seed: int | None = None,
    ) -> list[AgentState]:
        """Return subset of agents that should be activated this step.

        SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md#event-driven-activation
        """
        exposure_scores = exposure_scores or {}
        propagation_targets = propagation_targets or set()
        interventions = interventions or set()

        active: set[UUID] = set()
        inactive: list[AgentState] = []

        for agent in all_agents:
            aid = agent.agent_id
            if exposure_scores.get(aid, 0) > 0:
                active.add(aid)
            elif aid in propagation_targets:
                active.add(aid)
            elif aid in interventions:
                active.add(aid)
            else:
                inactive.append(agent)

        # Random activation of remaining agents
        if inactive and base_activation_rate > 0:
            rng = random.Random(seed)
            k = max(1, int(len(inactive) * base_activation_rate))
            random_active = rng.sample(inactive, min(k, len(inactive)))
            for a in random_active:
                active.add(a.agent_id)

        return [a for a in all_agents if a.agent_id in active]


__all__ = ["EventDrivenActivation"]
