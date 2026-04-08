"""Agent Tick — full execution flow for one simulation step.
SPEC: docs/spec/01_AGENT_SPEC.md#agent-tick
"""
import random as stdlib_random
from dataclasses import dataclass, replace
from uuid import UUID

from app.engine.agent.schema import AgentAction, AgentState
from app.engine.agent.perception import (
    PerceptionLayer, PerceptionResult, EnvironmentEvent, NeighborAction,
)
from app.engine.agent.memory import MemoryLayer, MemoryRecord
from app.engine.agent.emotion import EmotionLayer
from app.engine.agent.cognition import CognitionLayer
from app.engine.agent.decision import DecisionLayer
from app.engine.agent.influence import (
    InfluenceLayer, MessageStrength, PropagationEvent, build_contextual_packet,
)
from app.engine.agent.drift import PersonalityDrift


@dataclass
class AgentTickResult:
    """Output of AgentTick.tick().

    SPEC: docs/spec/01_AGENT_SPEC.md#agent-tick
    """
    updated_state: AgentState
    propagation_events: list[PropagationEvent]
    memory_stored: MemoryRecord | None
    llm_call_log: object | None  # LLMCallLog placeholder
    action: AgentAction
    llm_tier_used: int | None


@dataclass
class GraphContext:
    """Network topology context provided to AgentEngine.tick().

    SPEC: docs/spec/01_AGENT_SPEC.md#agent-tick
    """
    edges: dict[tuple[UUID, UUID], float]
    trust_matrix: dict[tuple[UUID, UUID], float]
    neighbor_ids: dict[UUID, list[UUID]]
    community_beliefs: dict[UUID, float]

    def get_community_mean_belief(self, community_id: UUID) -> float:
        """Returns mean belief for community. Default 0.0 if unknown.

        SPEC: docs/spec/01_AGENT_SPEC.md#agent-tick
        """
        return self.community_beliefs.get(community_id, 0.0)


def _step_to_hour(step: int) -> int:
    """Convert step number to hour of day (0-23).

    SPEC: docs/spec/01_AGENT_SPEC.md#agent-tick
    """
    return step % 24


