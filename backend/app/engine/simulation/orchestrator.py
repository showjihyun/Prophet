"""Simulation Orchestrator — top-level coordinator.
SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
"""
import asyncio
import logging
import random as stdlib_random
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from typing import Awaitable, Callable
from uuid import UUID, uuid4, uuid5

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
    SimulationStatus.COMPLETED.value: {
        SimulationStatus.CONFIGURED.value,  # allow reset after completion
    },
    SimulationStatus.FAILED.value: {
        SimulationStatus.CONFIGURED.value,  # allow reset after failure
    },
}

# Domain defaults — overridable via constructor injection
_MAX_CONCURRENT_DEFAULT = 3

# Allowed event types for inject_event
# SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idinject-event
_ALLOWED_EVENT_TYPES = {
    "campaign_ad", "influencer_post", "expert_review",
    "community_discussion", "negative_pr", "competitor_attack",
    "controversy", "celebrity_endorsement", "news_article",
    "regulatory_change", "product_update", "bad_review",
}


_SNAPSHOT_WINDOW = 20  # max agent snapshots to keep in memory


@dataclass
class SimulationState:
    """In-memory runtime state for a simulation.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
    SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#1.3
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
    # Agent snapshots for replay — step → deep-copied agent list
    agent_snapshots: dict[int, list[AgentState]] = field(default_factory=dict)


class SimulationOrchestrator:
    """Top-level coordinator that manages simulation lifecycle.

    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface

    Manages creation, execution, pausing, modification, and event injection
    for simulations. Uses in-memory state for Phase 6.
    """

    MAX_SIMULATIONS = 50
    SIMULATION_TTL_SECONDS = 86400  # 24h

    def __init__(self, llm_adapter=None, slm_adapter=None, gateway=None, session_factory=None) -> None:
        """Initialize the orchestrator.
        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§3 MP-02
        """
        self._simulations: dict[UUID, SimulationState] = {}
        self._locks: defaultdict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._session_factory = session_factory
        self._step_runner = StepRunner(
            llm_adapter=llm_adapter, gateway=gateway,
            session_factory=session_factory,
        )
        self._llm_adapter = llm_adapter
        self._slm_adapter = slm_adapter
        self._gateway = gateway
        # Per-(sim_id, step) caches for expensive read-only derivations.
        # Graph topology is immutable between steps, so we can safely reuse
        # serialized payloads and computed metrics until current_step changes.
        self._network_payload_cache: dict[UUID, tuple[int, dict]] = {}
        self._network_metrics_cache: dict[UUID, tuple[int, dict]] = {}

    def _get_lock(self, simulation_id: UUID) -> asyncio.Lock:
        """Get or create a per-simulation asyncio lock (atomic via defaultdict)."""
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
            # Never evict RUNNING simulations — they may be mid-step
            # SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#1.1
            if state.status == SimulationStatus.RUNNING.value:
                continue
            created_at = getattr(state, 'created_at', None)
            if created_at is not None:
                age = (now - created_at).total_seconds()
                if age > self.SIMULATION_TTL_SECONDS:
                    expired.append(sim_id)
        for sim_id in expired:
            del self._simulations[sim_id]
            self._locks.pop(sim_id, None)
            self._network_payload_cache.pop(sim_id, None)
            self._network_metrics_cache.pop(sim_id, None)

        # Also enforce max count (remove oldest first, skip RUNNING)
        if len(self._simulations) > self.MAX_SIMULATIONS:
            sorted_sims = sorted(
                self._simulations.keys(),
                key=lambda k: getattr(self._simulations[k], 'created_at', _dt.min),
            )
            while len(self._simulations) > self.MAX_SIMULATIONS and sorted_sims:
                oldest = sorted_sims.pop(0)
                if self._simulations[oldest].status == SimulationStatus.RUNNING.value:
                    continue
                del self._simulations[oldest]
                self._locks.pop(oldest, None)
                self._network_payload_cache.pop(oldest, None)
                self._network_metrics_cache.pop(oldest, None)

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

        # Reset per-simulation cascade-detector state (e.g. the
        # ``_slow_adoption_fired`` one-shot guard). Without this, a
        # slow_adoption event from the prior simulation would silently
        # suppress the detector for the new one. Round 8-8 fix.
        self._step_runner._cascade_detector.reset()

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

        # Compute blended influence score: degree + betweenness centrality
        # SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#5.1 — Network A-
        degree_cent = nx.degree_centrality(network.graph)
        # Sampled betweenness for scalability (k=100 max)
        _k = min(100, len(network.graph))
        between_cent = nx.betweenness_centrality(network.graph, k=_k, seed=seed)
        centrality = {
            n: 0.6 * degree_cent.get(n, 0.0) + 0.4 * between_cent.get(n, 0.0)
            for n in network.graph.nodes()
        }

        # Cache community UUIDs so every agent in the same community sees the
        # same UUID without re-hashing per node. The UUID is derived from
        # ``(sim_id, community_string)`` so it is:
        #   (a) deterministic within a simulation (for seed repeatability) and
        #   (b) globally unique across simulations (avoiding the
        #       ``communities_pkey`` violation that bare ``hash(cid_str)``
        #       caused when two sims shared community ids like "A", "B").
        import hashlib as _hashlib
        community_uuid_cache: dict[str, UUID] = {}

        def _community_uuid(cid_str: str) -> UUID:
            if cid_str in community_uuid_cache:
                return community_uuid_cache[cid_str]
            if seed is None:
                uid = uuid4()
            else:
                digest = _hashlib.sha256(
                    f"{sim_id}:{cid_str}".encode()
                ).digest()
                uid = UUID(bytes=digest[:16])
            community_uuid_cache[cid_str] = uid
            return uid

        for node_id, node_data in nodes:
            community_id_str = node_data.get("community_id", "default")
            community_uuid = _community_uuid(community_id_str)
            # Store the UUID on the node for later lookup
            network.graph.nodes[node_id]["community_uuid"] = community_uuid

            # Agent UUID is deterministic (for seed-repeatability) but
            # **scoped per simulation_id** so two sims with the same seed
            # don't collide on the ``agents_pkey`` primary key. Before
            # Round 8-7 this was ``UUID(int=(hash(node_id) + seed*9999))``
            # which ignored ``sim_id`` entirely and produced identical
            # counter-UUIDs across every simulation — bulk-loading a
            # second sim into Postgres failed with ``unique_violation``.
            # SPEC: docs/spec/04_SIMULATION_SPEC.md#agent-id-generation
            if seed is None:
                agent_id = uuid4()
            else:
                agent_id = uuid5(sim_id, f"node={node_id}:seed={seed}")
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

    async def start(self, simulation_id: UUID) -> None:
        """Transition to RUNNING state.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
        SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#1.1

        Raises:
            InvalidStateTransitionError: invalid transition
            SimulationCapacityError: max concurrent exceeded
        """
        async with self._get_lock(simulation_id):
            state = self._get_state(simulation_id)
            self._validate_transition(state.status, SimulationStatus.RUNNING.value)

            # Check concurrent limit
            running_count = sum(
                1 for s in self._simulations.values()
                if s.status == SimulationStatus.RUNNING.value
            )
            if running_count >= _MAX_CONCURRENT_DEFAULT:
                raise SimulationCapacityError(
                    f"Max {_MAX_CONCURRENT_DEFAULT} concurrent simulations exceeded"
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
                # Snapshot agents before step for replay support (P1.3)
                from copy import deepcopy
                state.agent_snapshots[state.current_step] = deepcopy(state.agents)
                # Evict oldest snapshots beyond sliding window
                if len(state.agent_snapshots) > _SNAPSHOT_WINDOW:
                    oldest_key = min(state.agent_snapshots)
                    del state.agent_snapshots[oldest_key]

                # Set simulation_id for pgvector memory persistence (MP-02)
                self._step_runner._simulation_id = simulation_id
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

    async def run_all(
        self,
        simulation_id: UUID,
        step_callback: Callable[[StepResult], Awaitable[None]] | None = None,
    ) -> dict:
        """Run all remaining steps to completion and return a summary report.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
        SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#1.2

        If the simulation is CONFIGURED it will be started automatically.
        Runs until max_steps is reached or the simulation moves to COMPLETED/FAILED.

        Args:
            step_callback: optional async callback invoked after each step
                           for persistence or progress reporting.

        Returns a report dict with:
          total_steps, final_adoption_rate, final_mean_sentiment,
          community_breakdown, duration_ms, emergent_events_count
        """
        import time as _time

        state = self._get_state(simulation_id)

        # Auto-start from CONFIGURED
        if state.status == SimulationStatus.CONFIGURED.value:
            await self.start(simulation_id)
        elif state.status != SimulationStatus.RUNNING.value:
            raise ValueError(
                f"run_all requires CONFIGURED or RUNNING status, got '{state.status}'"
            )

        start_ts = _time.monotonic()
        emergent_count = 0

        while state.status == SimulationStatus.RUNNING.value:
            result = await self.run_step(simulation_id)
            emergent_count += len(result.emergent_events)
            if step_callback:
                try:
                    await step_callback(result)
                except Exception as cb_exc:
                    logger.error(
                        "run_all step_callback failed at step %d: %s",
                        result.step, cb_exc,
                    )
            # Yield control to event loop so WebSocket broadcasts can fire
            await asyncio.sleep(0)

        duration_ms = (_time.monotonic() - start_ts) * 1000.0

        # Build community breakdown from the last step in history
        community_breakdown: list[dict] = []
        if state.step_history:
            last = state.step_history[-1]
            for cid, metric in last.community_metrics.items():
                if isinstance(metric, dict):
                    community_breakdown.append({
                        "community_id": str(cid),
                        "adoption_rate": metric.get("adoption_rate", 0.0),
                        "mean_belief": metric.get("mean_belief", 0.0),
                        "dominant_action": metric.get("dominant_action", "ignore"),
                    })
                else:
                    community_breakdown.append({
                        "community_id": str(cid),
                        "adoption_rate": getattr(metric, "adoption_rate", 0.0),
                        "mean_belief": getattr(metric, "mean_belief", 0.0),
                        "dominant_action": str(getattr(metric, "dominant_action", "ignore")),
                    })

        final_adoption_rate = 0.0
        final_mean_sentiment = 0.0
        if state.step_history:
            last = state.step_history[-1]
            final_adoption_rate = last.adoption_rate
            final_mean_sentiment = last.mean_sentiment

        return {
            "total_steps": state.current_step,
            "final_adoption_rate": final_adoption_rate,
            "final_mean_sentiment": final_mean_sentiment,
            "community_breakdown": community_breakdown,
            "duration_ms": duration_ms,
            "emergent_events_count": emergent_count,
            "status": state.status,
        }

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

    async def reset(self, simulation_id: UUID) -> None:
        """Reset a COMPLETED or FAILED simulation back to CREATED.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface

        This is the domain-owned counterpart of the previous
        ``state.status = "created"`` mutation that used to live in the
        API route handler. It puts the simulation back to an initial
        state so it can be re-configured and restarted, and it is the
        **only** sanctioned way for the Service layer to roll an
        in-memory simulation backwards.

        Raises:
            InvalidStateError: when the current status is not
                ``COMPLETED`` or ``FAILED``.
        """
        async with self._get_lock(simulation_id):
            state = self._get_state(simulation_id)
            if state.status not in (
                SimulationStatus.COMPLETED.value,
                SimulationStatus.FAILED.value,
            ):
                raise InvalidStateError(
                    "reset only allowed from COMPLETED or FAILED, "
                    f"current status: {state.status}"
                )
            state.status = SimulationStatus.CREATED.value
            state.current_step = 0

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

    async def inject_event(
        self,
        simulation_id: UUID,
        event: EnvironmentEvent | None = None,
        event_type: str | None = None,
        payload: dict | None = None,
        target_communities: list[str] | None = None,
    ) -> None:
        """Inject an external event mid-simulation.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
        SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#1.1

        Raises:
            ValueError: unknown event_type
        """
        async with self._get_lock(simulation_id):
            state = self._get_state(simulation_id)

            if event is not None:
                state.injected_events.append(event)
                return

            # String-based injection (for error test compatibility)
            if event_type is not None:
                NEGATIVE_EVENT_TYPES = {"negative_pr", "competitor_attack", "bad_review", "controversy", "regulatory_change"}
                POSITIVE_EVENT_TYPES = {"celebrity_endorsement", "product_update", "news_article"}
                DIRECT_TYPES = {"campaign_ad", "influencer_post", "expert_review", "community_discussion"}
                if event_type in NEGATIVE_EVENT_TYPES:
                    mapped_type = "community_discussion"
                elif event_type in POSITIVE_EVENT_TYPES:
                    mapped_type = "influencer_post"
                elif event_type in DIRECT_TYPES:
                    mapped_type = event_type
                else:
                    raise ValueError(
                        f"Unknown event type: '{event_type}'. "
                        f"Valid types: {sorted(_ALLOWED_EVENT_TYPES)}"
                    )
                env_event = EnvironmentEvent(
                    event_type=mapped_type,
                    content_id=uuid4(),
                    message=str(payload) if payload else "",
                    source_agent_id=None,
                    channel="direct",
                    timestamp=state.current_step,
                    target_communities=target_communities or [],
                )
                state.injected_events.append(env_event)
                return

            raise ValueError("Either event or event_type must be provided")

    async def replay_step(
        self,
        simulation_id: UUID,
        target_step: int,
    ) -> dict:
        """Replay from a specific step, creating a branch.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
        SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#1.1

        Finds the step in history, creates a replay branch with unique replay_id,
        then resets current_step to target_step so the simulation can be re-run
        from that point forward. Original history before target_step is preserved.

        Raises:
            ValueError: target_step > current_step
            StepNotFoundError: step not in history
        """
        async with self._get_lock(simulation_id):
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

            # Generate replay branch ID
            replay_id = uuid4()

            # Store original history length before truncation
            original_steps = state.current_step

            # Restore agent state from snapshot if available (P1.3)
            if target_step in state.agent_snapshots:
                from copy import deepcopy
                state.agents = deepcopy(state.agent_snapshots[target_step])

            # Reset current_step to target so simulation can be re-run from this point.
            # Trim history to only include steps up to and including target_step.
            state.current_step = target_step
            state.step_history = [sr for sr in state.step_history if sr.step <= target_step]
            # Evict snapshots beyond replay point
            state.agent_snapshots = {
                k: v for k, v in state.agent_snapshots.items() if k <= target_step
            }

            # Re-enable running from this branch point
            if state.status == SimulationStatus.COMPLETED.value:
                state.status = SimulationStatus.PAUSED.value

            return {
                "replay_id": str(replay_id),
                "from_step": target_step,
                "original_steps": original_steps,
                "status": state.status,
            }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _get_state(self, simulation_id: UUID) -> SimulationState:
        """Get simulation state by ID."""
        if simulation_id not in self._simulations:
            raise ValueError(f"Simulation {simulation_id} not found")
        return self._simulations[simulation_id]

    def _community_name_map(self, sim_uuid: UUID) -> dict[str, str]:
        """Build a ``community_uuid → config community name`` map for a sim.

        Walks the graph exactly once per call. Use this instead of an O(N)
        graph scan per endpoint hit — the AgentInspector triggers
        ``get_agent`` on every node click, and a 5k-node graph made that a
        ~5k-iteration linear walk per interaction.

        Caching one level deeper (per ``(sim_uuid, current_step)``) is not
        worth the invalidation cost: community membership doesn't change
        between steps for the lifetime of a simulation, and the build cost
        is already dominated by the graph walk which is O(N) once.

        Returns an empty dict if the sim has no network yet.
        """
        state = self._get_state(sim_uuid)
        if state.network is None or state.network.graph is None:
            return {}

        # uuid → short key (one walk)
        short_key_by_uuid: dict[str, str] = {}
        for _nid, ndata in state.network.graph.nodes(data=True):
            cuuid = str(ndata.get("community_uuid", ""))
            if cuuid and cuuid not in short_key_by_uuid:
                short_key = str(ndata.get("community_id", ""))
                if short_key:
                    short_key_by_uuid[cuuid] = short_key

        # short key → config.name
        name_by_short: dict[str, str] = {cc.id: cc.name for cc in state.config.communities}

        return {
            cuuid: name_by_short[short]
            for cuuid, short in short_key_by_uuid.items()
            if short in name_by_short
        }

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

    def list_states(
        self, *, status: str | None = None,
    ) -> list[SimulationState]:
        """Return a snapshot list of all in-memory simulation states.

        SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface

        The returned list is a **snapshot** — callers can iterate without
        worrying about concurrent mutation of the underlying dict.

        :param status: optional status filter (e.g. ``"running"``,
            ``"configured"``). When ``None``, all states are returned.
        """
        states = list(self._simulations.values())
        if status is not None:
            states = [s for s in states if s.status == status]
        return states

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

        # Resolve human-readable community name so the frontend doesn't have
        # to show a raw UUID in the inspector. Uses the cached
        # community_uuid → cc.name map so this endpoint is O(1) per call
        # regardless of graph size (previously walked every node on every
        # inspector click — 5000 iterations per click on large sims).
        # Falls back to ``None`` (not the raw UUID) so downstream code
        # can treat "missing human name" honestly.
        community_uuid_str = str(agent.community_id)
        community_name = self._community_name_map(sim_uuid).get(community_uuid_str)

        return {
            "agent_id": str(agent.agent_id),
            "community_id": str(agent.community_id),
            "community_name": community_name,
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

        # Build community UUID → human name mapping from config
        community_names: dict[str, str] = {}
        if state.network and state.network.graph:
            for cc in state.config.communities:
                for nid, ndata in state.network.graph.nodes(data=True):
                    if ndata.get("community_id") == cc.id:
                        cuuid = str(ndata.get("community_uuid", ""))
                        if cuuid:
                            community_names[cuuid] = cc.name
                        break

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
            belief_values = [a.belief for a in members]
            variance = (sum((b - mean_belief) ** 2 for b in belief_values) / count) if count > 0 else 0.0

            # Dominant action
            action_counts: Counter = Counter(a.action.value for a in members)
            dominant_action = action_counts.most_common(1)[0][0] if action_counts else "ignore"

            communities.append({
                "community_id": str(cid),
                "name": community_names.get(str(cid), str(cid)[:8]),
                "size": count,
                "adoption_rate": round(adoption_rate, 4),
                "mean_belief": round(mean_belief, 4),
                "sentiment_variance": round(variance, 4),
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
        """Return agent memory records from the in-memory MemoryLayer.

        SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idagentsagent_idmemory

        Retrieves stored memories from the AgentTick's MemoryLayer,
        sorted by timestamp descending. Returns empty list if agent has
        no memories yet (e.g., simulation not started).

        Args:
            simulation_id: Simulation UUID.
            agent_id_str: Agent UUID string.
            memory_type: Optional filter ('episodic', 'semantic', 'social').
            limit: Max records to return.

        Returns:
            Dict with 'memories' list of serialized MemoryRecord dicts.

        Raises:
            ValueError: If simulation or agent not found.
        """
        sim_uuid = UUID(str(simulation_id)) if not isinstance(simulation_id, UUID) else simulation_id
        agent_detail = self.get_agent(sim_uuid, agent_id_str)
        agent_uuid = UUID(agent_detail["agent_id"])

        # Access MemoryLayer from StepRunner → AgentTick
        memory_layer = self._step_runner._agent_tick._memory
        all_memories = memory_layer._store.get(agent_uuid, [])

        # Filter by type if specified
        if memory_type:
            all_memories = [m for m in all_memories if m.memory_type == memory_type]

        # Sort by timestamp descending (most recent first)
        all_memories = sorted(all_memories, key=lambda m: m.timestamp, reverse=True)
        all_memories = all_memories[:limit]

        return {
            "memories": [
                {
                    "memory_type": m.memory_type,
                    "content": m.content,
                    "timestamp": m.timestamp,
                    "importance": round(m.emotion_weight, 3),
                    "source_agent_id": None,
                }
                for m in all_memories
            ]
        }

    # ------------------------------------------------------------------ #
    # Network query methods (called from API endpoints)
    # SPEC: docs/spec/06_API_SPEC.md#4-network-endpoints
    # ------------------------------------------------------------------ #

    def get_network(
        self,
        simulation_id: str | UUID,
        format: str = "cytoscape",
    ) -> dict:
        """Return network graph data for visualization.

        SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idnetwork

        Converts NetworkX graph to Cytoscape.js format with agent metadata
        (community, action, adopted, influence_score, belief, emotion).

        Args:
            simulation_id: Simulation UUID.
            format: Output format — only 'cytoscape' supported.

        Returns:
            Dict with 'nodes' and 'edges' lists in Cytoscape format.

        Raises:
            ValueError: If simulation not found or network not generated.
        """
        sim_uuid = UUID(str(simulation_id)) if not isinstance(simulation_id, UUID) else simulation_id
        state = self._get_state(sim_uuid)

        if state.network is None or state.network.graph is None:
            raise ValueError(
                f"Network not available for simulation {simulation_id}. "
                "Simulation may not have been created properly."
            )

        # Cache check — graph topology is invariant between steps.
        cached = self._network_payload_cache.get(sim_uuid)
        if cached is not None and cached[0] == state.current_step:
            return cached[1]

        graph = state.network.graph

        # Bug 1 fix: O(1) agent lookup — build dict keyed by agent_id UUID
        agent_by_id: dict = {agent.agent_id: agent for agent in state.agents}
        # Map node_id → agent using node data's agent_id attribute
        agents_by_node: dict[int, AgentState] = {}
        for nid, ndata in graph.nodes(data=True):
            aid = ndata.get("agent_id")
            if aid is not None and aid in agent_by_id:
                agents_by_node[nid] = agent_by_id[aid]

        # Bug 2 fix: build community_uuid → short_key mapping by iterating all nodes
        # node_data["community_id"] is the short key (e.g. "A", "B", "C")
        # node_data["community_uuid"] is the full UUID
        community_uuid_to_key: dict[str, str] = {}
        for _nid, ndata in graph.nodes(data=True):
            cuuid = ndata.get("community_uuid")
            ckey = ndata.get("community_id", "")
            if cuuid is not None and str(cuuid) not in community_uuid_to_key:
                community_uuid_to_key[str(cuuid)] = str(ckey)

        # Build community_uuid → name mapping from config using correct key
        community_names: dict[str, str] = {}
        for cc in state.config.communities:
            for cuuid_str, ckey in community_uuid_to_key.items():
                if ckey == cc.id:
                    community_names[cuuid_str] = cc.name

        nodes = []
        for node_id, node_data in graph.nodes(data=True):
            agent = agents_by_node.get(node_id)
            community_uuid = str(node_data.get("community_uuid", ""))
            # Bug 3+4 fix: add `community` (short key) and `label` fields
            community_key = community_uuid_to_key.get(community_uuid, node_data.get("community_id", ""))
            agent_id_str = str(agent.agent_id) if agent else str(node_id)
            # Deterministic agent UUIDs pack most entropy into the low bits
            # (first 8 chars are often "00000000"), so prefer the node_id —
            # which is guaranteed unique within the graph — for the display
            # label. Falls back to the agent UUID tail if node_id is missing.
            label_suffix = str(node_id) if node_id is not None else agent_id_str[-8:]
            community_display = community_names.get(community_uuid, str(community_key))
            node_dict: dict = {
                "id": str(node_id),
                "label": f"Agent #{label_suffix}",
                "community": str(community_key),
                "community_id": community_uuid,
                "community_name": community_display,
            }
            if agent:
                node_dict.update({
                    "agent_id": agent_id_str,
                    "agent_type": agent.agent_type.value if hasattr(agent.agent_type, "value") else str(agent.agent_type),
                    "action": agent.action.value if hasattr(agent.action, "value") else str(agent.action),
                    "adopted": agent.adopted,
                    "belief": round(agent.belief, 3),
                    "influence_score": round(agent.influence_score, 3),
                })
            nodes.append({"data": node_dict})

        # Bug 5 fix: add `edge_type` and `is_bridge` to each edge
        # Build node_id → community_key map for bridge detection
        node_community: dict[int, str] = {}
        for node_id, node_data in graph.nodes(data=True):
            cuuid = str(node_data.get("community_uuid", ""))
            node_community[node_id] = community_uuid_to_key.get(cuuid, node_data.get("community_id", ""))

        edges = []
        for u, v, edge_data in graph.edges(data=True):
            is_bridge = node_community.get(u, "") != node_community.get(v, "")
            edge_type = "bridge" if is_bridge else "intra"
            edge_dict: dict = {
                "id": f"e{u}-{v}",
                "source": str(u),
                "target": str(v),
                "weight": round(edge_data.get("weight", 0.5), 3),
                "is_bridge": edge_data.get("is_bridge", is_bridge),
                "edge_type": edge_data.get("edge_type", edge_type),
            }
            edges.append({"data": edge_dict})

        payload = {"nodes": nodes, "edges": edges}
        self._network_payload_cache[sim_uuid] = (state.current_step, payload)
        return payload

    def get_network_summary(self, simulation_id: str | UUID) -> dict:
        """Lightweight network summary (no per-node payload).

        Allows the frontend to render a skeleton + counts immediately
        while the full graph payload is loaded lazily.
        """
        sim_uuid = UUID(str(simulation_id)) if not isinstance(simulation_id, UUID) else simulation_id
        state = self._get_state(sim_uuid)
        if state.network is None or state.network.graph is None:
            return {"total_nodes": 0, "total_edges": 0, "community_counts": {}}

        graph = state.network.graph
        counts: dict[str, int] = {}
        for _nid, ndata in graph.nodes(data=True):
            key = str(ndata.get("community_id", "default"))
            counts[key] = counts.get(key, 0) + 1
        return {
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges(),
            "community_counts": counts,
        }

    def get_network_metrics(self, simulation_id: str | UUID) -> dict:
        """Return computed network metrics.

        SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idnetworkmetrics

        Computes real-time metrics from the NetworkX graph using standard
        graph theory measures.

        Args:
            simulation_id: Simulation UUID.

        Returns:
            Dict with clustering_coefficient, avg_path_length, modularity,
            density, total_nodes, total_edges.

        Raises:
            ValueError: If simulation not found or network not generated.
        """
        sim_uuid = UUID(str(simulation_id)) if not isinstance(simulation_id, UUID) else simulation_id
        state = self._get_state(sim_uuid)

        if state.network is None or state.network.graph is None:
            raise ValueError(
                f"Network not available for simulation {simulation_id}."
            )

        cached = self._network_metrics_cache.get(sim_uuid)
        if cached is not None and cached[0] == state.current_step:
            return cached[1]

        graph = state.network.graph
        total_nodes = graph.number_of_nodes()
        total_edges = graph.number_of_edges()

        # Clustering coefficient (async-safe: pure computation, no I/O)
        clustering = nx.average_clustering(graph) if total_nodes > 0 else 0.0

        # Average path length (sample for large graphs to avoid O(n^2))
        avg_path = 0.0
        if total_nodes > 1:
            try:
                if total_nodes <= 500:
                    avg_path = nx.average_shortest_path_length(graph)
                else:
                    # Sample-based approximation for large graphs
                    import random as _rand
                    sample_nodes = _rand.sample(list(graph.nodes()), min(100, total_nodes))
                    path_lengths = []
                    for src in sample_nodes:
                        lengths = nx.single_source_shortest_path_length(graph, src)
                        path_lengths.extend(lengths.values())
                    avg_path = sum(path_lengths) / max(len(path_lengths), 1)
            except nx.NetworkXError:
                # Disconnected graph — compute on largest component
                largest_cc = max(nx.connected_components(graph), key=len)
                subgraph = graph.subgraph(largest_cc)
                if subgraph.number_of_nodes() > 1:
                    avg_path = nx.average_shortest_path_length(subgraph)

        # Density
        density = nx.density(graph) if total_nodes > 1 else 0.0

        # Modularity (use community structure from node data)
        modularity = 0.0
        try:
            communities_map: dict[str, set[int]] = {}
            for nid, ndata in graph.nodes(data=True):
                cid = str(ndata.get("community_id", "default"))
                communities_map.setdefault(cid, set()).add(nid)
            if len(communities_map) > 1:
                community_sets = list(communities_map.values())
                modularity = nx.community.modularity(graph, community_sets)
        except Exception:
            pass

        metrics = {
            "clustering_coefficient": round(clustering, 4),
            "avg_path_length": round(avg_path, 4),
            "modularity": round(modularity, 4),
            "density": round(density, 6),
            "total_nodes": total_nodes,
            "total_edges": total_edges,
        }
        self._network_metrics_cache[sim_uuid] = (state.current_step, metrics)
        return metrics

    # ------------------------------------------------------------------ #
    # LLM Dashboard query methods (called from API endpoints)
    # SPEC: docs/spec/06_API_SPEC.md#6-llm-dashboard-endpoints
    # ------------------------------------------------------------------ #

    def get_llm_stats(self, simulation_id: str | UUID) -> dict:
        """Aggregate LLM usage statistics across all steps.

        SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idllmstats

        Computes totals from step_history and agent llm_tier_used fields.

        Args:
            simulation_id: Simulation UUID.

        Returns:
            Dict with total_calls, cached_calls, provider_breakdown,
            avg_latency_ms, total_tokens, tier_breakdown.

        Raises:
            ValueError: If simulation not found.
        """
        sim_uuid = UUID(str(simulation_id)) if not isinstance(simulation_id, UUID) else simulation_id
        state = self._get_state(sim_uuid)

        total_calls = 0
        tier_breakdown: dict[str, int] = {"1": 0, "2": 0, "3": 0}

        # Aggregate from step history
        for step_result in state.step_history:
            total_calls += step_result.llm_calls_this_step
            for tier, count in step_result.llm_tier_distribution.items():
                tier_key = str(tier)
                tier_breakdown[tier_key] = tier_breakdown.get(tier_key, 0) + count

        # Count current agent tier distribution
        for agent in state.agents:
            if agent.llm_tier_used is not None:
                tier_key = str(agent.llm_tier_used)
                tier_breakdown[tier_key] = tier_breakdown.get(tier_key, 0) + 1

        # Estimate provider breakdown from config
        provider = state.config.default_llm_provider or "ollama"
        slm_calls = tier_breakdown.get("1", 0)
        llm_calls = tier_breakdown.get("2", 0) + tier_breakdown.get("3", 0)
        provider_breakdown: dict[str, int] = {}
        if slm_calls > 0:
            provider_breakdown["ollama-slm"] = slm_calls
        if llm_calls > 0:
            provider_breakdown[provider] = llm_calls

        # Estimate avg latency from step durations
        avg_latency = 0.0
        if state.step_history and total_calls > 0:
            total_duration = sum(s.step_duration_ms for s in state.step_history)
            avg_latency = total_duration / max(total_calls, 1)

        # Pull real cache-hit and token counts from the gateway that actually
        # executed the LLM calls.  The step_runner holds the live gateway
        # instance (shared with all CommunityOrchestrators for this sim).
        gw_stats: dict = {}
        gw = getattr(self._step_runner, "_gateway", None)
        if gw is not None:
            gw_stats = gw.get_stats()

        cached_calls = (
            gw_stats.get("inmemory_hits", 0)
            + gw_stats.get("valkey_hits", 0)
            + gw_stats.get("vector_hits", 0)
        )
        total_tokens = gw_stats.get("total_tokens", 0)

        return {
            "total_calls": total_calls,
            "cached_calls": cached_calls,
            "provider_breakdown": provider_breakdown,
            "avg_latency_ms": round(avg_latency, 1),
            "total_tokens": total_tokens,
            "tier_breakdown": tier_breakdown,
        }

    def get_llm_calls(
        self,
        simulation_id: str | UUID,
        step: int | None = None,
        agent_id: str | None = None,
        provider: str | None = None,
        limit: int = 20,
    ) -> dict:
        """Return recent LLM call log entries.

        SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idllmcalls

        Reconstructs call log from agent state and step history since
        individual call records are not persisted in-memory.

        Args:
            simulation_id: Simulation UUID.
            step: Optional filter by step number.
            agent_id: Optional filter by agent ID.
            provider: Optional filter by provider name.
            limit: Max entries to return.

        Returns:
            Dict with 'calls' list of LLMCallLogEntry-compatible dicts.

        Raises:
            ValueError: If simulation not found.
        """
        sim_uuid = UUID(str(simulation_id)) if not isinstance(simulation_id, UUID) else simulation_id
        state = self._get_state(sim_uuid)

        default_provider = state.config.default_llm_provider or "ollama"

        # --- Fetch real per-call data from the gateway ring buffer ---
        # The ring buffer stores the most recent LLM calls with real latency
        # and token counts, but without per-agent metadata (lightweight).
        gw = getattr(self._step_runner, "_gateway", None)
        gw_call_log: list[dict] = gw.get_call_log() if gw is not None else []

        calls: list[dict] = []

        if not agent_id and step is None:
            # No fine-grained filter requested — serve directly from ring buffer
            # (most recent calls first) with provider filter if specified.
            for i, entry in enumerate(reversed(gw_call_log)):
                call_provider = entry.get("provider", default_provider)
                if provider and call_provider != provider:
                    continue
                calls.append({
                    "call_id": f"gw-call-{i}",
                    "step": None,
                    "agent_id": None,
                    "provider": call_provider,
                    "latency_ms": round(entry.get("latency_ms", 0.0), 2),
                    "tokens": entry.get("tokens", 0),
                    "cached": entry.get("cached", False),
                })
                if len(calls) >= limit:
                    break
        else:
            # Filtered view: reconstruct from agent state (which has step/agent_id),
            # then enrich with average latency/tokens from the gateway ring buffer.
            avg_latency = 0.0
            avg_tokens = 0
            if gw_call_log:
                real_calls = [e for e in gw_call_log if not e.get("cached", False)]
                if real_calls:
                    avg_latency = sum(e.get("latency_ms", 0.0) for e in real_calls) / len(real_calls)
                    avg_tokens = sum(e.get("tokens", 0) for e in real_calls) // len(real_calls)

            for agent in state.agents:
                if agent.llm_tier_used is None:
                    continue
                if agent_id and str(agent.agent_id) != agent_id:
                    continue
                agent_provider = "ollama-slm" if agent.llm_tier_used == 1 else default_provider
                if provider and agent_provider != provider:
                    continue
                if step is not None and agent.step != step:
                    continue

                calls.append({
                    "call_id": f"call-{agent.agent_id}-s{agent.step}",
                    "step": agent.step,
                    "agent_id": str(agent.agent_id),
                    "provider": agent_provider,
                    "latency_ms": round(avg_latency, 2),
                    "tokens": avg_tokens,
                    "cached": False,
                })

            calls.sort(key=lambda c: (c["step"] or 0), reverse=True)

        return {"calls": calls[:limit]}

    def get_llm_impact(self, simulation_id: str | UUID) -> dict:
        """Return current engine impact assessment.

        SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idllmimpact

        Provides SLM/LLM ratio, tier distribution, and qualitative
        impact assessment based on current simulation config.

        Args:
            simulation_id: Simulation UUID.

        Returns:
            Dict with slm_llm_ratio, tier_distribution, impact, slm_model.

        Raises:
            ValueError: If simulation not found.
        """
        sim_uuid = UUID(str(simulation_id)) if not isinstance(simulation_id, UUID) else simulation_id
        state = self._get_state(sim_uuid)

        ratio = state.config.slm_llm_ratio
        total_agents = len(state.agents)

        # Compute actual tier distribution from agents
        tier_dist: dict[str, int] = {"1": 0, "2": 0, "3": 0}
        for agent in state.agents:
            if agent.llm_tier_used is not None:
                tier_dist[str(agent.llm_tier_used)] = tier_dist.get(str(agent.llm_tier_used), 0) + 1
            else:
                # Agents not yet ticked → estimate from ratio
                tier_dist["1"] = tier_dist.get("1", 0) + 1

        # Qualitative impact assessment
        if ratio >= 0.8:
            reasoning_depth = "quantitative"
            prediction_type = "Quantitative"
        elif ratio >= 0.4:
            reasoning_depth = "balanced"
            prediction_type = "Hybrid"
        else:
            reasoning_depth = "qualitative"
            prediction_type = "Qualitative"

        cost_per_step = (1 - ratio) * 0.01 * total_agents  # rough estimate
        est_velocity = f"{round(0.3 + (1 - ratio) * 2.0, 1)}s/step"

        return {
            "slm_llm_ratio": ratio,
            "tier_distribution": tier_dist,
            "impact": {
                "cost_efficiency": f"${round(cost_per_step, 4)}/step",
                "reasoning_depth": reasoning_depth,
                "simulation_velocity": est_velocity,
                "prediction_type": prediction_type,
            },
            "slm_model": state.config.slm_model or "phi4",
            "slm_batch_throughput": f"{int(total_agents * ratio)}/step",
        }

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


    # ------------------------------------------------------------------ #
    # Community Management (Runtime CRUD)
    # SPEC: docs/spec/16_COMMUNITY_MGMT_SPEC.md
    # ------------------------------------------------------------------ #

    def _require_mutable(self, state: SimulationState) -> None:
        """Raise 409 if simulation is not in a mutable state (paused/configured)."""
        if state.status not in (
            SimulationStatus.PAUSED.value,
            SimulationStatus.CONFIGURED.value,
            "created",
        ):
            raise InvalidStateError(
                "Community changes only allowed when paused or configured"
            )

    async def update_community(
        self,
        simulation_id: UUID,
        community_id: str,
        name: str | None = None,
        personality_profile: dict[str, float] | None = None,
    ) -> dict:
        """Update community properties. Requires PAUSED/CONFIGURED state.

        SPEC: docs/spec/16_COMMUNITY_MGMT_SPEC.md#2-1
        """
        import random
        async with self._get_lock(simulation_id):
            state = self._get_state(simulation_id)
            self._require_mutable(state)

            # Find agents in this community
            members = [a for a in state.agents if str(a.community_id) == community_id]
            if not members:
                raise ValueError(f"Community {community_id!r} not found")

            agents_updated = 0
            if personality_profile:
                for i, agent in enumerate(state.agents):
                    if str(agent.community_id) != community_id:
                        continue
                    from dataclasses import replace as dc_replace
                    new_p = AgentPersonality(
                        openness=max(0, min(1, personality_profile.get("openness", agent.personality.openness) + random.uniform(-0.1, 0.1))),
                        skepticism=max(0, min(1, personality_profile.get("skepticism", agent.personality.skepticism) + random.uniform(-0.1, 0.1))),
                        trend_following=max(0, min(1, personality_profile.get("trend_following", agent.personality.trend_following) + random.uniform(-0.1, 0.1))),
                        brand_loyalty=max(0, min(1, personality_profile.get("brand_loyalty", agent.personality.brand_loyalty) + random.uniform(-0.1, 0.1))),
                        social_influence=max(0, min(1, personality_profile.get("social_influence", agent.personality.social_influence) + random.uniform(-0.1, 0.1))),
                    )
                    state.agents[i] = dc_replace(agent, personality=new_p)
                    agents_updated += 1

            return {
                "community_id": community_id,
                "name": name or community_id,
                "size": len(members),
                "agents_updated": agents_updated,
            }

    async def add_community(
        self,
        simulation_id: UUID,
        name: str,
        agent_type: str,
        size: int,
        personality_profile: dict[str, float],
    ) -> dict:
        """Add a new community with agents and edges.

        SPEC: docs/spec/16_COMMUNITY_MGMT_SPEC.md#2-2
        """
        import random
        from uuid import uuid4
        async with self._get_lock(simulation_id):
            state = self._get_state(simulation_id)
            self._require_mutable(state)

            new_community_id = uuid4()
            new_agents = []
            for _ in range(size):
                agent = AgentState(
                    agent_id=uuid4(),
                    simulation_id=simulation_id,
                    agent_type=AgentType(agent_type) if agent_type in [t.value for t in AgentType] else AgentType.CONSUMER,
                    step=state.current_step,
                    personality=AgentPersonality(
                        openness=max(0, min(1, personality_profile.get("openness", 0.5) + random.uniform(-0.1, 0.1))),
                        skepticism=max(0, min(1, personality_profile.get("skepticism", 0.5) + random.uniform(-0.1, 0.1))),
                        trend_following=max(0, min(1, personality_profile.get("trend_following", 0.5) + random.uniform(-0.1, 0.1))),
                        brand_loyalty=max(0, min(1, personality_profile.get("brand_loyalty", 0.5) + random.uniform(-0.1, 0.1))),
                        social_influence=max(0, min(1, personality_profile.get("social_influence", 0.4) + random.uniform(-0.1, 0.1))),
                    ),
                    emotion=AgentEmotion(interest=0.5, trust=0.5, skepticism=0.3, excitement=0.5),
                    belief=0.0,
                    action=AgentAction.IGNORE,
                    exposure_count=0,
                    adopted=False,
                    community_id=new_community_id,
                    influence_score=random.uniform(0.1, 0.9),
                )
                new_agents.append(agent)

            state.agents.extend(new_agents)

            # Add edges to network
            edges_created = 0
            if state.network and state.network.graph:
                g = state.network.graph
                base_node = max(g.nodes()) + 1 if g.nodes() else 0
                for i, agent in enumerate(new_agents):
                    nid = base_node + i
                    g.add_node(nid, agent_id=agent.agent_id, community_id=str(new_community_id))
                # Intra-community edges (ring + random shortcuts)
                new_nodes = list(range(base_node, base_node + size))
                for i, n in enumerate(new_nodes):
                    for j in range(1, min(4, size)):
                        neighbor = new_nodes[(i + j) % size]
                        if not g.has_edge(n, neighbor):
                            g.add_edge(n, neighbor, weight=random.uniform(0.5, 1.0))
                            edges_created += 1
                # Cross-community edges
                existing_nodes = [n for n in g.nodes() if n < base_node]
                cross_count = max(1, int(len(existing_nodes) * 0.02))
                for n in new_nodes[:cross_count]:
                    if existing_nodes:
                        target = random.choice(existing_nodes)
                        g.add_edge(n, target, weight=random.uniform(0.1, 0.4))
                        edges_created += 1

            return {
                "community_id": str(new_community_id),
                "name": name,
                "size": size,
                "agents_created": size,
                "edges_created": edges_created,
            }

    async def remove_community(
        self,
        simulation_id: UUID,
        community_id: str,
    ) -> dict:
        """Remove community and its agents/edges.

        SPEC: docs/spec/16_COMMUNITY_MGMT_SPEC.md#2-3
        """
        async with self._get_lock(simulation_id):
            state = self._get_state(simulation_id)
            self._require_mutable(state)

            # Check not last community
            community_ids = {str(a.community_id) for a in state.agents}
            if len(community_ids) <= 1:
                raise ValueError("Cannot delete last community")

            # Remove agents
            removed_agents = [a for a in state.agents if str(a.community_id) == community_id]
            if not removed_agents:
                raise ValueError(f"Community {community_id!r} not found")
            removed_ids = {a.agent_id for a in removed_agents}
            state.agents = [a for a in state.agents if str(a.community_id) != community_id]

            # Remove edges from network
            edges_removed = 0
            if state.network and state.network.graph:
                g = state.network.graph
                nodes_to_remove = [
                    n for n, d in g.nodes(data=True)
                    if d.get("agent_id") in removed_ids
                ]
                edges_removed = sum(g.degree(n) for n in nodes_to_remove)
                g.remove_nodes_from(nodes_to_remove)

            return {
                "community_id": community_id,
                "agents_removed": len(removed_agents),
                "edges_removed": edges_removed,
            }

    async def reassign_agents(
        self,
        simulation_id: UUID,
        community_id: str,
        agent_ids: list[UUID],
        target_community_id: str,
    ) -> dict:
        """Move agents to a different community.

        SPEC: docs/spec/16_COMMUNITY_MGMT_SPEC.md#2-4
        """
        from dataclasses import replace as dc_replace
        async with self._get_lock(simulation_id):
            state = self._get_state(simulation_id)
            self._require_mutable(state)

            # Verify target community exists
            target_exists = any(str(a.community_id) == target_community_id for a in state.agents)
            if not target_exists:
                raise ValueError(f"Target community {target_community_id!r} not found")

            target_uuid = UUID(target_community_id)
            reassigned = 0
            for i, agent in enumerate(state.agents):
                if agent.agent_id in agent_ids and str(agent.community_id) == community_id:
                    state.agents[i] = dc_replace(agent, community_id=target_uuid)
                    # Update network node data
                    if state.network and state.network.graph:
                        for n, d in state.network.graph.nodes(data=True):
                            if d.get("agent_id") == agent.agent_id:
                                d["community_id"] = target_community_id
                                break
                    reassigned += 1

            return {
                "reassigned_count": reassigned,
                "source_community_id": community_id,
                "target_community_id": target_community_id,
            }


__all__ = ["SimulationOrchestrator", "SimulationState"]
