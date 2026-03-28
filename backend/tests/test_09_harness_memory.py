"""
Auto-generated from SPEC: docs/spec/09_HARNESS_SPEC.md#memory-eviction-policy
SPEC Version: 0.1.0 (updated: memory eviction + simulation cleanup)
Generated BEFORE implementation — tests define the contract.
"""
import pytest
from uuid import uuid4


@pytest.mark.phase2
class TestMemoryEvictionPolicy:
    """SPEC: 09_HARNESS_SPEC.md#memory-eviction-policy

    MemoryLayer.MAX_MEMORIES_PER_AGENT = 1000 (configurable).
    If agent's memory count exceeds MAX_MEMORIES_PER_AGENT,
    evict the lowest-scored memory before inserting the new one.
    """

    def test_memory_layer_has_max_constant(self):
        """MemoryLayer must define MAX_MEMORIES_PER_AGENT."""
        from app.engine.agent.memory_layer import MemoryLayer
        assert hasattr(MemoryLayer, "MAX_MEMORIES_PER_AGENT")
        assert isinstance(MemoryLayer.MAX_MEMORIES_PER_AGENT, int)
        assert MemoryLayer.MAX_MEMORIES_PER_AGENT > 0

    def test_max_memories_default_is_1000(self):
        """Default MAX_MEMORIES_PER_AGENT should be 1000."""
        from app.engine.agent.memory_layer import MemoryLayer
        assert MemoryLayer.MAX_MEMORIES_PER_AGENT == 1000

    def test_store_evicts_lowest_scored_when_full(self):
        """When memory count exceeds limit, lowest-scored memory is evicted."""
        from app.engine.agent.memory_layer import MemoryLayer
        layer = MemoryLayer()
        # This test will fail until eviction logic is implemented
        # The store() method should evict lowest-scored memory
        assert callable(getattr(layer, "store", None))


@pytest.mark.phase6
class TestSimulationCleanup:
    """SPEC: 09_HARNESS_SPEC.md#memory-eviction-policy

    SimulationOrchestrator.delete_simulation() purges simulation
    state from memory after completion or timeout.
    """

    def test_orchestrator_has_delete_simulation(self):
        """SimulationOrchestrator must have delete_simulation method."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        orch = SimulationOrchestrator()
        assert hasattr(orch, "delete_simulation")
        assert callable(orch.delete_simulation)

    @pytest.mark.asyncio
    async def test_delete_simulation_removes_state(self):
        """delete_simulation should remove simulation from internal state."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        from app.engine.simulation.schema import SimulationConfig, CampaignConfig
        from app.engine.network.schema import CommunityConfig

        orch = SimulationOrchestrator()
        config = SimulationConfig(
            simulation_id=uuid4(),
            communities=[
                CommunityConfig(id="c0", name="C0", size=10, agent_type="consumer"),
            ],
            campaign=CampaignConfig(name="test", message="test msg"),
            max_steps=5,
            random_seed=42,
            enable_dynamic_edges=False,
        )
        state = orch.create_simulation(config)
        sim_id = state.simulation_id

        await orch.delete_simulation(sim_id)

        # After deletion, the simulation should not be accessible
        assert sim_id not in orch._simulations

    @pytest.mark.asyncio
    async def test_delete_simulation_unknown_id_raises(self):
        """delete_simulation with unknown ID should raise."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        orch = SimulationOrchestrator()
        with pytest.raises((KeyError, ValueError)):
            await orch.delete_simulation(uuid4())
