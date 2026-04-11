"""Thread message capture from agent tick results.
SPEC: docs/spec/22_CONVERSATION_THREAD_SPEC.md#CT-03
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.engine.agent.schema import AgentAction, AgentState
from app.engine.agent.tick import AgentTickResult


# Actions that produce visible thread messages
_VISIBLE_ACTIONS = {AgentAction.COMMENT, AgentAction.SHARE, AgentAction.REPOST, AgentAction.ADOPT}

# Stance-derived templates for Tier 1/2 agents (no LLM content)
_STANCE_TEMPLATES = {
    "positive": [
        "This campaign message makes a compelling point. Worth sharing.",
        "The data supports this — I'm seeing real engagement around me.",
        "Strong initiative. The community should pay attention to this.",
    ],
    "negative": [
        "I'm not convinced by this campaign. The evidence is weak.",
        "This feels like hype. Let's wait for more data before committing.",
        "Several concerns remain unaddressed. I'm staying skeptical.",
    ],
    "neutral": [
        "Interesting perspective. Still forming my opinion on this.",
        "The campaign raises valid points, but I need more context.",
        "Watching how this develops before making any judgment.",
    ],
}


@dataclass
class CapturedMessage:
    """A thread message captured during a simulation step.
    SPEC: docs/spec/22_CONVERSATION_THREAD_SPEC.md#CT-01
    """
    message_id: UUID
    simulation_id: UUID
    community_id: UUID
    agent_id: UUID
    step: int
    action: str
    content: str
    belief: float
    emotion_valence: float
    reply_to_id: UUID | None


def _stance_content(belief: float, seed: int) -> str:
    """Pick stance-based template content for Tier 1/2 agents."""
    if belief > 0.1:
        templates = _STANCE_TEMPLATES["positive"]
    elif belief < -0.1:
        templates = _STANCE_TEMPLATES["negative"]
    else:
        templates = _STANCE_TEMPLATES["neutral"]
    return templates[seed % len(templates)]


def collect_thread_messages(
    community_id: UUID,
    simulation_id: UUID,
    step: int,
    tick_results: list[AgentTickResult],
    agents: dict[UUID, AgentState],
    campaign_message: str = "",
) -> list[CapturedMessage]:
    """Extract thread messages from agent actions in a step.

    SPEC: docs/spec/22_CONVERSATION_THREAD_SPEC.md#CT-03

    Rules:
    - IGNORE actions do not produce messages
    - COMMENT/SHARE/REPOST/ADOPT produce messages
    - Content: PropagationEvent.generated_content (Tier 3) or stance template (Tier 1/2)
    - reply_to_id: first propagation target neighbor (if any)
    """
    messages: list[CapturedMessage] = []

    for result in tick_results:
        if result.action not in _VISIBLE_ACTIONS:
            continue

        agent = result.updated_state
        emotion = agent.emotion
        emotion_valence = (emotion.interest + emotion.trust + emotion.excitement) / 3.0

        # Determine content
        generated = None
        reply_to: UUID | None = None
        for pe in result.propagation_events:
            if pe.generated_content:
                generated = pe.generated_content
            if reply_to is None and pe.target_agent_id != agent.agent_id:
                reply_to = pe.target_agent_id

        if generated:
            content = generated
        elif campaign_message:
            content = campaign_message
        else:
            seed = hash(agent.agent_id) + step
            content = _stance_content(agent.belief, seed)

        messages.append(CapturedMessage(
            message_id=uuid4(),
            simulation_id=simulation_id,
            community_id=community_id,
            agent_id=agent.agent_id,
            step=step,
            action=result.action.value,
            content=content,
            belief=agent.belief,
            emotion_valence=emotion_valence,
            reply_to_id=reply_to,
        ))

    return messages
