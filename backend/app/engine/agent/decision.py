"""Layer 5: Decision — converts cognition results into probabilistic action selection.

SPEC: docs/spec/01_AGENT_SPEC.md#layer-5-decisionlayer
SPEC: docs/spec/26_DIFFUSION_CALIBRATION_SPEC.md (Round 7-c)

Round 7-c calibration: previously this layer used a hard
``personality.skepticism > 0.7`` threshold to apply skeptic penalties,
which meant agents at 0.69 vs 0.71 had wildly different behavior. Combined
with agent jitter (±0.15) at instantiation, this caused community-level
differentiation to wash out — all communities converged to the same
adoption trajectory regardless of their declared personality_profile.

The new model:
  1. Graduated skepticism penalty (no hard threshold) — penalty grows
     linearly with the trait value, so a community averaging 0.85
     consistently gets a stronger headwind than one averaging 0.45.
  2. ``agent_type`` multipliers — SKEPTIC and EARLY_ADOPTER now have
     direct, type-level biases on positive actions, on top of the
     personality-driven graduated penalty.
"""
import math
import random as stdlib_random
from uuid import UUID

from app.engine.agent.schema import (
    AgentAction,
    AgentPersonality,
    AgentType,
    ACTION_WEIGHT,
)
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

# Round 7-c: per-agent-type multipliers on positive actions.
#
# These act in addition to the graduated personality penalties below.
# A SKEPTIC with low personality.skepticism still gets the type penalty;
# an EARLY_ADOPTER with low personality.openness still gets the type boost.
# This is what gives community-level diffusion the dramatic differentiation
# that was missing pre-Round 7.
_AGENT_TYPE_POSITIVE_MULTIPLIER: dict[AgentType, float] = {
    AgentType.SKEPTIC:        0.55,   # ~45% headwind on positive actions
    AgentType.CONSUMER:       1.00,   # baseline
    AgentType.EARLY_ADOPTER:  1.45,   # ~45% tailwind
    AgentType.INFLUENCER:     1.30,   # ~30% tailwind
    AgentType.EXPERT:         0.90,   # slightly cautious
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
        agent_type: AgentType | None = None,
    ) -> AgentAction:
        """Selects an action via softmax sampling.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-5-decisionlayer
        SPEC: docs/spec/26_DIFFUSION_CALIBRATION_SPEC.md (Round 7-c)

        :param agent_type: optional — when provided, applies type-level
            multipliers (skeptic headwind, early-adopter tailwind, etc.)
            on top of personality-driven graduated penalties. Old callers
            that pass only personality keep working with neutral baseline.

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

        # Step 3: Apply personality modifiers.
        #
        # Round 7-c: replaced hard ``> 0.7`` thresholds with graduated
        # responses so personality drift across communities (configured
        # via personality_profile) actually flows through to behavior.
        if personality.openness > 0.7:
            action_scores[AgentAction.SEARCH] *= 1.5
        if personality.trend_following > 0.7:
            action_scores[AgentAction.SHARE] *= 1.5
            action_scores[AgentAction.REPOST] *= 1.5

        # Graduated skepticism penalty: scales linearly from 0 (when
        # skepticism=0.5, baseline) to a strong headwind (when
        # skepticism=1.0). Below 0.5 there is no penalty.
        skep_excess = max(0.0, personality.skepticism - 0.5)
        if skep_excess > 0:
            mute_boost = 1.0 + skep_excess * 1.4    # up to 1.7x
            ignore_boost = 1.0 + skep_excess * 1.6  # up to 1.8x
            action_scores[AgentAction.MUTE] *= mute_boost
            action_scores[AgentAction.IGNORE] *= ignore_boost
            # Strong, graduated penalty on positive actions.
            penalty = personality.skepticism * 1.4  # up to 1.4 absolute hit
            for action in _POSITIVE_ACTIONS:
                action_scores[action] -= penalty

        if personality.brand_loyalty > 0.7:
            action_scores[AgentAction.ADOPT] *= 1.3

        # Step 3b — Round 7-c: per-agent-type multiplier on positive actions.
        # This is what produces community-level differentiation: a SKEPTIC
        # community has a structural headwind on adoption that no amount
        # of social pressure can fully overcome, while an EARLY_ADOPTER
        # community gets a tailwind that pushes them through.
        if agent_type is not None:
            type_mult = _AGENT_TYPE_POSITIVE_MULTIPLIER.get(agent_type, 1.0)
            if type_mult != 1.0:
                for action in _POSITIVE_ACTIONS:
                    action_scores[action] *= type_mult

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
