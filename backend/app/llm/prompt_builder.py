"""Prompt construction for agent cognition, expert analysis, and memory reflection.
SPEC: docs/spec/05_LLM_SPEC.md#5-prompt-builder
SPEC: docs/spec/19_SIMULATION_QUALITY_SPEC.md#sq-04
SPEC: docs/spec/20_SIMULATION_QUALITY_P2_SPEC.md#§3
"""
from __future__ import annotations

import re
from typing import Any

from app.llm.schema import LLMPrompt

# SQ-04: 프롬프트 구조 토큰 — 사용자 콘텐츠에서 제거해야 할 패턴
_INJECTION_PATTERNS = re.compile(
    r"---|###|\"\"\"|\'\'\'"
    r"|<\||\|>"
    r"|\[INST\]|\[/INST\]"
    r"|<system>|</system>"
    r"|<\|im_start\|>|<\|im_end\|>"
    r"|<\|endoftext\|>",
    re.IGNORECASE,
)
_MAX_CONTENT_LENGTH = 500


class PromptBuilder:
    """Builds structured LLM prompts per SPEC templates.

    SPEC: docs/spec/05_LLM_SPEC.md#5-prompt-builder

    All methods return LLMPrompt with response_format="json".
    """

    def sanitize_content(self, content: str) -> str:
        """사용자/캠페인 제공 콘텐츠에서 프롬프트 인젝션 패턴을 제거한다.

        SPEC: docs/spec/19_SIMULATION_QUALITY_SPEC.md#sq-04

        처리 규칙:
        1. 500자 초과 시 잘라내기 + "[truncated]" 추가
        2. 프롬프트 구조 토큰 → "[SEP]" 대체
        3. 연속 3개 이상 개행 → 2개로 압축
        4. null byte / non-printable 제거
        """
        if not content:
            return content

        # 1. 길이 제한
        if len(content) > _MAX_CONTENT_LENGTH:
            content = content[:_MAX_CONTENT_LENGTH] + "...[truncated]"

        # 2. 프롬프트 구조 토큰 격리
        content = _INJECTION_PATTERNS.sub("[SEP]", content)

        # 3. 연속 개행 압축
        content = re.sub(r"\n{3,}", "\n\n", content)

        # 4. non-printable 제거 (개행/탭 제외)
        content = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", content)

        return content

    def build_agent_cognition_prompt(
        self,
        agent: Any,
        perception: Any,
        memories: list[Any],
        campaign: Any,
    ) -> LLMPrompt:
        """Build prompt for agent cognition (Tier 3 evaluation).

        SPEC: docs/spec/05_LLM_SPEC.md#5-prompt-builder
        SPEC: docs/spec/19_SIMULATION_QUALITY_SPEC.md#sq-04

        System: agent identity + personality + response format
        User: campaign exposure (격리) + memories + emotion + neighbor actions
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

        # SQ-04: 캠페인 메시지 sanitize + 명시적 XML 경계로 격리
        raw_campaign_message = getattr(campaign, "message", str(campaign))
        campaign_message = self.sanitize_content(raw_campaign_message)

        user = (
            f"<campaign_content>\n{campaign_message}\n</campaign_content>\n"
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


    def build_content_generation_prompt(
        self,
        agent: Any,
        original_content: str,
        action: Any,
        step: int,
    ) -> LLMPrompt:
        """Build prompt for Tier 3 agent content generation (SHARE/COMMENT).

        SPEC: docs/spec/20_SIMULATION_QUALITY_P2_SPEC.md#§3 CG-01/CG-02

        Generates a short user post (≤ 140 chars) reflecting agent's personal framing.
        Response format: JSON with key generated_text (str).
        """
        agent_id = str(agent.agent_id)
        agent_type = agent.agent_type.value if hasattr(agent.agent_type, "value") else str(agent.agent_type)
        action_str = action.value if hasattr(action, "value") else str(action)

        system = (
            f"You are simulating agent {agent_id}, a {agent_type} in community {agent.community_id}.\n"
            f"You are performing a {action_str} action on social media.\n"
            f"Write a short authentic post (≤ 140 characters) in your voice.\n"
            f"Respond ONLY in JSON with key: generated_text"
        )

        # CG-02: sanitize original content before embedding in prompt
        safe_content = self.sanitize_content(original_content)

        user = (
            f"Original content you are reacting to:\n"
            f"<source_content>\n{safe_content}\n</source_content>\n\n"
            f"Action: {action_str} (step {step})\n"
            f"Write your short {action_str} post (≤ 140 chars). "
            f"Make it personal and authentic to your perspective.\n"
            f"Respond in JSON: {{\"generated_text\": \"...\"}}"
        )

        return LLMPrompt(
            system=system,
            user=user,
            context={
                "agent_id": agent_id,
                "action": action_str,
                "step": step,
            },
            response_format="json",
            max_tokens=128,
        )


__all__ = ["PromptBuilder"]
