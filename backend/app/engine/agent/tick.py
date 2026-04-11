"""Agent Tick — full execution flow for one simulation step.
SPEC: docs/spec/01_AGENT_SPEC.md#agent-tick
"""
import random as stdlib_random
from dataclasses import dataclass, field, replace
from uuid import UUID

from app.engine.agent.schema import AgentAction, AgentEmotion, AgentState, DiffusionState
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
from app.engine.agent.reflection import ReflectionEngine
from app.engine.diffusion.opinion_dynamics import OpinionDynamicsModel


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
    SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#2.1
    """
    edges: dict[tuple[UUID, UUID], float]
    trust_matrix: dict[tuple[UUID, UUID], float]
    neighbor_ids: dict[UUID, list[UUID]]
    community_beliefs: dict[UUID, float]
    agent_beliefs: dict[UUID, float] = field(default_factory=dict)
    agent_emotions: dict[UUID, AgentEmotion] = field(default_factory=dict)

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

    def __init__(self, llm_adapter=None, gateway=None, session_factory=None, simulation_id=None):
        """SPEC: docs/spec/01_AGENT_SPEC.md#agent-tick
        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§3 MP-02
        """
        self._perception = PerceptionLayer(feed_capacity=20)
        self._memory = MemoryLayer(
            llm_adapter=llm_adapter,
            session_factory=session_factory,
            simulation_id=simulation_id,
        )
        self._emotion = EmotionLayer()
        self._cognition = CognitionLayer(llm_adapter=llm_adapter, gateway=gateway)
        self._decision = DecisionLayer()
        self._influence = InfluenceLayer()
        self._drift = PersonalityDrift()
        self._reflection = ReflectionEngine()
        self._opinion = OpinionDynamicsModel(epsilon=0.3, mu=0.5)
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
        campaign_novelty: float = 0.5,
        campaign_utility: float = 0.5,
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
        # Pass real edge weights so perception uses network topology (SQ-02)
        _edge_weights = None
        if graph_context is not None:
            _edge_weights = {
                nid: graph_context.edges.get((agent.agent_id, nid), 0.5)
                for nid in graph_context.neighbor_ids.get(agent.agent_id, [])
            }
        perception = self._perception.observe(agent, environment_events, neighbor_actions, edge_weights=_edge_weights)

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

        # Build neighbor emotion list for contagion (EC-01~04)
        neighbor_emotions_list = None
        if graph_context is not None and graph_context.agent_emotions:
            nids = graph_context.neighbor_ids.get(agent.agent_id, [])
            neighbor_emotions_list = [
                (graph_context.agent_emotions[nid],
                 graph_context.edges.get((agent.agent_id, nid), 0.5))
                for nid in nids
                if nid in graph_context.agent_emotions
            ] or None
        emotion = self._emotion.update(
            agent.emotion, social_signal, media_signal, expert_signal,
            neighbor_emotions=neighbor_emotions_list,
        )

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
            agent_with_emotion, perception, memories, actual_tier, community_bias,
            campaign_novelty=campaign_novelty,
            campaign_utility=campaign_utility,
        )

        # Step 6: Decision
        trust_matrix: dict[tuple[UUID, UUID], float] = {}
        if graph_context is not None:
            trust_matrix = graph_context.trust_matrix
        social_pressure = self._decision.compute_social_pressure(
            agent.agent_id, neighbor_actions, trust_matrix
        )
        action = self._decision.choose_action(
            cognition, social_pressure, agent.personality, agent_seed,
            agent_type=agent.agent_type,
        )

        # Step 7: Influence Propagation
        propagation_events: list[PropagationEvent] = []
        if action in {AgentAction.COMMENT, AgentAction.SHARE, AgentAction.REPOST, AgentAction.ADOPT}:
            # MessageStrength blends two signals:
            #   1. Campaign-inherent properties from CampaignConfig
            #      (novelty/utility/controversy — what the message IS)
            #   2. Agent-derived perception (media_signal, evaluation_score —
            #      how THIS agent reacts to the message)
            # The 0.6/0.4 blend makes campaign inputs dominant so a swing
            # from controversy=0.8 to controversy=0.2 actually moves the
            # propagation probability. Before Round 8-6, only
            # campaign_controversy was forwarded (novelty and utility were
            # agent-only), which made the entire campaign-framing slider
            # effectively dead — see docs/USE_CASE_PILOTS.md.
            # SPEC: docs/spec/26_DIFFUSION_CALIBRATION_SPEC.md (Round 8-6)
            agent_novelty = min(media_signal, 1.0)
            agent_utility = max(0.0, min(1.0, cognition.evaluation_score / 2.0))
            ms = MessageStrength(
                novelty=min(1.0, 0.6 * campaign_novelty + 0.4 * agent_novelty),
                controversy=campaign_controversy,
                utility=min(1.0, 0.6 * campaign_utility + 0.4 * agent_utility),
            )
            neighbor_ids: list[UUID] = []
            edges: dict[tuple[UUID, UUID], float] = {}
            if graph_context is not None:
                neighbor_ids = graph_context.neighbor_ids.get(agent.agent_id, [])
                edges = graph_context.edges
            propagation_events = self._influence.propagate(
                agent_with_emotion, action, neighbor_ids, edges, ms, agent_seed
            )

        # Step 8: Memory Storage
        # Sync tick() does not generate embeddings — use async_tick() for Tier 3 with embeddings.
        step_summary = f"Step {agent.step}: took action {action.value}"
        emotion_mean = (emotion.interest + emotion.trust + emotion.excitement) / 3.0

        memory_stored = self._memory.store(
            agent.agent_id, "episodic", step_summary,
            emotion_weight=emotion_mean, step=agent.step,
        )

        # Step 9: Personality Drift — evolve personality based on action taken
        new_personality, new_cumulative_drift = self._drift.apply_drift(
            agent.personality, action, agent.cumulative_drift,
            emotion=emotion,
        )

        # Step 9.5: Reflection — periodic belief revision from accumulated memories
        # SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1 RF-01~05
        reflection_belief_delta = 0.0
        last_reflection_step = agent.last_reflection_step
        memories_since = len(self._memory._store.get(agent.agent_id, [])) - (
            agent.step - agent.last_reflection_step
        ) if agent.last_reflection_step >= 0 else len(self._memory._store.get(agent.agent_id, []))
        if self._reflection.should_reflect(max(0, memories_since), agent.step, agent.last_reflection_step):
            refl_memories = self._memory.retrieve(agent.agent_id, "", top_k=10, current_step=agent.step)
            refl_input = self._reflection.build_reflection_input(
                recent_memories=refl_memories, current_belief=agent.belief, agent_id=agent.agent_id, step=agent.step,
            )
            refl_result = self._reflection.apply_reflection_heuristic(refl_input)
            reflection_belief_delta = refl_result.belief_delta
            last_reflection_step = agent.step
            if refl_result.new_memories_generated > 0:
                self._memory.store(
                    agent.agent_id, "semantic", refl_result.insight,
                    emotion_weight=abs(refl_result.belief_delta), step=agent.step,
                )

        # Step 10: State Update — Belief Update (Deffuant bounded confidence)
        # SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#2.1
        # External stimulus from cognition (halved to leave room for social dynamics)
        stimulus_belief = max(-1.0, min(1.0, agent.belief + cognition.evaluation_score * 0.05 + reflection_belief_delta))
        # Deffuant pairwise dynamics with neighbors
        if graph_context is not None and graph_context.agent_beliefs:
            nids = graph_context.neighbor_ids.get(agent.agent_id, [])
            neighbor_beliefs = [
                (graph_context.agent_beliefs.get(nid, 0.0),
                 graph_context.edges.get((agent.agent_id, nid), 0.5))
                for nid in nids
                if nid in graph_context.agent_beliefs
            ]
            new_belief = self._opinion.batch_update(
                stimulus_belief, neighbor_beliefs,
                stubbornness=agent.personality.skepticism,
            )
        else:
            new_belief = stimulus_belief

        # DiffusionState transitions (SEIAR)
        # SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#3.1
        ds = agent.diffusion_state
        if ds == DiffusionState.SUSCEPTIBLE and agent.exposure_count > 0:
            ds = DiffusionState.EXPOSED
        if ds == DiffusionState.EXPOSED:
            if agent.personality.skepticism > 0.8 and action == AgentAction.IGNORE:
                ds = DiffusionState.RESISTANT
            elif emotion.interest > 0.5:
                ds = DiffusionState.INTERESTED
        if ds == DiffusionState.INTERESTED and action == AgentAction.ADOPT:
            ds = DiffusionState.ADOPTED
        if ds == DiffusionState.ADOPTED and new_belief < -0.3:
            ds = DiffusionState.RECOVERED
        is_adopted = ds == DiffusionState.ADOPTED or agent.adopted or (action == AgentAction.ADOPT)

        updated_state = replace(
            agent,
            personality=new_personality,
            emotion=emotion,
            action=action,
            belief=new_belief,
            adopted=is_adopted,
            diffusion_state=ds,
            llm_tier_used=cognition.tier_used,
            cumulative_drift=new_cumulative_drift,
            last_reflection_step=last_reflection_step,
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
        campaign_novelty: float = 0.5,
        campaign_utility: float = 0.5,
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
        # Pass real edge weights so perception uses network topology (SQ-02)
        _edge_weights = None
        if graph_context is not None:
            _edge_weights = {
                nid: graph_context.edges.get((agent.agent_id, nid), 0.5)
                for nid in graph_context.neighbor_ids.get(agent.agent_id, [])
            }
        perception = self._perception.observe(agent, environment_events, neighbor_actions, edge_weights=_edge_weights)

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

        # Build neighbor emotion list for contagion (EC-01~04)
        neighbor_emotions_list = None
        if graph_context is not None and graph_context.agent_emotions:
            nids = graph_context.neighbor_ids.get(agent.agent_id, [])
            neighbor_emotions_list = [
                (graph_context.agent_emotions[nid],
                 graph_context.edges.get((agent.agent_id, nid), 0.5))
                for nid in nids
                if nid in graph_context.agent_emotions
            ] or None
        emotion = self._emotion.update(
            agent.emotion, social_signal, media_signal, expert_signal,
            neighbor_emotions=neighbor_emotions_list,
        )

        # Step 5: Cognition — async path uses real LLM for Tier 3
        community_bias = 0.0
        if graph_context is not None:
            community_bias = graph_context.get_community_mean_belief(agent.community_id)

        agent_with_emotion = replace(agent, emotion=emotion)
        cognition = await self._cognition.evaluate_async(
            agent_with_emotion, perception, memories, cognition_tier, community_bias,
            campaign=campaign,
            campaign_novelty=campaign_novelty,
            campaign_utility=campaign_utility,
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
            cognition, social_pressure, agent.personality, agent_seed,
            agent_type=agent.agent_type,
        )

        # Step 7: Influence Propagation
        propagation_events: list[PropagationEvent] = []
        if action in {AgentAction.COMMENT, AgentAction.SHARE, AgentAction.REPOST, AgentAction.ADOPT}:
            # MessageStrength blends two signals:
            #   1. Campaign-inherent properties from CampaignConfig
            #      (novelty/utility/controversy — what the message IS)
            #   2. Agent-derived perception (media_signal, evaluation_score —
            #      how THIS agent reacts to the message)
            # The 0.6/0.4 blend makes campaign inputs dominant so a swing
            # from controversy=0.8 to controversy=0.2 actually moves the
            # propagation probability. Before Round 8-6, only
            # campaign_controversy was forwarded (novelty and utility were
            # agent-only), which made the entire campaign-framing slider
            # effectively dead — see docs/USE_CASE_PILOTS.md.
            # SPEC: docs/spec/26_DIFFUSION_CALIBRATION_SPEC.md (Round 8-6)
            agent_novelty = min(media_signal, 1.0)
            agent_utility = max(0.0, min(1.0, cognition.evaluation_score / 2.0))
            ms = MessageStrength(
                novelty=min(1.0, 0.6 * campaign_novelty + 0.4 * agent_novelty),
                controversy=campaign_controversy,
                utility=min(1.0, 0.6 * campaign_utility + 0.4 * agent_utility),
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

        memory_stored = await self._memory.store_async(
            agent.agent_id, "episodic", step_summary,
            emotion_weight=emotion_mean, step=agent.step,
            embedding=embedding,
        )

        # Step 9: Personality Drift — evolve personality based on action taken
        new_personality, new_cumulative_drift = self._drift.apply_drift(
            agent.personality, action, agent.cumulative_drift,
            emotion=emotion,
        )

        # Step 9.5: Reflection — periodic belief revision from accumulated memories
        # SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§1 RF-01~05
        reflection_belief_delta = 0.0
        last_reflection_step = agent.last_reflection_step
        memories_since = len(self._memory._store.get(agent.agent_id, [])) - (
            agent.step - agent.last_reflection_step
        ) if agent.last_reflection_step >= 0 else len(self._memory._store.get(agent.agent_id, []))
        if self._reflection.should_reflect(max(0, memories_since), agent.step, agent.last_reflection_step):
            refl_memories = self._memory.retrieve(agent.agent_id, "", top_k=10, current_step=agent.step)
            refl_input = self._reflection.build_reflection_input(
                recent_memories=refl_memories, current_belief=agent.belief, agent_id=agent.agent_id, step=agent.step,
            )
            refl_result = self._reflection.apply_reflection_heuristic(refl_input)
            reflection_belief_delta = refl_result.belief_delta
            last_reflection_step = agent.step
            if refl_result.new_memories_generated > 0:
                await self._memory.store_async(
                    agent.agent_id, "semantic", refl_result.insight,
                    emotion_weight=abs(refl_result.belief_delta), step=agent.step,
                )

        # Step 10: State Update — Belief Update (Deffuant bounded confidence)
        # SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#2.1
        # External stimulus from cognition (halved to leave room for social dynamics)
        stimulus_belief = max(-1.0, min(1.0, agent.belief + cognition.evaluation_score * 0.05 + reflection_belief_delta))
        # Deffuant pairwise dynamics with neighbors
        if graph_context is not None and graph_context.agent_beliefs:
            nids = graph_context.neighbor_ids.get(agent.agent_id, [])
            neighbor_beliefs = [
                (graph_context.agent_beliefs.get(nid, 0.0),
                 graph_context.edges.get((agent.agent_id, nid), 0.5))
                for nid in nids
                if nid in graph_context.agent_beliefs
            ]
            new_belief = self._opinion.batch_update(
                stimulus_belief, neighbor_beliefs,
                stubbornness=agent.personality.skepticism,
            )
        else:
            new_belief = stimulus_belief

        # DiffusionState transitions (SEIAR)
        # SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#3.1
        ds = agent.diffusion_state
        if ds == DiffusionState.SUSCEPTIBLE and agent.exposure_count > 0:
            ds = DiffusionState.EXPOSED
        if ds == DiffusionState.EXPOSED:
            if agent.personality.skepticism > 0.8 and action == AgentAction.IGNORE:
                ds = DiffusionState.RESISTANT
            elif emotion.interest > 0.5:
                ds = DiffusionState.INTERESTED
        if ds == DiffusionState.INTERESTED and action == AgentAction.ADOPT:
            ds = DiffusionState.ADOPTED
        if ds == DiffusionState.ADOPTED and new_belief < -0.3:
            ds = DiffusionState.RECOVERED
        is_adopted = ds == DiffusionState.ADOPTED or agent.adopted or (action == AgentAction.ADOPT)

        updated_state = replace(
            agent,
            personality=new_personality,
            emotion=emotion,
            action=action,
            belief=new_belief,
            adopted=is_adopted,
            diffusion_state=ds,
            llm_tier_used=cognition.tier_used,
            cumulative_drift=new_cumulative_drift,
            last_reflection_step=last_reflection_step,
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
