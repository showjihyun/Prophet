"""Agent Reflection Engine — periodic belief revision from accumulated experience.

SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1

Simulacra-style (Park et al. 2023): agents periodically reflect on accumulated
memories to update their beliefs. Triggered by memory count or step interval.
"""
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.engine.agent.memory import MemoryRecord


@dataclass
class ReflectionInput:
    """Structured input for reflection processing.

    SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1 RF-02
    """
    agent_id: UUID
    recent_memories: list[MemoryRecord]
    current_belief: float
    step: int


@dataclass
class ReflectionResult:
    """Output of reflection processing.

    SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1 RF-02
    """
    belief_delta: float         # [-0.3, 0.3]
    insight: str                # 1-line summary of what agent "learned"
    new_memories_generated: int # count of synthetic semantic memories created


class ReflectionEngine:
    """Periodic reflection engine for agent belief revision.

    SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1

    Tier 1/2 agents use heuristic reflection (deterministic).
    Tier 3 agents use LLM via PromptBuilder.build_memory_reflection_prompt().
    """

    def __init__(
        self,
        memory_threshold: int = 5,
        step_interval: int = 10,
        reflection_weight: float = 0.2,
    ) -> None:
        """SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1 RF-03"""
        self._memory_threshold = memory_threshold
        self._step_interval = step_interval
        self._reflection_weight = reflection_weight

    def should_reflect(
        self,
        memory_count_since_last: int,
        step: int,
        last_reflection_step: int,
    ) -> bool:
        """Returns True when agent should perform reflection.

        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1 RF-01

        Conditions (ANY triggers reflection):
        - memory_count_since_last >= MEMORY_THRESHOLD
        - step - last_reflection_step >= STEP_INTERVAL
        """
        if memory_count_since_last >= self._memory_threshold:
            return True
        if step - last_reflection_step >= self._step_interval:
            return True
        return False

    def build_reflection_input(
        self,
        recent_memories: list[MemoryRecord],
        current_belief: float,
        agent_id: UUID | None = None,
        step: int = 0,
    ) -> ReflectionInput:
        """Prepare structured input for reflection.

        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1 RF-01
        """
        return ReflectionInput(
            agent_id=agent_id or uuid4(),
            recent_memories=recent_memories,
            current_belief=current_belief,
            step=step,
        )

    def apply_reflection_heuristic(
        self,
        reflection_input: ReflectionInput,
    ) -> ReflectionResult:
        """Tier 1/2 fallback: compute belief_delta from memory patterns.

        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1 RF-01

        Algorithm:
        - Count positive vs negative memories (emotion_weight > 0.5 → positive)
        - ratio = (positive - negative) / total
        - belief_delta = REFLECTION_WEIGHT * ratio
        - clamp belief_delta to [-0.3, 0.3]
        """
        memories = reflection_input.recent_memories
        if not memories:
            return ReflectionResult(
                belief_delta=0.0,
                insight="No recent memories to reflect on.",
                new_memories_generated=0,
            )

        positive = sum(1 for m in memories if m.emotion_weight > 0.5)
        negative = len(memories) - positive
        total = len(memories)

        ratio = (positive - negative) / total
        belief_delta = self._reflection_weight * ratio
        belief_delta = max(-0.3, min(0.3, belief_delta))

        if belief_delta > 0:
            insight = f"Reflecting on {total} memories: mostly positive experiences reinforce belief."
        elif belief_delta < 0:
            insight = f"Reflecting on {total} memories: mostly negative experiences weaken belief."
        else:
            insight = f"Reflecting on {total} memories: mixed signals, belief unchanged."

        return ReflectionResult(
            belief_delta=belief_delta,
            insight=insight,
            new_memories_generated=1 if abs(belief_delta) > 0.01 else 0,
        )


__all__ = ["ReflectionEngine", "ReflectionInput", "ReflectionResult"]
