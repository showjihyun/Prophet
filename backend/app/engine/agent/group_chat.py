"""Group Chat — multi-agent LLM discussion within a simulation.
SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#group-chat-action
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.engine.agent.schema import AgentState

logger = logging.getLogger(__name__)


@dataclass
class GroupMessage:
    agent_id: UUID
    content: str
    step: int
    sentiment: float  # -1.0 to 1.0


@dataclass
class GroupChat:
    group_id: UUID = field(default_factory=uuid4)
    members: list[UUID] = field(default_factory=list)
    topic: str = ""
    messages: list[GroupMessage] = field(default_factory=list)

    def add_message(
        self, agent_id: UUID, content: str, step: int, sentiment: float = 0.0
    ) -> GroupMessage:
        msg = GroupMessage(
            agent_id=agent_id, content=content, step=step, sentiment=sentiment
        )
        self.messages.append(msg)
        return msg

    def get_messages(self, last_n: int = 20) -> list[GroupMessage]:
        return self.messages[-last_n:]

    @property
    def member_count(self) -> int:
        return len(self.members)

    @property
    def message_count(self) -> int:
        return len(self.messages)


class GroupChatManager:
    """Manages group chat sessions with LLM-generated agent messages.
    SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#group-chat-action
    """

    def __init__(self, gateway: object | None = None, llm_adapter: object | None = None) -> None:
        self._chats: dict[UUID, GroupChat] = {}
        self._gateway = gateway
        self._llm_adapter = llm_adapter

    def create_group(self, members: list[UUID], topic: str) -> GroupChat:
        chat = GroupChat(members=members, topic=topic)
        self._chats[chat.group_id] = chat
        return chat

    def get_group(self, group_id: UUID) -> GroupChat:
        if group_id not in self._chats:
            raise KeyError(f"Group {group_id} not found")
        return self._chats[group_id]

    def list_groups(self) -> list[GroupChat]:
        return list(self._chats.values())

    def add_message(
        self,
        group_id: UUID,
        agent_id: UUID,
        content: str,
        step: int,
        sentiment: float = 0.0,
    ) -> GroupMessage:
        chat = self.get_group(group_id)
        if agent_id not in chat.members:
            raise ValueError(
                f"Agent {agent_id} is not a member of group {group_id}"
            )
        return chat.add_message(agent_id, content, step, sentiment)

    async def generate_responses(
        self,
        group_id: UUID,
        agents: dict[UUID, AgentState],
        researcher_message: str,
        step: int,
    ) -> list[GroupMessage]:
        """Generate LLM responses from all group members to a researcher message.

        Adds the researcher message first, then each agent responds in-character via LLM.
        Falls back to rule-based responses if no LLM is available.
        """
        chat = self.get_group(group_id)
        generated: list[GroupMessage] = []

        for member_id in chat.members:
            agent = agents.get(member_id)
            if agent is None:
                continue

            response_text = await self._generate_agent_message(agent, chat, researcher_message)
            sentiment = agent.belief  # use belief as sentiment proxy
            msg = chat.add_message(member_id, response_text, step, sentiment)
            generated.append(msg)

        return generated

    async def _generate_agent_message(
        self, agent: AgentState, chat: GroupChat, prompt_text: str,
    ) -> str:
        """Generate a single agent's response via LLM or fallback."""
        if self._gateway is None and self._llm_adapter is None:
            return self._rule_based_response(agent, chat.topic)

        try:
            from app.llm.schema import LLMPrompt, LLMOptions

            agent_type_str = (
                agent.agent_type.value if hasattr(agent.agent_type, "value") else agent.agent_type
            )

            # Build conversation history context (sanitize to prevent prompt injection)
            recent = chat.get_messages(last_n=5)
            def _sanitize(text: str, max_len: int = 300) -> str:
                clean = text.replace("\n", " ").strip()[:max_len]
                return clean
            history = "\n".join(
                f"Agent {m.agent_id}: {_sanitize(m.content)}" for m in recent
            ) if recent else "(no previous messages)"

            system = (
                f"You are agent {agent.agent_id} ({agent_type_str}) in a group discussion "
                f"about '{chat.topic}'. "
                f"Your belief about the topic: {agent.belief:.2f} (-1=negative, 1=positive). "
                f"Your personality: openness={agent.personality.openness:.1f}, "
                f"skepticism={agent.personality.skepticism:.1f}. "
                f"Your emotions: trust={agent.emotion.trust:.1f}, excitement={agent.emotion.excitement:.1f}. "
                f"Recent conversation:\n{history}\n\n"
                f"Respond naturally and concisely in 1-3 sentences. Stay in character."
            )
            prompt = LLMPrompt(system=system, user=prompt_text, response_format="text", max_tokens=150)
            options = LLMOptions(temperature=0.9, timeout_seconds=10.0)

            if self._gateway is not None:
                response = await self._gateway.call(prompt, task_type="cognition", tier=3, options=options)
            else:
                response = await self._llm_adapter.complete(prompt, options)

            return response.content.strip()
        except Exception:
            logger.warning("LLM group chat failed for agent %s, using fallback", agent.agent_id)
            return self._rule_based_response(agent, chat.topic)

    @staticmethod
    def _rule_based_response(agent: AgentState, topic: str) -> str:
        if agent.belief > 0.5:
            return f"I'm quite positive about {topic}. It aligns with my views."
        elif agent.belief > 0:
            return f"I'm cautiously optimistic about {topic}."
        elif agent.belief > -0.5:
            return f"I have some concerns about {topic}."
        else:
            return f"I'm skeptical about {topic}. I don't think it's a good idea."

    def delete_group(self, group_id: UUID) -> None:
        if group_id not in self._chats:
            raise KeyError(f"Group {group_id} not found")
        del self._chats[group_id]
