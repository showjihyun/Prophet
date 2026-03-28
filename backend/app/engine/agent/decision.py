"""Layer 5: Decision — converts cognition results into probabilistic action selection.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-5-decisionlayer
"""
import math
import random as stdlib_random
from uuid import UUID

from app.engine.agent.schema import AgentAction, AgentPersonality, ACTION_WEIGHT
from app.engine.agent.cognition import CognitionResult
from app.engine.agent.perception import NeighborAction


# All possible actions for softmax
_ALL_ACTIONS = list(AgentAction)

# Positive actions that benefit from social pressure
_POSITIVE_ACTIONS = {
    AgentAction.LIKE, AgentAction.SAVE, AgentAction.COMMENT,
    AgentAction.SHARE, AgentAction.REPOST, AgentAction.ADOPT,
    AgentAction.FOLLOW, AgentAction.SEARCH,
}


class DecisionLayer:
    """Converts cognition results into probabilistic action selection.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-5-decisionlayer

    Algorithm:
        1. Compute base score per action from cognition.evaluation_score
        2. Add social_pressure to positive actions
        3. Apply personality modifiers
        4. Softmax over all action scores -> probability distribution
        5. Sample action from distribution using agent-specific RNG
    """

    def choose_action(
        self,
        cognition: CognitionResult,
        social_pressure: float,
        personality: AgentPersonality,
        agent_seed: int,
    ) -> AgentAction:
        """Selects an action via softmax sampling.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-5-decisionlayer

        Determinism: Deterministic for same seed + inputs.
        Side Effects: None.
        """
        # Clamp social_pressure to [-5.0, 5.0]
        social_pressure = max(-5.0, min(5.0, social_pressure))

        score = cognition.evaluation_score

        # Step 1: Compute base score per action using evaluation_score mapping.
        # Actions closer to the recommended action get higher base scores.
        action_scores: dict[AgentAction, float] = {}
        for action in _ALL_ACTIONS:
            weight = ACTION_WEIGHT[action]
            base = -abs(score - weight) + 1.0
            action_scores[action] = base

        # Give the recommended action a significant boost
        action_scores[cognition.recommended_action] += 2.0

        # For negative scores, also boost nearby negative actions
        if score < -0.5:
            action_scores[AgentAction.IGNORE] += 1.5
            action_scores[AgentAction.MUTE] += 1.0
        elif score < 0.0:
            action_scores[AgentAction.IGNORE] += 1.0
            action_scores[AgentAction.VIEW] += 0.5

        # Step 2: Add social_pressure to positive actions
        for action in _POSITIVE_ACTIONS:
            action_scores[action] += social_pressure * 0.3

        # Add negative social pressure effect
        if social_pressure < 0:
            action_scores[AgentAction.IGNORE] += abs(social_pressure) * 0.3
            action_scores[AgentAction.MUTE] += abs(social_pressure) * 0.2

        # Step 3: Apply personality modifiers
        if personality.openness > 0.7:
            action_scores[AgentAction.SEARCH] *= 1.5
        if personality.trend_following > 0.7:
            action_scores[AgentAction.SHARE] *= 1.5
            action_scores[AgentAction.REPOST] *= 1.5
        if personality.skepticism > 0.7:
            action_scores[AgentAction.MUTE] *= 1.5
            action_scores[AgentAction.IGNORE] *= 1.5
            # High skepticism also penalizes positive actions
            for action in _POSITIVE_ACTIONS:
                action_scores[action] -= personality.skepticism * 0.5
        if personality.brand_loyalty > 0.7:
            action_scores[AgentAction.ADOPT] *= 1.3

        # Step 4: Softmax over all action scores
        # Use temperature to control distribution sharpness
        temperature = 0.5
        max_score = max(action_scores.values())
        exp_scores = {}
        for action, s in action_scores.items():
            exp_scores[action] = math.exp((s - max_score) / temperature)
        total_exp = sum(exp_scores.values())
        probabilities = {action: exp_s / total_exp for action, exp_s in exp_scores.items()}

        # Step 5: Sample action from distribution using agent-specific RNG
        rng = stdlib_random.Random(agent_seed)
        actions_list = list(probabilities.keys())
        probs_list = [probabilities[a] for a in actions_list]

        # Weighted random choice
        r = rng.random()
        cumulative = 0.0
        for action, prob in zip(actions_list, probs_list):
            cumulative += prob
            if r < cumulative:
                return action
        return actions_list[-1]  # fallback

    def compute_social_pressure(
        self,
        agent_id: UUID,
        neighbors: list[NeighborAction],
        trust_matrix: dict[tuple[UUID, UUID], float],
    ) -> float:
        """Computes social pressure from neighbor actions.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-5-decisionlayer

        Formula:
            social_pressure = sum(
                trust_matrix.get((agent_id, n.agent_id), 0.0)
                * ACTION_WEIGHT[n.action]
                for n in neighbors
            )

        Determinism: Pure function.
        Side Effects: None.
        """
        return sum(
            trust_matrix.get((agent_id, n.agent_id), 0.0)
            * ACTION_WEIGHT[n.action]
            for n in neighbors
        )


__all__ = ["DecisionLayer"]
