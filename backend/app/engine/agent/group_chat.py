"""Group Chat — multi-agent discussion within a simulation.
SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#group-chat-action
"""
from dataclasses import dataclass, field
from uuid import UUID, uuid4


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
    """Manages group chat sessions within a simulation.
    SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#group-chat-action
    """

    def __init__(self) -> None:
        self._chats: dict[UUID, GroupChat] = {}

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

    def delete_group(self, group_id: UUID) -> None:
        if group_id not in self._chats:
            raise KeyError(f"Group {group_id} not found")
        del self._chats[group_id]