class AgentTick:
    """Full agent execution for one simulation step.

    SPEC: docs/spec/01_AGENT_SPEC.md#agent-tick

    Orchestrates all 6 layers in order:
        perception -> memory -> emotion -> cognition -> decision -> influence -> store memory
    """

    def __init__(self, llm_adapter=None, gateway=None):
        """SPEC: docs/spec/01_AGENT_SPEC.md#agent-tick"""
        self._perception = PerceptionLayer(feed_capacity=20)
        self._memory = MemoryLayer(llm_adapter=llm_adapter)
        self._emotion = EmotionLayer()
        self._cognition = CognitionLayer(llm_adapter=llm_adapter, gateway=gateway)
        self._decision = DecisionLayer()
        self._influence = InfluenceLayer()
        self._drift = PersonalityDrift()
        self._llm_adapter = llm_adapter
        self._gateway = gateway

    def tick(
        self,
        agent: AgentState,
        environment_events: list[EnvironmentEvent],
        neighbor_actions: list[NeighborAction],
        cognition_tier: int = 1,
        seed: int = 0,
        graph_context: GraphContext | None = None,
        campaign_controversy: float = 0.0,
    ) -> AgentTickResult:
        """Full agent execution for one simulation step.

        SPEC: docs/spec/01_AGENT_SPEC.md#agent-tick

        Execution Order (strict sequential):
            1. Activity check
            2. Perception
            3. Memory retrieval
            4. Emotion update
            5. Cognition
            6. Decision
            7. Influence propagation
            8. Memory storage
            9. State update
        """
        agent_seed = seed + hash(agent.agent_id) + agent.step

        # Step 1: Activity Check
        hour = _step_to_hour(agent.step)
        rng = stdlib_random.Random(agent_seed)
        if rng.random() > agent.activity_vector[hour]:
            # Inactive: return IGNORE with no changes
            return AgentTickResult(
                updated_state=agent,
                propagation_events=[],
                memory_stored=None,
                llm_call_log=None,
                action=AgentAction.IGNORE,
                llm_tier_used=agent.llm_tier_used,
            )

        # Step 2: Perception
        perception = self._perception.observe(agent, environment_events, neighbor_actions)

        # Step 3: Memory Retrieval
        context = ""
        if perception.feed_items:
            context = perception.feed_items[0].message[:200]
        memories = self._memory.retrieve(agent.agent_id, context, top_k=10, current_step=agent.step)

        # Step 4: Emotion Update
        social_signal = 0.0
        if perception.social_signals:
            social_signal = sum(s.weighted_score for s in perception.social_signals) / len(perception.social_signals)
        media_signal = min(perception.total_exposure_score / 10.0, 1.0)
        expert_signal = 0.0
        if perception.expert_signals:
            expert_signal = sum(
                e.opinion_score * e.credibility for e in perception.expert_signals
            ) / len(perception.expert_signals)

        emotion = self._emotion.update(agent.emotion, social_signal, media_signal, expert_signal)

        # Step 5: Cognition
        community_bias = 0.0
        if graph_context is not None:
            community_bias = graph_context.get_community_mean_belief(agent.community_id)

        # Tier 3 LLM integration requires async context.
        # In synchronous tick(), Tier 3 falls back to Tier 2 with personality adjustment.
        # Full async LLM path will be enabled when tick() is made async.
        actual_tier = cognition_tier
        llm_call_log = None

        if cognition_tier == 3:
            actual_tier = 2  # Tier 3 → Tier 2 fallback (sync context)

        # Update agent emotion for cognition
        agent_with_emotion = replace(agent, emotion=emotion)
        cognition = self._cognition.evaluate(
            agent_with_emotion, perception, memories, actual_tier, community_bias
        )

        # Step 6: Decision
        trust_matrix: dict[tuple[UUID, UUID], float] = {}
        if graph_context is not None:
            trust_matrix = graph_context.trust_matrix
        social_pressure = self._decision.compute_social_pressure(
            agent.agent_id, neighbor_actions, trust_matrix
        )
        action = self._decision.choose_action(
            cognition, social_pressure, agent.personality, agent_seed
        )

        # Step 7: Influence Propagation
        propagation_events: list[PropagationEvent] = []
        if action in {AgentAction.COMMENT, AgentAction.SHARE, AgentAction.REPOST, AgentAction.ADOPT}:
            ms = MessageStrength(
                novelty=min(media_signal, 1.0),
                controversy=campaign_controversy,
                utility=max(0.0, min(1.0, cognition.evaluation_score / 2.0)),
            )
            neighbor_ids: list[UUID] = []
            edges: dict[tuple[UUID, UUID], float] = {}
            if graph_context is not None:
                neighbor_ids = graph_context.neighbor_ids.get(agent.agent_id, [])
                edges = graph_context.edges
            propagation_events = self._influence.propagate(
                agent_with_emotion, action, neighbor_ids, edges, ms, agent_seed
            )

        # Step 8: Memory Storage (with best-effort embedding)
        step_summary = f"Step {agent.step}: took action {action.value}"
        emotion_mean = (emotion.interest + emotion.trust + emotion.excitement) / 3.0

        # Try to compute embedding synchronously via run_until_complete
        embedding: list[float] | None = None
        if self._llm_adapter is not None and cognition_tier >= 2:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Can't await in sync context — schedule and skip
                    pass
                else:
                    embedding = loop.run_until_complete(self._memory.embed_text(step_summary))
            except Exception:
                pass  # best-effort: embedding is optional

        memory_stored = self._memory.store(
            agent.agent_id, "episodic", step_summary,
            emotion_weight=emotion_mean, step=agent.step, embedding=embedding,
        )

        # Step 9: Personality Drift — evolve personality based on action taken
        new_personality, new_cumulative_drift = self._drift.apply_drift(
            agent.personality, action, agent.cumulative_drift,
        )

        # Step 10: State Update — Belief Update Formula
        new_belief = max(-1.0, min(1.0, agent.belief + cognition.evaluation_score * 0.1))

        updated_state = replace(
            agent,
            personality=new_personality,
            emotion=emotion,
            action=action,
            belief=new_belief,
            adopted=agent.adopted or (action == AgentAction.ADOPT),
            llm_tier_used=cognition.tier_used,
            cumulative_drift=new_cumulative_drift,
        )

        return AgentTickResult(
            updated_state=updated_state,
            propagation_events=propagation_events,
            memory_stored=memory_stored,
            llm_call_log=llm_call_log,
            action=action,
            llm_tier_used=cognition.tier_used,
        )

    async def async_tick(
        self,
        agent: AgentState,
        environment_events: list[EnvironmentEvent],
        neighbor_actions: list[NeighborAction],
        cognition_tier: int = 3,
        seed: int = 0,
        graph_context: GraphContext | None = None,
        campaign: object | None = None,
        campaign_controversy: float = 0.0,
    ) -> AgentTickResult:
        """Async agent execution for Tier 3 agents using embedding-based memory and real LLM.

        SPEC: docs/spec/01_AGENT_SPEC.md#agent-tick

        This is the high-fidelity path for Tier 3 (Elite LLM) agents:
            - Uses retrieve_async() for embedding-based similarity retrieval (GraphRAG)
            - Uses embed_text() to attach embeddings to stored memories
            - Uses evaluate_async() for real LLM cognition (Tier 3)
            - Falls back gracefully if embedding or LLM fails

        The sync tick() remains the fast path for Tier 1/2 agents (~80%+ of the fleet).
        """
        agent_seed = seed + hash(agent.agent_id) + agent.step

        # Step 1: Activity Check
        hour = _step_to_hour(agent.step)
        rng = stdlib_random.Random(agent_seed)
        if rng.random() > agent.activity_vector[hour]:
            return AgentTickResult(
                updated_state=agent,
                propagation_events=[],
                memory_stored=None,
                llm_call_log=None,
                action=AgentAction.IGNORE,
                llm_tier_used=agent.llm_tier_used,
            )

        # Step 2: Perception
        perception = self._perception.observe(agent, environment_events, neighbor_actions)

        # Step 3: Memory Retrieval — use async path with embedding similarity
        query_text: str | None = None
        if perception.feed_items:
            query_text = perception.feed_items[0].message[:200]
        context = query_text or ""
        memories = await self._memory.retrieve_async(
            agent.agent_id,
            context,
            top_k=10,
            current_step=agent.step,
            query_text=query_text,
        )

        # Step 4: Emotion Update
        social_signal = 0.0
        if perception.social_signals:
            social_signal = sum(s.weighted_score for s in perception.social_signals) / len(perception.social_signals)
        media_signal = min(perception.total_exposure_score / 10.0, 1.0)
        expert_signal = 0.0
        if perception.expert_signals:
            expert_signal = sum(
                e.opinion_score * e.credibility for e in perception.expert_signals
            ) / len(perception.expert_signals)

        emotion = self._emotion.update(agent.emotion, social_signal, media_signal, expert_signal)

        # Step 5: Cognition — async path uses real LLM for Tier 3
        community_bias = 0.0
        if graph_context is not None:
            community_bias = graph_context.get_community_mean_belief(agent.community_id)

        agent_with_emotion = replace(agent, emotion=emotion)
        cognition = await self._cognition.evaluate_async(
            agent_with_emotion, perception, memories, cognition_tier, community_bias,
            campaign=campaign,
        )
        llm_call_log = None  # placeholder; real logging wired at gateway level

        # Step 6: Decision
        trust_matrix: dict[tuple[UUID, UUID], float] = {}
        if graph_context is not None:
            trust_matrix = graph_context.trust_matrix
        social_pressure = self._decision.compute_social_pressure(
            agent.agent_id, neighbor_actions, trust_matrix
        )
        action = self._decision.choose_action(
            cognition, social_pressure, agent.personality, agent_seed
        )

        # Step 7: Influence Propagation
        propagation_events: list[PropagationEvent] = []
        if action in {AgentAction.COMMENT, AgentAction.SHARE, AgentAction.REPOST, AgentAction.ADOPT}:
            ms = MessageStrength(
                novelty=min(media_signal, 1.0),
                controversy=campaign_controversy,
                utility=max(0.0, min(1.0, cognition.evaluation_score / 2.0)),
            )
            neighbor_ids: list[UUID] = []
            edges: dict[tuple[UUID, UUID], float] = {}
            if graph_context is not None:
                neighbor_ids = graph_context.neighbor_ids.get(agent.agent_id, [])
                edges = graph_context.edges
            propagation_events = self._influence.propagate(
                agent_with_emotion, action, neighbor_ids, edges, ms, agent_seed
            )

        # Step 8: Memory Storage — generate embedding for richer future retrieval
        step_summary = f"Step {agent.step}: took action {action.value}"
        emotion_mean = (emotion.interest + emotion.trust + emotion.excitement) / 3.0
        embedding: list[float] | None = None
        try:
            embedding = await self._memory.embed_text(step_summary)
        except Exception:
            embedding = None  # graceful fallback: store without embedding

        memory_stored = self._memory.store(
            agent.agent_id, "episodic", step_summary,
            emotion_weight=emotion_mean, step=agent.step,
            embedding=embedding,
        )

        # Step 9: Personality Drift — evolve personality based on action taken
        new_personality, new_cumulative_drift = self._drift.apply_drift(
            agent.personality, action, agent.cumulative_drift,
        )

        # Step 10: State Update — Belief Update Formula
        new_belief = max(-1.0, min(1.0, agent.belief + cognition.evaluation_score * 0.1))

        updated_state = replace(
            agent,
            personality=new_personality,
            emotion=emotion,
            action=action,
            belief=new_belief,
            adopted=agent.adopted or (action == AgentAction.ADOPT),
            llm_tier_used=cognition.tier_used,
            cumulative_drift=new_cumulative_drift,
        )

        return AgentTickResult(
            updated_state=updated_state,
            propagation_events=propagation_events,
            memory_stored=memory_stored,
            llm_call_log=llm_call_log,
            action=action,
            llm_tier_used=cognition.tier_used,
        )


__all__ = ["AgentTick", "AgentTickResult", "GraphContext"]
