"""Agent Interview — query agents mid-simulation via LLM.
SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#interview-action
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from uuid import UUID

from app.engine.agent.schema import AgentState

logger = logging.getLogger(__name__)


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

    Uses LLM (Tier 3) when a gateway or adapter is provided.
    Falls back to rule-based reasoning otherwise.
    """

    def __init__(self, gateway: object | None = None, llm_adapter: object | None = None):
        self._gateway = gateway
        self._llm_adapter = llm_adapter

    async def interview_async(
        self,
        agent: AgentState,
        question: str,
    ) -> InterviewResponse:
        """Async interview using LLM Tier 3 for in-character responses.

        Falls back to rule-based interview() on LLM failure.
        """
        if self._gateway is None and self._llm_adapter is None:
            return self.interview(agent, question)

        try:
            from app.llm.schema import LLMPrompt, LLMOptions

            personality = agent.personality
            emotion = agent.emotion
            agent_type_str = (
                agent.agent_type.value if hasattr(agent.agent_type, "value") else agent.agent_type
            )

            system_prompt = (
                f"You are a simulated {agent_type_str} agent in a social network simulation. "
                f"Your personality: openness={personality.openness:.2f}, skepticism={personality.skepticism:.2f}, "
                f"trend_following={personality.trend_following:.2f}, brand_loyalty={personality.brand_loyalty:.2f}. "
                f"Your emotions: trust={emotion.trust:.2f}, excitement={emotion.excitement:.2f}, "
                f"interest={emotion.interest:.2f}, skepticism={emotion.skepticism:.2f}. "
                f"Your current belief about the campaign: {agent.belief:.2f} (range -1 to 1). "
                f"Answer in character. Be concise. Respond in JSON: "
                f'{{"answer": "...", "reasoning": "...", "confidence": 0.0-1.0}}'
            )

            prompt = LLMPrompt(system=system_prompt, user=question, response_format="json")
            options = LLMOptions(temperature=0.8, timeout_seconds=10.0)

            if self._gateway is not None:
                response = await self._gateway.call(prompt, task_type="expert_analysis", tier=3, options=options)
            else:
                response = await self._llm_adapter.complete(prompt, options)

            # Parse LLM response
            parsed = json.loads(response.content) if isinstance(response.content, str) else {}
            answer = parsed.get("answer", response.content)
            reasoning = parsed.get("reasoning", "LLM-generated response")
            confidence = float(parsed.get("confidence", min(1.0, abs(agent.belief) + 0.3)))
            confidence = max(0.0, min(1.0, confidence))

            return InterviewResponse(
                agent_id=agent.agent_id,
                question=question,
                answer=answer,
                belief=agent.belief,
                confidence=confidence,
                reasoning=reasoning,
            )
        except Exception:
            logger.warning("LLM interview failed for agent %s, falling back to rule-based", agent.agent_id)
            return self.interview(agent, question)

    def interview(
        self,
        agent: AgentState,
        question: str,
    ) -> InterviewResponse:
        """Rule-based interview (Tier 1/2 fallback).

        The response reflects the agent's personality, emotion, and belief.
        """
        personality = agent.personality
        emotion = agent.emotion

        if agent.belief > 0.5:
            stance = "strongly positive"
        elif agent.belief > 0:
            stance = "mildly positive"
        elif agent.belief > -0.5:
            stance = "mildly negative"
        else:
            stance = "strongly negative"

        agent_type_str = (
            agent.agent_type.value if hasattr(agent.agent_type, "value") else agent.agent_type
        )

        reasoning = (
            f"As a {agent_type_str} "
            f"with openness={personality.openness:.1f} and "
            f"skepticism={personality.skepticism:.1f}, "
            f"my current stance is {stance} (belief={agent.belief:.2f}). "
            f"My trust level is {emotion.trust:.1f} and "
            f"excitement is {emotion.excitement:.1f}."
        )

        confidence = min(1.0, abs(agent.belief) + 0.3)

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
