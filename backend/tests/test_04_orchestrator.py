"""
Auto-generated from SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
SPEC Version: 0.1.1 (updated: concurrency control + agent_node_map)
Interface tests for SimulationOrchestrator.
"""
import pytest
from uuid import uuid4

from app.engine.network.schema import CommunityConfig
from app.engine.simulation.schema import (
    SimulationConfig,
    CampaignConfig,
    SimulationStatus,
    AgentModification,
)
from app.engine.simulation.orchestrator import SimulationOrchestrator, SimulationState
from app.engine.simulation.exceptions import (
    InvalidStateTransitionError,
    InvalidStateError,
    SimulationCapacityError,
    StepNotFoundError,
)


def _make_config(n_communities=2, size=30, seed=42) -> SimulationConfig:
    return SimulationConfig(
        simulation_id=uuid4(),
        communities=[
            CommunityConfig(id=f"c{i}", name=f"Comm{i}", size=size, agent_type="consumer")
            for i in range(n_communities)
        ],
        campaign=CampaignConfig(name="test", message="test msg"),
        max_steps=10,
        random_seed=seed,
        enable_dynamic_edges=False,
    )


class TestCreateSimulation:
    """SPEC: 04_SIMULATION_SPEC.md#simulationorchestrator-interface — create_simulation"""

    async def test_returns_simulation_state(self):
        """create_simulation returns SimulationState."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        assert isinstance(state, SimulationState)

    async def test_status_is_configured(self):
        """Status should be CONFIGURED after creation."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        assert state.status == SimulationStatus.CONFIGURED.value

    async def test_agents_populated(self):
        """Agents list should match community sizes."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config(n_communities=3, size=20))
        assert len(state.agents) == 60

    async def test_network_populated(self):
        """Network should be generated."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        assert state.network is not None
        assert state.network.graph.number_of_nodes() > 0

    async def test_current_step_is_zero(self):
        """current_step should start at 0."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        assert state.current_step == 0

    async def test_empty_communities_raises(self):
        """Empty community list raises ValueError."""
        orch = SimulationOrchestrator()
        with pytest.raises(ValueError, match="communities"):
            orch.create_simulation(SimulationConfig(communities=[]))

    async def test_agent_ids_unique(self):
        """All agent IDs should be unique."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        ids = [a.agent_id for a in state.agents]
        assert len(ids) == len(set(ids))


class TestStartSimulation:
    """SPEC: 04_SIMULATION_SPEC.md#simulationorchestrator-interface — start"""

    async def test_start_transitions_to_running(self):
        """start() sets status to RUNNING."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.start(state.simulation_id)
        assert state.status == SimulationStatus.RUNNING.value

    async def test_start_completed_raises(self):
        """Starting a COMPLETED simulation raises."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        state.status = SimulationStatus.COMPLETED.value
        with pytest.raises(InvalidStateTransitionError):
            orch.start(state.simulation_id)

    async def test_start_failed_raises(self):
        """Starting a FAILED simulation raises."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        state.status = SimulationStatus.FAILED.value
        with pytest.raises(InvalidStateTransitionError):
            orch.start(state.simulation_id)

    async def test_max_concurrent_raises(self):
        """4th concurrent start raises SimulationCapacityError."""
        orch = SimulationOrchestrator()
        for _ in range(3):
            s = orch.create_simulation(_make_config())
            orch.start(s.simulation_id)
        s4 = orch.create_simulation(_make_config())
        with pytest.raises(SimulationCapacityError):
            orch.start(s4.simulation_id)


class TestRunStep:
    """SPEC: 04_SIMULATION_SPEC.md#simulationorchestrator-interface — run_step"""

    @pytest.mark.asyncio
    async def test_run_step_returns_step_result(self):
        """run_step returns a StepResult."""
        from app.engine.simulation.schema import StepResult
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.start(state.simulation_id)
        result = await orch.run_step(state.simulation_id)
        assert isinstance(result, StepResult)

    @pytest.mark.asyncio
    async def test_run_step_increments_current_step(self):
        """current_step increments after run_step."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.start(state.simulation_id)
        await orch.run_step(state.simulation_id)
        assert state.current_step == 1

    @pytest.mark.asyncio
    async def test_run_step_records_history(self):
        """step_history grows after each step."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.start(state.simulation_id)
        await orch.run_step(state.simulation_id)
        await orch.run_step(state.simulation_id)
        assert len(state.step_history) == 2

    @pytest.mark.asyncio
    async def test_run_step_completes_simulation(self):
        """Simulation completes after max_steps."""
        orch = SimulationOrchestrator()
        config = _make_config()
        config.max_steps = 3
        state = orch.create_simulation(config)
        orch.start(state.simulation_id)
        for _ in range(3):
            await orch.run_step(state.simulation_id)
        assert state.status == SimulationStatus.COMPLETED.value


class TestPauseResume:
    """SPEC: 04_SIMULATION_SPEC.md#simulationorchestrator-interface — pause/resume"""

    @pytest.mark.asyncio
    async def test_pause_sets_paused(self):
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.start(state.simulation_id)
        await orch.run_step(state.simulation_id)
        await orch.pause(state.simulation_id)
        assert state.status == SimulationStatus.PAUSED.value

    @pytest.mark.asyncio
    async def test_resume_sets_running(self):
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.start(state.simulation_id)
        await orch.pause(state.simulation_id)
        await orch.resume(state.simulation_id)
        assert state.status == SimulationStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_pause_non_running_raises(self):
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        with pytest.raises(InvalidStateTransitionError):
            await orch.pause(state.simulation_id)


