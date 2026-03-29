"""Agent Interview — query agents mid-simulation.
SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#interview-action
"""
from dataclasses import dataclass
from uuid import UUID

from app.engine.agent.schema import AgentState


@dataclass
class InterviewResponse:
    agent_id: UUID
    question: str
    answer: str
    belief: float
    confidence: float
    reasoning: str


class AgentInterviewer:
    """Query an agent about their current state and decisions.
    SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#interview-action
    """

    def interview(
        self,
        agent: AgentState,
        question: str,
    ) -> InterviewResponse:
        """Generate a response based on agent's current state.

        Uses rule-based reasoning (Tier 1/2). Async LLM path for Tier 3.
        The response reflects the agent's personality, emotion, and belief.
        """
        personality = agent.personality
        emotion = agent.emotion

        # Determine stance from belief
        if agent.belief > 0.5:
            stance = "strongly positive"
        elif agent.belief > 0:
            stance = "mildly positive"
        elif agent.belief > -0.5:
            stance = "mildly negative"
        else:
            stance = "strongly negative"

        agent_type_str = (
            agent.agent_type.value
            if hasattr(agent.agent_type, "value")
            else agent.agent_type
        )

        reasoning = (
            f"As a {agent_type_str} "
            f"with openness={personality.openness:.1f} and "
            f"skepticism={personality.skepticism:.1f}, "
            f"my current stance is {stance} (belief={agent.belief:.2f}). "
            f"My trust level is {emotion.trust:.1f} and "
            f"excitement is {emotion.excitement:.1f}."
        )

        # Confidence based on how extreme the belief is
        confidence = min(1.0, abs(agent.belief) + 0.3)

        # Answer based on belief direction
        if agent.belief > 0:
            answer = f"I'm {stance} about this. {reasoning}"
        else:
            answer = f"I'm {stance}. {reasoning}"

        return InterviewResponse(
            agent_id=agent.agent_id,
            question=question,
            answer=answer,
            belief=agent.belief,
            confidence=confidence,
            reasoning=reasoning,
        )
