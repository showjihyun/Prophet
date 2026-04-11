"""Personality Drift — optional personality evolution based on cumulative experience.
SPEC: docs/spec/01_AGENT_SPEC.md#personality-drift
"""
from __future__ import annotations

from app.engine.agent.schema import AgentAction, AgentEmotion, AgentPersonality

# Default max drift if not injected via constructor
_DEFAULT_MAX_DRIFT = 0.3


class PersonalityDrift:
    """Optional personality evolution based on cumulative experience.

    SPEC: docs/spec/01_AGENT_SPEC.md#personality-drift

    Formula:
        P_dim(t+1) = clamp(P_dim(t) + learning_rate * delta_dim, 0.0, 1.0)

    Drift limits:
        Max drift per dimension per simulation: 0.3
    """

    DRIFT_TABLE: dict[AgentAction, dict[str, float]] = {
        AgentAction.ADOPT:   {"openness": 0.01, "brand_loyalty": 0.02},
        AgentAction.SHARE:   {"social_influence": 0.01, "trend_following": 0.01},
        AgentAction.REPOST:  {"trend_following": 0.005},
        AgentAction.COMMENT: {"openness": 0.005},
        AgentAction.FOLLOW:  {"trend_following": 0.005},
        AgentAction.MUTE:    {"skepticism": 0.01},
    }

    MAX_DRIFT = _DEFAULT_MAX_DRIFT

    def apply_drift(
        self,
        personality: AgentPersonality,
        action: AgentAction,
        cumulative_drift: dict[str, float],
        learning_rate: float = 1.0,
        emotion: AgentEmotion | None = None,
    ) -> tuple[AgentPersonality, dict[str, float]]:
        """Applies personality drift based on action taken, modulated by emotion.

        SPEC: docs/spec/01_AGENT_SPEC.md#personality-drift
        SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#4 — drift↔emotion coupling

        Args:
            personality: Current personality (frozen dataclass -- returns new instance).
            action: Action taken this step.
            cumulative_drift: Running total of drift per dimension.
            learning_rate: Multiplier for drift deltas. Default 1.0.
            emotion: Optional current emotion — modulates drift speed.
                     High excitement accelerates positive-action drift;
                     high skepticism accelerates negative-action drift.

        Returns:
            (new_personality, updated_cumulative_drift)
            If action has no drift entry, returns (personality, cumulative_drift) unchanged.

        Determinism: Pure function.
        Side Effects: None.
        """
        if action not in self.DRIFT_TABLE:
            return personality, cumulative_drift

        # Emotion-modulated learning rate (B2 upgrade)
        if emotion is not None:
            positive_actions = {AgentAction.ADOPT, AgentAction.SHARE, AgentAction.COMMENT, AgentAction.FOLLOW}
            if action in positive_actions:
                learning_rate *= 1.0 + 0.5 * emotion.excitement
            elif action == AgentAction.MUTE:
                learning_rate *= 1.0 + 0.3 * emotion.skepticism

        deltas = self.DRIFT_TABLE[action]
        new_cumulative = dict(cumulative_drift)
        values = {
            "openness": personality.openness,
            "skepticism": personality.skepticism,
            "trend_following": personality.trend_following,
            "brand_loyalty": personality.brand_loyalty,
            "social_influence": personality.social_influence,
        }

        for dim, delta in deltas.items():
            actual_delta = learning_rate * delta
            current_cum = new_cumulative.get(dim, 0.0)

            # Cap at MAX_DRIFT (with float tolerance)
            if abs(current_cum) >= self.MAX_DRIFT - 1e-9:
                continue

            # Limit delta so cumulative doesn't exceed MAX_DRIFT
            remaining = self.MAX_DRIFT - abs(current_cum)
            if abs(actual_delta) > remaining:
                actual_delta = remaining if actual_delta > 0 else -remaining

            values[dim] = max(0.0, min(1.0, values[dim] + actual_delta))
            new_cumulative[dim] = current_cum + actual_delta

        new_personality = AgentPersonality(
            openness=round(values["openness"], 10),
            skepticism=round(values["skepticism"], 10),
            trend_following=round(values["trend_following"], 10),
            brand_loyalty=round(values["brand_loyalty"], 10),
            social_influence=round(values["social_influence"], 10),
        )

        return new_personality, new_cumulative


__all__ = ["PersonalityDrift"]
