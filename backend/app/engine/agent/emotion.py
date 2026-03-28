"""Layer 3: Emotion — updates agent emotional state based on environmental signals.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-3-emotionlayer
"""
from app.engine.agent.schema import AgentEmotion


class EmotionLayer:
    """Updates agent emotional state based on environmental signals.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-3-emotionlayer

    Update formula (applied to each emotion dimension independently):
        E_i(t+1) = clamp(E_i(t) + signal_deltas - decay, 0.0, 1.0)

    Signal application per dimension:
        interest:   += media_signal * 0.5 + social_signal * 0.3 + expert_signal * 0.2
        trust:      += expert_signal * 0.5 + social_signal * 0.3 + media_signal * 0.2
        skepticism: -= expert_signal * 0.3 (positive expert reduces skepticism)
                    += media_signal * 0.1  (ads can increase skepticism)
        excitement: += media_signal * 0.4 + social_signal * 0.4 + expert_signal * 0.2
    """

    def update(
        self,
        current_emotion: AgentEmotion,
        social_signal: float,
        media_signal: float,
        expert_signal: float,
        decay: float = 0.05,
    ) -> AgentEmotion:
        """Updates all emotion dimensions and returns new clamped AgentEmotion.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-3-emotionlayer

        Determinism: Pure function. Same inputs -> same output.
        Side Effects: None.
        """
        if decay < 0.0:
            raise ValueError(f"decay must be >= 0.0, got {decay}")

        # Clamp current emotion before processing
        c = current_emotion.clamped()

        # Interest: media * 0.5 + social * 0.3 + expert * 0.2
        interest = c.interest + media_signal * 0.5 + social_signal * 0.3 + expert_signal * 0.2 - decay

        # Trust: expert * 0.5 + social * 0.3 + media * 0.2
        trust = c.trust + expert_signal * 0.5 + social_signal * 0.3 + media_signal * 0.2 - decay

        # Skepticism: -expert * 0.3 + media * 0.1
        skepticism = c.skepticism - expert_signal * 0.3 + media_signal * 0.1 - decay

        # Excitement: media * 0.4 + social * 0.4 + expert * 0.2
        excitement = c.excitement + media_signal * 0.4 + social_signal * 0.4 + expert_signal * 0.2 - decay

        return AgentEmotion(
            interest=max(0.0, min(1.0, interest)),
            trust=max(0.0, min(1.0, trust)),
            skepticism=max(0.0, min(1.0, skepticism)),
            excitement=max(0.0, min(1.0, excitement)),
        )

    def emotion_factor(self, emotion: AgentEmotion) -> float:
        """Computes scalar factor for diffusion probability.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-3-emotionlayer

        Formula:
            factor = emotion.excitement - emotion.skepticism
            return clamp(factor, -1.0, 1.0)

        Determinism: Pure function.
        Side Effects: None.
        """
        factor = emotion.excitement - emotion.skepticism
        return max(-1.0, min(1.0, factor))


__all__ = ["EmotionLayer"]
