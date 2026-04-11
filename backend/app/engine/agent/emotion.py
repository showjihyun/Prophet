"""Layer 3: Emotion — updates agent emotional state based on environmental signals.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-3-emotionlayer
SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1
"""
from app.engine.agent.schema import AgentEmotion

_DEFAULT_CONTAGION_ALPHA = 0.15


class EmotionLayer:
    """Updates agent emotional state based on environmental signals.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-3-emotionlayer
    SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1

    Update formula (applied to each emotion dimension independently):
        E_i(t+1) = clamp(E_i(t) + signal_deltas - decay, 0.0, 1.0)

    Signal application per dimension:
        interest:   += media_signal * 0.5 + social_signal * 0.3 + expert_signal * 0.2
        trust:      += expert_signal * 0.5 + social_signal * 0.3 + media_signal * 0.2
        skepticism: -= expert_signal * 0.3 (positive expert reduces skepticism)
                    += media_signal * 0.1  (ads can increase skepticism)
        excitement: += media_signal * 0.4 + social_signal * 0.4 + expert_signal * 0.2

    Emotional contagion (EC, §1): excitement and skepticism additionally shift
    toward the weighted mean of neighbor emotions by contagion_alpha.
    """

    def __init__(self, contagion_alpha: float = _DEFAULT_CONTAGION_ALPHA) -> None:
        """SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1 EC-02"""
        self._contagion_alpha = contagion_alpha

    def update(
        self,
        current_emotion: AgentEmotion,
        social_signal: float,
        media_signal: float,
        expert_signal: float,
        decay: float = 0.05,
        neighbor_emotions: "list[tuple[AgentEmotion, float]] | None" = None,
    ) -> AgentEmotion:
        """Updates all emotion dimensions and returns new clamped AgentEmotion.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-3-emotionlayer
        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1

        Args:
            neighbor_emotions: Optional list of (AgentEmotion, edge_weight) tuples.
                Applies emotional contagion to excitement and skepticism only (EC-01~04).

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

        # EC-02: Emotional contagion — all 4 dimensions shift toward weighted-mean neighbors
        # Extended: interest + trust now also subject to contagion (B2 upgrade)
        if neighbor_emotions:
            total_weight = sum(w for _, w in neighbor_emotions)
            if total_weight > 0.0:
                mean_interest = sum(e.interest * w for e, w in neighbor_emotions) / total_weight
                mean_trust = sum(e.trust * w for e, w in neighbor_emotions) / total_weight
                mean_excitement = sum(e.excitement * w for e, w in neighbor_emotions) / total_weight
                mean_skepticism = sum(e.skepticism * w for e, w in neighbor_emotions) / total_weight
                interest += self._contagion_alpha * (mean_interest - interest)
                trust += self._contagion_alpha * (mean_trust - trust)
                excitement += self._contagion_alpha * (mean_excitement - excitement)
                skepticism += self._contagion_alpha * (mean_skepticism - skepticism)

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
