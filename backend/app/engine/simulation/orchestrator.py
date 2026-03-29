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

            # Random personality
            personality = AgentPersonality(
                openness=rng.uniform(0.2, 0.8),
                skepticism=rng.uniform(0.2, 0.8),
                trend_following=rng.uniform(0.2, 0.8),
                brand_loyalty=rng.uniform(0.2, 0.8),
                social_influence=rng.uniform(0.2, 0.8),
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

        Raises:
            ValueError: target_step > current_step
            StepNotFoundError: step not in history
        """
        state = self._get_state(simulation_id)

        if target_step > state.current_step:
            raise ValueError(
                f"target_step {target_step} > current_step {state.current_step}"
            )

        # Check if step is in history
        for sr in state.step_history:
            if sr.step == target_step:
                return sr

        raise StepNotFoundError(
            f"Step {target_step} not found in history for simulation {simulation_id}"
        )

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
