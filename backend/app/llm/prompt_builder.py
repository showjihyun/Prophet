"""Prompt construction for agent cognition, expert analysis, and memory reflection.
SPEC: docs/spec/05_LLM_SPEC.md#5-prompt-builder
"""
from __future__ import annotations

from typing import Any

from app.llm.schema import LLMPrompt


class PromptBuilder:
    """Builds structured LLM prompts per SPEC templates.

    SPEC: docs/spec/05_LLM_SPEC.md#5-prompt-builder

    All methods return LLMPrompt with response_format="json".
    """

    def build_agent_cognition_prompt(
        self,
        agent: Any,
        perception: Any,
        memories: list[Any],
        campaign: Any,
    ) -> LLMPrompt:
        """Build prompt for agent cognition (Tier 3 evaluation).

        SPEC: docs/spec/05_LLM_SPEC.md#5-prompt-builder

        System: agent identity + personality + response format
        User: campaign exposure + memories + emotion + neighbor actions
        """
        # Extract personality values
        personality = agent.personality
        emotion = agent.emotion

        system = (
            f"You are simulating agent {agent.agent_id}, "
            f"a {agent.agent_type.value if hasattr(agent.agent_type, 'value') else agent.agent_type} "
            f"in community {agent.community_id}.\n"
            f"Your personality: openness={personality.openness}, "
            f"skepticism={personality.skepticism}, "
            f"trend_following={personality.trend_following}, "
            f"brand_loyalty={personality.brand_loyalty}, "
            f"social_influence={personality.social_influence}\n"
            f"Respond ONLY in JSON with keys: evaluation_score, "
            f"recommended_action, reasoning, confidence"
        )

        # Top 3 memories
        top_memories = memories[:3]
        memories_text = "; ".join(
            getattr(m, "content", str(m)) for m in top_memories
        ) if top_memories else "None"

        # Neighbor action summary from social signals
        neighbor_summary = "None"
        if hasattr(perception, "social_signals") and perception.social_signals:
            actions = [
                f"{s.neighbor_id}: {s.action.value if hasattr(s.action, 'value') else s.action}"
                for s in perception.social_signals[:5]
            ]
            neighbor_summary = "; ".join(actions)

        # Campaign message
        campaign_message = getattr(campaign, "message", str(campaign))

        user = (
            f"You have been exposed to: {campaign_message}\n"
            f"Your recent memories: {memories_text}\n"
            f"Your current emotion: interest={emotion.interest}, "
            f"trust={emotion.trust}, skepticism={emotion.skepticism}, "
            f"excitement={emotion.excitement}\n"
            f"Your neighbors' actions: {neighbor_summary}\n\n"
            f"Evaluate this content and decide your action.\n"
            f"Actions available: ignore, view, search, like, save, comment, "
            f"share, repost, follow, unfollow, adopt, mute\n"
            f"evaluation_score: float from -2.0 to 2.0\n"
            f"confidence: float from 0.0 to 1.0"
        )

        return LLMPrompt(
            system=system,
            user=user,
            context={
                "agent_id": str(agent.agent_id),
                "agent_type": agent.agent_type.value if hasattr(agent.agent_type, "value") else str(agent.agent_type),
                "community_id": str(agent.community_id),
            },
            response_format="json",
            max_tokens=512,
        )

    def build_expert_analysis_prompt(
        self,
        expert: Any,
        campaign: Any,
        sentiment: Any,
        memories: list[Any],
    ) -> LLMPrompt:
        """Build prompt for expert analysis.

        SPEC: docs/spec/05_LLM_SPEC.md#5-prompt-builder

        System: expert role + objective analysis + JSON format
        User: campaign info + community sentiment + feedback
        """
        expert_type = expert.agent_type.value if hasattr(expert.agent_type, "value") else str(expert.agent_type)

        system = (
            f"You are an expert analyst (role: {expert_type}).\n"
            f"Analyze the following product/campaign objectively.\n"
            f"Respond in JSON: score (float -1 to 1), reasoning (str), confidence (float)"
        )

        # Top memories summary
        memories_text = "; ".join(
            getattr(m, "content", str(m)) for m in memories[:3]
        ) if memories else "None"

        campaign_name = getattr(campaign, "name", "Unknown")
        campaign_message = getattr(campaign, "message", str(campaign))
        mean_belief = getattr(sentiment, "mean_belief", 0.0)
        adoption_rate = getattr(sentiment, "adoption_rate", 0.0)

        user = (
            f"Campaign: {campaign_name} - {campaign_message}\n"
            f"Current community sentiment: {mean_belief}\n"
            f"Adoption rate: {adoption_rate}\n"
            f"Key community feedback: {memories_text}"
        )

        return LLMPrompt(
            system=system,
            user=user,
            context={
                "expert_id": str(expert.agent_id),
                "campaign_name": campaign_name,
            },
            response_format="json",
            max_tokens=512,
        )

    def build_memory_reflection_prompt(
        self,
        agent: Any,
        recent_events: list[Any],
    ) -> LLMPrompt:
        """Build prompt for memory reflection (belief update).

        SPEC: docs/spec/05_LLM_SPEC.md#5-prompt-builder

        Triggered when repeated_event_count > threshold (default: 5 similar memories).
        Generates high-level belief update.
        """
        events_summary = "; ".join(
            getattr(e, "content", str(e)) for e in recent_events
        ) if recent_events else "None"

        system = (
            f"You are simulating agent {agent.agent_id}.\n"
            f"You are reflecting on repeated experiences.\n"
            f"Respond in JSON: belief_delta (float -0.5 to 0.5), insight (str)"
        )

        user = (
            f"You have experienced these events multiple times: {events_summary}\n"
            f"What conclusion do you draw? Update your belief on the product/campaign.\n"
            f"Respond in JSON: belief_delta (float -0.5 to 0.5), insight (str)"
        )

        return LLMPrompt(
            system=system,
            user=user,
            context={
                "agent_id": str(agent.agent_id),
                "event_count": len(recent_events),
            },
            response_format="json",
            max_tokens=256,
        )


__all__ = ["PromptBuilder"]