class TestModifyAgent:
    """SPEC: 04_SIMULATION_SPEC.md#simulationorchestrator-interface — modify_agent"""

    @pytest.mark.asyncio
    async def test_modify_belief(self):
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.start(state.simulation_id)
        await orch.pause(state.simulation_id)
        agent = state.agents[0]
        modified = await orch.modify_agent(state.simulation_id, agent.agent_id, belief=0.9)
        assert modified.belief == 0.9

    @pytest.mark.asyncio
    async def test_modify_while_running_raises(self):
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.start(state.simulation_id)
        with pytest.raises(InvalidStateError):
            await orch.modify_agent(state.simulation_id, uuid4(), belief=0.5)

    @pytest.mark.asyncio
    async def test_modify_with_modifications_object(self):
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.start(state.simulation_id)
        await orch.pause(state.simulation_id)
        agent = state.agents[0]
        mods = AgentModification(belief=0.75)
        modified = await orch.modify_agent(
            state.simulation_id, agent.agent_id, modifications=mods
        )
        assert modified.belief == 0.75

    @pytest.mark.asyncio
    async def test_modify_unknown_agent_raises(self):
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        state.status = SimulationStatus.PAUSED.value
        with pytest.raises(ValueError, match="not found"):
            await orch.modify_agent(state.simulation_id, uuid4(), belief=0.5)


class TestInjectEvent:
    """SPEC: 04_SIMULATION_SPEC.md#simulationorchestrator-interface — inject_event"""

    async def test_inject_valid_event_type(self):
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.inject_event(state.simulation_id, event_type="negative_pr", payload={})
        assert len(state.injected_events) == 1

    async def test_inject_unknown_event_type_raises(self):
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        with pytest.raises(ValueError, match="Unknown event type"):
            orch.inject_event(state.simulation_id, event_type="UNKNOWN", payload={})

    async def test_inject_environment_event(self):
        from app.engine.agent.perception import EnvironmentEvent
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        ev = EnvironmentEvent(
            event_type="campaign_ad",
            content_id=uuid4(),
            message="test",
            source_agent_id=None,
            channel="sns",
            timestamp=0,
        )
        orch.inject_event(state.simulation_id, event=ev)
        assert len(state.injected_events) == 1


class TestReplayStep:
    """SPEC: 04_SIMULATION_SPEC.md#simulationorchestrator-interface — replay_step"""

    @pytest.mark.asyncio
    async def test_replay_existing_step(self):
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.start(state.simulation_id)
        original = await orch.run_step(state.simulation_id)
        replayed = orch.replay_step(state.simulation_id, target_step=0)
        assert replayed["from_step"] == original.step
        assert "replay_id" in replayed

    async def test_replay_beyond_current_raises(self):
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        state.current_step = 5
        with pytest.raises(ValueError):
            orch.replay_step(state.simulation_id, target_step=10)

    async def test_replay_not_persisted_raises(self):
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        state.current_step = 10
        with pytest.raises(StepNotFoundError):
            orch.replay_step(state.simulation_id, target_step=3)


class TestConcurrencyControl:
    """SPEC: 04_SIMULATION_SPEC.md — Concurrency Control (engineering review addition).

    Each simulation has a dedicated asyncio.Lock. The lock is acquired
    for run_step(), pause(), resume(), and modify_agent().
    """

    def test_orchestrator_has_locks_dict(self):
        """Orchestrator must maintain a _locks dict[UUID, asyncio.Lock]."""
        orch = SimulationOrchestrator()
        assert hasattr(orch, "_locks")
        assert isinstance(orch._locks, dict)

    async def test_lock_created_on_simulation_create(self):
        """A lock should be created when a simulation is created."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        assert state.simulation_id in orch._locks

    @pytest.mark.asyncio
    async def test_run_step_acquires_lock(self):
        """run_step should acquire the simulation lock (non-reentrant check)."""
        import asyncio

        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.start(state.simulation_id)

        lock = orch._locks[state.simulation_id]
        # Lock should not be held before run_step
        assert not lock.locked()
        await orch.run_step(state.simulation_id)
        # Lock should be released after run_step completes
        assert not lock.locked()


class TestAgentNodeMap:
    """SPEC: 04_SIMULATION_SPEC.md — agent_node_map optimization.

    All engine calls receive an agent_node_map: dict[UUID, int] mapping
    agent UUIDs to NetworkX integer node IDs, built once per step.
    """

    @pytest.mark.asyncio
    async def test_step_result_contains_valid_data(self):
        """run_step should successfully complete with the agent_node_map optimization.
        This validates the map is built and used without errors."""
        from app.engine.simulation.schema import StepResult

        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        orch.start(state.simulation_id)
        result = await orch.run_step(state.simulation_id)
        assert isinstance(result, StepResult)
        # All agents should have been processed
        total_actions = sum(result.action_distribution.values())
        assert total_actions == len(state.agents)
