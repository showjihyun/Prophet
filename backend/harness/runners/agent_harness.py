"""F18 Unit Test Hooks — Agent Harness.
SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks
"""
from app.engine.agent.cognition import CognitionLayer, CognitionResult
from app.engine.agent.emotion import EmotionLayer
from app.engine.agent.memory import MemoryRecord
from app.engine.agent.perception import (
    EnvironmentEvent,
    NeighborAction,
    PerceptionLayer,
    PerceptionResult,
)
from app.engine.agent.schema import AgentEmotion, AgentState
from app.engine.agent.tick import AgentTick, AgentTickResult, GraphContext


class AgentHarness:
    """Per-layer test entry points for Agent engine.

    SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks
    """

    def run_perception(
        self,
        agent: AgentState,
        events: list[EnvironmentEvent],
        neighbors: list[NeighborAction],
    ) -> PerceptionResult:
        """Direct PerceptionLayer call — no other layers involved.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks
        """
        layer = PerceptionLayer(feed_capacity=20)
        return layer.observe(agent, events, neighbors)

    def run_emotion_update(
        self,
        current_emotion: AgentEmotion,
        social_signal: float = 0.0,
        media_signal: float = 0.0,
        expert_signal: float = 0.0,
        decay: float = 0.05,
    ) -> AgentEmotion:
        """Direct EmotionLayer call.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks

        Accepts scalar float signals (social, media, expert) and maps to
        EmotionLayer.update(). The SPEC EmotionSignals container is represented
        as named parameters here for direct layer access.
        """
        layer = EmotionLayer()
        return layer.update(current_emotion, social_signal, media_signal, expert_signal, decay)

    def run_cognition(
        self,
        agent: AgentState,
        perception: PerceptionResult,
        memories: list[MemoryRecord],
        tier: int,
    ) -> CognitionResult:
        """Direct CognitionLayer call with mocked LLM if tier=3.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks

        When tier=3, the synchronous evaluate() falls back to Tier 2 (no real LLM call).
        """
        layer = CognitionLayer(llm_adapter=None)
        return layer.evaluate(agent, perception, memories, tier)  # type: ignore[arg-type]

    def run_full_tick(
        self,
        agent: AgentState,
        context: GraphContext | None = None,
        mock_llm: bool = True,
    ) -> AgentTickResult:
        """Full agent tick with optional mock LLM.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks
        """
        llm_adapter = None
        if mock_llm:
            from harness.mocks.mock_environment import MockLLMAdapter
            llm_adapter = MockLLMAdapter()

        tick = AgentTick(llm_adapter=llm_adapter)
        return tick.tick(
            agent=agent,
            environment_events=[],
            neighbor_actions=[],
            cognition_tier=1,
            seed=42,
            graph_context=context,
        )


__all__ = ["AgentHarness"]
