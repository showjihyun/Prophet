"""Simulation Orchestrator — top-level coordinator.
SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
"""
import asyncio
import logging
import random as stdlib_random
from collections import Counter
from dataclasses import dataclass, field, replace
from uuid import UUID, uuid4

import networkx as nx

from app.engine.agent.schema import (
    AgentAction,
    AgentEmotion,
    AgentPersonality,
    AgentState,
    AgentType,
)
from app.engine.agent.perception import EnvironmentEvent
from app.engine.agent.tier_selector import TierConfig, TierSelector
from app.engine.diffusion.schema import CampaignEvent, EmergentEvent
from app.engine.network.generator import NetworkGenerator
from app.engine.network.schema import NetworkConfig, SocialNetwork

from app.engine.simulation.exceptions import (
    InvalidStateError,
    InvalidStateTransitionError,
    SimulationCapacityError,
    StepNotFoundError,
)
from app.engine.simulation.schema import (
    AgentModification,
    CampaignConfig,
    SimulationConfig,
    SimulationRun,
    SimulationStatus,
    StepResult,
)
from app.engine.simulation.step_runner import StepRunner

logger = logging.getLogger(__name__)

# Valid state transitions: from_status -> set of allowed to_statuses
_VALID_TRANSITIONS: dict[str, set[str]] = {
    SimulationStatus.CREATED.value: {SimulationStatus.CONFIGURED.value},
    SimulationStatus.CONFIGURED.value: {SimulationStatus.RUNNING.value},
    SimulationStatus.RUNNING.value: {
        SimulationStatus.PAUSED.value,
        SimulationStatus.COMPLETED.value,
        SimulationStatus.FAILED.value,
    },
    SimulationStatus.PAUSED.value: {
        SimulationStatus.RUNNING.value,
        SimulationStatus.FAILED.value,
    },
    SimulationStatus.COMPLETED.value: set(),
    SimulationStatus.FAILED.value: set(),
}

_MAX_CONCURRENT = 3

# Allowed event types for inject_event
_ALLOWED_EVENT_TYPES = {
    "campaign_ad", "influencer_post", "expert_review",
    "community_discussion", "negative_pr", "competitor_attack",
}


@dataclass
class SimulationState:
    """In-memory runtime state for a simulation.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
    """
    simulation_id: UUID
    config: SimulationConfig
    status: str = SimulationStatus.CONFIGURED.value
    current_step: int = 0
    network: SocialNetwork | None = None
    agents: list[AgentState] = field(default_factory=list)
    step_history: list[StepResult] = field(default_factory=list)
    injected_events: list[EnvironmentEvent] = field(default_factory=list)
    ws_connected: bool = True


