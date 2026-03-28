"""
Auto-generated from SPEC: docs/spec/04_SIMULATION_SPEC.md#error-specification
SPEC Version: 0.1.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest
from uuid import uuid4


def _make_sim_config(n_communities=2):
    from app.engine.simulation.schema import SimulationConfig
    from app.engine.network.schema import CommunityConfig
    return SimulationConfig(
        communities=[
            CommunityConfig(id=chr(65 + i), name=f"comm_{i}", size=50,
                            agent_type="consumer")
            for i in range(n_communities)
        ],
    )


class TestSimulationStateTransitions:
    """SPEC: 04_SIMULATION_SPEC.md#error-specification — lifecycle errors"""

    def test_invalid_transition_completed_to_running_raises(self):
        """COMPLETED → RUNNING is invalid state transition."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        from app.engine.simulation.exceptions import InvalidStateTransitionError
        orch = SimulationOrchestrator()
        sim = orch.create_simulation(_make_sim_config())
        # Force to COMPLETED state
        sim.status = "COMPLETED"
        with pytest.raises(InvalidStateTransitionError):
            orch.start(sim.simulation_id)

    def test_invalid_transition_failed_to_running_raises(self):
        """FAILED → RUNNING is invalid state transition."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        from app.engine.simulation.exceptions import InvalidStateTransitionError
        orch = SimulationOrchestrator()
        sim = orch.create_simulation(_make_sim_config())
        sim.status = "FAILED"
        with pytest.raises(InvalidStateTransitionError):
            orch.start(sim.simulation_id)

    @pytest.mark.asyncio
    async def test_modify_agent_while_running_raises(self):
        """modify_agent while RUNNING raises InvalidStateError."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        from app.engine.simulation.exceptions import InvalidStateError
        orch = SimulationOrchestrator()
        sim = orch.create_simulation(_make_sim_config())
        sim.status = "RUNNING"
        with pytest.raises(InvalidStateError):
            await orch.modify_agent(sim.simulation_id, agent_id=uuid4(), belief=0.8)


class TestSimulationInputValidation:
    """SPEC: 04_SIMULATION_SPEC.md#error-specification — input validation"""

    def test_create_empty_community_list_raises(self):
        """create_simulation with empty community list raises ValueError."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        from app.engine.simulation.schema import SimulationConfig
        orch = SimulationOrchestrator()
        config = SimulationConfig(communities=[])
        with pytest.raises(ValueError):
            orch.create_simulation(config)

    def test_inject_unknown_event_type_raises(self):
        """inject_event with unknown event type raises ValueError."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        orch = SimulationOrchestrator()
        sim = orch.create_simulation(_make_sim_config())
        sim.status = "PAUSED"
        with pytest.raises(ValueError):
            orch.inject_event(sim.simulation_id, event_type="UNKNOWN_TYPE", payload={})

    def test_replay_step_beyond_current_raises(self):
        """replay_step target step > current step raises ValueError."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        orch = SimulationOrchestrator()
        sim = orch.create_simulation(_make_sim_config())
        sim.status = "PAUSED"
        sim.current_step = 5
        with pytest.raises(ValueError):
            orch.replay_step(sim.simulation_id, target_step=10)

    def test_replay_step_not_persisted_raises(self):
        """replay_step with non-persisted step raises StepNotFoundError."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        from app.engine.simulation.exceptions import StepNotFoundError
        orch = SimulationOrchestrator()
        sim = orch.create_simulation(_make_sim_config())
        sim.status = "PAUSED"
        sim.current_step = 10
        with pytest.raises(StepNotFoundError):
            orch.replay_step(sim.simulation_id, target_step=3)


class TestSimulationCapacity:
    """SPEC: 04_SIMULATION_SPEC.md#error-specification — concurrency limits"""

    def test_max_concurrent_exceeded_raises(self):
        """Max 3 concurrent simulations → 4th raises SimulationCapacityError."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        from app.engine.simulation.exceptions import SimulationCapacityError
        orch = SimulationOrchestrator()
        # Start 3 simulations
        for _ in range(3):
            sim = orch.create_simulation(_make_sim_config())
            orch.start(sim.simulation_id)
        # 4th should fail
        sim4 = orch.create_simulation(_make_sim_config())
        with pytest.raises(SimulationCapacityError):
            orch.start(sim4.simulation_id)


class TestSimulationRecovery:
    """SPEC: 04_SIMULATION_SPEC.md#error-specification — recovery behavior"""

    @pytest.mark.asyncio
    async def test_step_crash_sets_status_failed(self):
        """Step loop crash → status FAILED, last valid step persisted."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        from unittest.mock import patch, AsyncMock
        orch = SimulationOrchestrator()
        sim = orch.create_simulation(_make_sim_config())
        orch.start(sim.simulation_id)
        with patch.object(
            orch._step_runner, 'execute_step',
            new_callable=AsyncMock,
            side_effect=RuntimeError("crash"),
        ):
            with pytest.raises(RuntimeError):
                await orch.run_step(sim.simulation_id)
        assert sim.status == "failed"

    @pytest.mark.asyncio
    async def test_websocket_disconnect_continues_step(self):
        """WebSocket disconnect during step → step continues, events buffered."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        orch = SimulationOrchestrator()
        sim = orch.create_simulation(_make_sim_config())
        orch.start(sim.simulation_id)
        # Simulate WS disconnect by setting no active connection
        sim.ws_connected = False
        await orch.run_step(sim.simulation_id)
        # Step should complete regardless
        assert sim.current_step >= 1