class SimulationOrchestrator:
    """Top-level coordinator that manages simulation lifecycle.

    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface

    Manages creation, execution, pausing, modification, and event injection
    for simulations. Uses in-memory state for Phase 6.
    """

    MAX_SIMULATIONS = 50
    SIMULATION_TTL_SECONDS = 86400  # 24 hours

    def __init__(self, llm_adapter=None, slm_adapter=None) -> None:
        """Initialize the orchestrator.
        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
        """
        self._simulations: dict[UUID, SimulationState] = {}
        self._locks: dict[UUID, asyncio.Lock] = {}
        self._step_runner = StepRunner(llm_adapter=llm_adapter)
        self._llm_adapter = llm_adapter
        self._slm_adapter = slm_adapter

    def _get_lock(self, simulation_id: UUID) -> asyncio.Lock:
        """Get or create a per-simulation asyncio lock."""
        if simulation_id not in self._locks:
            self._locks[simulation_id] = asyncio.Lock()
        return self._locks[simulation_id]

    # ------------------------------------------------------------------ #
    # Eviction
    # ------------------------------------------------------------------ #

    def _cleanup_expired(self) -> None:
        """Remove simulations older than TTL or if over max count.
        SPEC: docs/spec/09_HARNESS_SPEC.md#memory-eviction-policy
        """
        from datetime import datetime as _dt, timezone as _tz

        now = _dt.now(_tz.utc)
        expired: list[UUID] = []
        for sim_id, state in self._simulations.items():
            created_at = getattr(state, 'created_at', None)
            if created_at is not None:
                age = (now - created_at).total_seconds()
                if age > self.SIMULATION_TTL_SECONDS:
                    expired.append(sim_id)
        for sim_id in expired:
            del self._simulations[sim_id]
            self._locks.pop(sim_id, None)

        # Also enforce max count (remove oldest first)
        if len(self._simulations) > self.MAX_SIMULATIONS:
            sorted_sims = sorted(
                self._simulations.keys(),
                key=lambda k: getattr(self._simulations[k], 'created_at', _dt.min),
            )
            while len(self._simulations) > self.MAX_SIMULATIONS:
                oldest = sorted_sims.pop(0)
                del self._simulations[oldest]
                self._locks.pop(oldest, None)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def create_simulation(self, config: SimulationConfig) -> SimulationState:
        """Create and configure a simulation from config.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface

        1. Validate config
        2. Generate agent population
        3. Generate SocialNetwork
        4. Assign influence scores from network degree centrality
        5. Status -> CONFIGURED

        Raises:
            ValueError: empty community list
        """
        self._cleanup_expired()

        if not config.communities:
            raise ValueError("communities list must not be empty")

        sim_id = config.simulation_id
        seed = config.random_seed

        # Generate network
        net_config = config.network_config
        # Sync communities into network config
        net_config.communities = config.communities
        net_gen = NetworkGenerator()
        network = net_gen.generate(net_config, seed=seed)

        # Generate agents from network nodes
        rng = stdlib_random.Random(seed)
        agents: list[AgentState] = []
        nodes = list(network.graph.nodes(data=True))

        # Compute degree centrality for influence scores
        centrality = nx.degree_centrality(network.graph)

        for node_id, node_data in nodes:
            community_id_str = node_data.get("community_id", "default")
            # Map community string id to a deterministic UUID
            community_uuid = uuid4() if seed is None else UUID(
                int=hash(community_id_str) % (2**128)
            )
            # Store the UUID on the node for later lookup
            network.graph.nodes[node_id]["community_uuid"] = community_uuid

            agent_id = uuid4() if seed is None else UUID(
                int=(hash(node_id) + (seed or 0) * 9999) % (2**128)
            )
            network.graph.nodes[node_id]["agent_id"] = agent_id

            # Determine agent type from community config
            agent_type_str = node_data.get("agent_type", "consumer")
            try:
                agent_type = AgentType(agent_type_str)
            except ValueError:
                agent_type = AgentType.CONSUMER

            # Personality from community profile (with +-0.15 jitter) or random
            community_cfg = next(
                (cc for cc in config.communities if cc.id == community_id_str),
                None,
            )
            pp = community_cfg.personality_profile if community_cfg else {}
            def _trait(key: str) -> float:
                if key in pp:
                    return max(0.0, min(1.0, pp[key] + rng.uniform(-0.15, 0.15)))
                return rng.uniform(0.2, 0.8)
            personality = AgentPersonality(
                openness=_trait("openness"),
                skepticism=_trait("skepticism"),
                trend_following=_trait("trend_following"),
                brand_loyalty=_trait("brand_loyalty"),
                social_influence=_trait("social_influence"),
            )

            emotion = AgentEmotion(
                interest=rng.uniform(0.3, 0.7),
                trust=rng.uniform(0.3, 0.7),
                skepticism=rng.uniform(0.2, 0.6),
                excitement=rng.uniform(0.2, 0.6),
            )

            influence_score = centrality.get(node_id, 0.0)

            agent = AgentState(
                agent_id=agent_id,
                simulation_id=sim_id,
                agent_type=agent_type,
                step=0,
                personality=personality,
                emotion=emotion,
                belief=rng.uniform(-0.3, 0.3),
                action=AgentAction.IGNORE,
                exposure_count=0,
                adopted=False,
                community_id=community_uuid,
                influence_score=influence_score,
                llm_tier_used=None,
            )
            agents.append(agent)

        state = SimulationState(
            simulation_id=sim_id,
            config=config,
            status=SimulationStatus.CONFIGURED.value,
            current_step=0,
            network=network,
            agents=agents,
        )
        self._simulations[sim_id] = state
        # Pre-create lock for this simulation
        self._locks[sim_id] = asyncio.Lock()
        return state

    def start(self, simulation_id: UUID) -> None:
        """Transition to RUNNING state.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface

        Raises:
            InvalidStateTransitionError: invalid transition
            SimulationCapacityError: max concurrent exceeded
        """
        state = self._get_state(simulation_id)
        self._validate_transition(state.status, SimulationStatus.RUNNING.value)

        # Check concurrent limit
        running_count = sum(
            1 for s in self._simulations.values()
            if s.status == SimulationStatus.RUNNING.value
        )
        if running_count >= _MAX_CONCURRENT:
            raise SimulationCapacityError(
                f"Max {_MAX_CONCURRENT} concurrent simulations exceeded"
            )

        state.status = SimulationStatus.RUNNING.value

    async def run_step(self, simulation_id: UUID) -> StepResult:
        """Execute one simulation step.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface

        Raises:
            SimulationStepError on internal crash (status -> FAILED)
        """
        async with self._get_lock(simulation_id):
            state = self._get_state(simulation_id)
            try:
                result = await self._step_runner.execute_step(state, state.current_step)
                state.step_history.append(result)
                state.current_step += 1

                # Check completion
                if state.current_step >= state.config.max_steps:
                    state.status = SimulationStatus.COMPLETED.value

                return result
            except Exception:
                state.status = SimulationStatus.FAILED.value
                raise

    async def pause(self, simulation_id: UUID) -> None:
        """Pause a running simulation.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
        """
        async with self._get_lock(simulation_id):
            state = self._get_state(simulation_id)
            self._validate_transition(state.status, SimulationStatus.PAUSED.value)
            state.status = SimulationStatus.PAUSED.value

    async def resume(self, simulation_id: UUID) -> None:
        """Resume a paused simulation.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
        """
        async with self._get_lock(simulation_id):
            state = self._get_state(simulation_id)
            self._validate_transition(state.status, SimulationStatus.RUNNING.value)
            state.status = SimulationStatus.RUNNING.value

    async def modify_agent(
        self,
        simulation_id: UUID,
        agent_id: UUID,
        belief: float | None = None,
        modifications: AgentModification | None = None,
    ) -> AgentState:
        """Modify an agent while simulation is PAUSED.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface

        Raises:
            InvalidStateError: if not PAUSED
            ValueError: agent not found
        """
        async with self._get_lock(simulation_id):
            state = self._get_state(simulation_id)
            if state.status != SimulationStatus.PAUSED.value:
                raise InvalidStateError(
                    f"modify_agent only allowed when PAUSED, current status: {state.status}"
                )

            # Find agent
            agent_idx = None
            for i, agent in enumerate(state.agents):
                if agent.agent_id == agent_id:
                    agent_idx = i
                    break

            if agent_idx is None:
                raise ValueError(f"Agent {agent_id} not found in simulation {simulation_id}")

            agent = state.agents[agent_idx]

            # Apply modifications
            updates: dict = {}
            if belief is not None:
                updates["belief"] = max(-1.0, min(1.0, belief))
            if modifications is not None:
                if modifications.personality is not None:
                    updates["personality"] = modifications.personality
                if modifications.emotion is not None:
                    updates["emotion"] = modifications.emotion
                if modifications.community_id is not None:
                    updates["community_id"] = modifications.community_id
                if modifications.belief is not None:
                    updates["belief"] = max(-1.0, min(1.0, modifications.belief))

            if updates:
                state.agents[agent_idx] = replace(agent, **updates)

            return state.agents[agent_idx]

    def inject_event(
        self,
        simulation_id: UUID,
        event: EnvironmentEvent | None = None,
        event_type: str | None = None,
        payload: dict | None = None,
    ) -> None:
        """Inject an external event mid-simulation.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface

        Raises:
            ValueError: unknown event_type
        """
        state = self._get_state(simulation_id)

        if event is not None:
            state.injected_events.append(event)
            return

        # String-based injection (for error test compatibility)
        if event_type is not None:
            NEGATIVE_EVENT_TYPES = {"negative_pr", "competitor_attack", "bad_review"}
            if event_type in NEGATIVE_EVENT_TYPES:
                mapped_type = "community_discussion"  # negative events are discussions
            elif event_type in {"campaign_ad", "influencer_post", "expert_review", "community_discussion"}:
                mapped_type = event_type
            else:
                raise ValueError(f"Unknown event type: {event_type}")
            env_event = EnvironmentEvent(
                event_type=mapped_type,
                content_id=uuid4(),
                message=str(payload) if payload else "",
                source_agent_id=None,
                channel="direct",
                timestamp=state.current_step,
            )
            state.injected_events.append(env_event)
            return

        raise ValueError("Either event or event_type must be provided")

    def replay_step(
        self,
        simulation_id: UUID,
        target_step: int,
    ) -> StepResult:
        """Replay from a specific step.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface

        Finds the step in history, then resets current_step to target_step so
        the simulation can be re-run from that point forward.

        Raises:
            ValueError: target_step > current_step
            StepNotFoundError: step not in history
        """
        state = self._get_state(simulation_id)

        if target_step > state.current_step:
            raise ValueError(
                f"target_step {target_step} > current_step {state.current_step}"
            )

        # Find the step result in history
        step_result = None
        for sr in state.step_history:
            if sr.step == target_step:
                step_result = sr
                break

        if step_result is None:
            raise StepNotFoundError(
                f"Step {target_step} not found in history for simulation {simulation_id}"
            )

        # Reset current_step to target so simulation can be re-run from this point.
        # Trim history to only include steps up to and including target_step.
        state.current_step = target_step
        state.step_history = [sr for sr in state.step_history if sr.step <= target_step]
        # Re-enable running from this branch point
        if state.status == SimulationStatus.COMPLETED.value:
            state.status = SimulationStatus.PAUSED.value

        return step_result

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _get_state(self, simulation_id: UUID) -> SimulationState:
        """Get simulation state by ID."""
        if simulation_id not in self._simulations:
            raise ValueError(f"Simulation {simulation_id} not found")
        return self._simulations[simulation_id]

    def _validate_transition(self, from_status: str, to_status: str) -> None:
        """Validate state transition.
        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulation-lifecycle
        """
        allowed = _VALID_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition from {from_status} to {to_status}"
            )

    def get_state(self, simulation_id: UUID) -> SimulationState:
        """Public accessor for simulation state."""
        return self._get_state(simulation_id)

    # ------------------------------------------------------------------ #
    # Agent / Community query methods (called from API endpoints)
    # SPEC: docs/spec/06_API_SPEC.md#3-agent-endpoints
    # SPEC: docs/spec/06_API_SPEC.md#5-community-endpoints
    # ------------------------------------------------------------------ #

    def list_agents(
        self,
        simulation_id: str | UUID,
        community_id: str | None = None,
        action: str | None = None,
        adopted: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Return a paginated, filtered list of agents for a simulation.

        SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idagents
        """
        sim_uuid = UUID(str(simulation_id)) if not isinstance(simulation_id, UUID) else simulation_id
        state = self._get_state(sim_uuid)

        agents = state.agents

        # Apply filters
        if community_id is not None:
            agents = [a for a in agents if str(a.community_id) == community_id]
        if action is not None:
            agents = [a for a in agents if a.action.value == action]
        if adopted is not None:
            agents = [a for a in agents if a.adopted == adopted]

        total = len(agents)
        page = agents[offset: offset + limit]

        items = [
            {
                "agent_id": str(a.agent_id),
                "community_id": str(a.community_id),
                "agent_type": a.agent_type.value,
                "action": a.action.value,
                "adopted": a.adopted,
                "influence_score": a.influence_score,
                "belief": a.belief,
            }
            for a in page
        ]
        return {"items": items, "total": total}

    def get_agent(self, simulation_id: str | UUID, agent_id_str: str) -> dict:
        """Return full agent state dict.

        SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idagentsagent_id

        Raises:
            ValueError: agent not found
        """
        sim_uuid = UUID(str(simulation_id)) if not isinstance(simulation_id, UUID) else simulation_id
        state = self._get_state(sim_uuid)

        agent = None
        for a in state.agents:
            if str(a.agent_id) == agent_id_str:
                agent = a
                break

        if agent is None:
            raise ValueError(f"Agent {agent_id_str} not found in simulation {simulation_id}")

        return {
            "agent_id": str(agent.agent_id),
            "community_id": str(agent.community_id),
            "agent_type": agent.agent_type.value,
            "action": agent.action.value,
            "adopted": agent.adopted,
            "influence_score": agent.influence_score,
            "belief": agent.belief,
            "personality": {
                "openness": agent.personality.openness,
                "skepticism": agent.personality.skepticism,
                "trend_following": agent.personality.trend_following,
                "brand_loyalty": agent.personality.brand_loyalty,
                "social_influence": agent.personality.social_influence,
            },
            "emotion": {
                "interest": agent.emotion.interest,
                "trust": agent.emotion.trust,
                "skepticism": agent.emotion.skepticism,
                "excitement": agent.emotion.excitement,
            },
            "memories": [],
        }

    def list_communities(self, simulation_id: str | UUID) -> dict:
        """Return community-level aggregate metrics.

        SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idcommunities
        """
        sim_uuid = UUID(str(simulation_id)) if not isinstance(simulation_id, UUID) else simulation_id
        state = self._get_state(sim_uuid)

        # Group agents by community_id
        from collections import defaultdict
        groups: dict = defaultdict(list)
        for a in state.agents:
            groups[a.community_id].append(a)

        communities = []
        for cid, members in groups.items():
            count = len(members)
            adopted_count = sum(1 for a in members if a.adopted)
            adoption_rate = adopted_count / count if count > 0 else 0.0
            mean_belief = sum(a.belief for a in members) / count if count > 0 else 0.0

            # Dominant action
            action_counts: Counter = Counter(a.action.value for a in members)
            dominant_action = action_counts.most_common(1)[0][0] if action_counts else "ignore"

            communities.append({
                "community_id": str(cid),
                "name": str(cid)[:8],
                "size": count,
                "adoption_rate": adoption_rate,
                "mean_belief": mean_belief,
                "sentiment_variance": 0.0,
                "dominant_action": dominant_action,
            })

        return {"communities": communities}

    def patch_agent(
        self,
        simulation_id: str | UUID,
        agent_id_str: str,
        updates_dict: dict,
    ) -> dict:
        """Apply field updates to an agent and return the updated agent dict.

        SPEC: docs/spec/06_API_SPEC.md#patch-simulationssimulation_idagentsagent_id

        Raises:
            ValueError: agent not found
        """
        sim_uuid = UUID(str(simulation_id)) if not isinstance(simulation_id, UUID) else simulation_id
        state = self._get_state(sim_uuid)

        agent_idx = None
        for i, a in enumerate(state.agents):
            if str(a.agent_id) == agent_id_str:
                agent_idx = i
                break

        if agent_idx is None:
            raise ValueError(f"Agent {agent_id_str} not found in simulation {simulation_id}")

        agent = state.agents[agent_idx]
        update_kwargs: dict = {}

        if "belief" in updates_dict:
            update_kwargs["belief"] = max(-1.0, min(1.0, float(updates_dict["belief"])))
        if "personality" in updates_dict:
            p = updates_dict["personality"]
            if isinstance(p, dict):
                from app.engine.agent.schema import AgentPersonality
                update_kwargs["personality"] = AgentPersonality(
                    openness=p.get("openness", agent.personality.openness),
                    skepticism=p.get("skepticism", agent.personality.skepticism),
                    trend_following=p.get("trend_following", agent.personality.trend_following),
                    brand_loyalty=p.get("brand_loyalty", agent.personality.brand_loyalty),
                    social_influence=p.get("social_influence", agent.personality.social_influence),
                )
            else:
                update_kwargs["personality"] = p
        if "emotion" in updates_dict:
            e = updates_dict["emotion"]
            if isinstance(e, dict):
                from app.engine.agent.schema import AgentEmotion
                update_kwargs["emotion"] = AgentEmotion(
                    interest=e.get("interest", agent.emotion.interest),
                    trust=e.get("trust", agent.emotion.trust),
                    skepticism=e.get("skepticism", agent.emotion.skepticism),
                    excitement=e.get("excitement", agent.emotion.excitement),
                )
            else:
                update_kwargs["emotion"] = e

        if update_kwargs:
            state.agents[agent_idx] = replace(agent, **update_kwargs)

        return self.get_agent(sim_uuid, agent_id_str)

    def get_agent_memory(
        self,
        simulation_id: str | UUID,
        agent_id_str: str,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Return agent memory records (stub — memory records are in-memory only).

        SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idagentsagent_idmemory
        """
        sim_uuid = UUID(str(simulation_id)) if not isinstance(simulation_id, UUID) else simulation_id
        # Validate agent exists (raises ValueError if not found)
        self.get_agent(sim_uuid, agent_id_str)
        return {"memories": []}

    async def delete_simulation(self, simulation_id: UUID) -> None:
        """Remove simulation state from memory.
        SPEC: docs/spec/09_HARNESS_SPEC.md#memory-eviction-policy

        Raises:
            KeyError: simulation_id not found
        """
        if simulation_id not in self._simulations:
            raise KeyError(f"Simulation {simulation_id} not found")
        del self._simulations[simulation_id]
        if simulation_id in self._locks:
            del self._locks[simulation_id]


__all__ = ["SimulationOrchestrator", "SimulationState"]
