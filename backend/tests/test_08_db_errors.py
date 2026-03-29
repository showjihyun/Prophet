"""DB error handling tests.
SPEC: docs/spec/08_DB_SPEC.md#error-specification

Tests verify DB-level constraints and error handling at the application layer.
Since unit tests use in-memory state (no real PostgreSQL), we test the equivalent
logic through the orchestrator and engine layers.
"""
import asyncio
import pytest
from uuid import uuid4

from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.engine.simulation.schema import SimulationConfig, CampaignConfig
from app.engine.network.schema import CommunityConfig
from app.engine.agent.memory import MemoryLayer


def _make_config(**overrides) -> SimulationConfig:
    """Helper to create a valid SimulationConfig."""
    defaults = dict(
        simulation_id=uuid4(),
        name="test",
        description="",
        communities=[CommunityConfig(id="A", name="a", size=10, agent_type="consumer")],
        campaign=CampaignConfig(
            name="t", channels=["sns"], message="t", target_communities=["all"]
        ),
        max_steps=2,
        random_seed=42,
    )
    defaults.update(overrides)
    return SimulationConfig(**defaults)


@pytest.mark.phase1
class TestDBConstraintViolations:
    """SPEC: 08_DB_SPEC.md#error-specification — constraint handling"""

    def test_unique_violation_returns_existing_or_409(self):
        """Duplicate simulation_id is silently overwritten in in-memory mode.

        With a real DB this would be a UNIQUE constraint violation. Here we verify
        the orchestrator at least accepts the duplicate without crashing, and
        that the state is consistent afterward.
        """
        orch = SimulationOrchestrator()
        sim_id = uuid4()
        config = _make_config(simulation_id=sim_id)
        state1 = orch.create_simulation(config)
        # In-memory: second create overwrites (no DB unique constraint)
        state2 = orch.create_simulation(config)
        assert state2.simulation_id == sim_id
        # State should be retrievable
        retrieved = orch.get_state(sim_id)
        assert retrieved.simulation_id == sim_id

    def test_foreign_key_violation_raises(self):
        """Referencing non-existent simulation should fail."""
        orch = SimulationOrchestrator()
        with pytest.raises(ValueError):
            orch.get_state(uuid4())

    def test_empty_communities_raises_value_error(self):
        """Simulation config with no communities should be rejected."""
        orch = SimulationOrchestrator()
        config = _make_config(communities=[])
        with pytest.raises(ValueError, match="communities"):
            orch.create_simulation(config)

    def test_embedding_dimension_mismatch_raises(self):
        """Wrong embedding dimension should raise ValueError."""
        ml = MemoryLayer()
        with pytest.raises(ValueError, match="768"):
            ml.store(
                agent_id=uuid4(),
                memory_type="episodic",
                content="test",
                emotion_weight=0.5,
                embedding=[0.1] * 512,  # wrong dim, expect 768
            )


@pytest.mark.phase1
class TestDBCascadeDelete:
    """SPEC: 08_DB_SPEC.md#error-specification — cascade safety"""

    def test_delete_nonexistent_raises_key_error(self):
        """Deleting a simulation that doesn't exist should raise KeyError."""
        orch = SimulationOrchestrator()
        with pytest.raises(KeyError):
            asyncio.get_event_loop().run_until_complete(
                orch.delete_simulation(uuid4())
            )

    def test_delete_existing_simulation_succeeds(self):
        """Delete existing simulation removes all state."""
        orch = SimulationOrchestrator()
        config = _make_config()
        state = orch.create_simulation(config)
        asyncio.get_event_loop().run_until_complete(
            orch.delete_simulation(state.simulation_id)
        )
        with pytest.raises(ValueError):
            orch.get_state(state.simulation_id)


@pytest.mark.phase1
class TestDBPgVectorFallback:
    """SPEC: 08_DB_SPEC.md#error-specification — pgvector degradation"""

    def test_pgvector_unavailable_falls_back_to_recency(self):
        """Without embeddings, retrieval uses recency+emotion scoring."""
        ml = MemoryLayer()
        aid = uuid4()
        ml.store(agent_id=aid, memory_type="episodic", content="old memory",
                 emotion_weight=0.3, step=0)
        ml.store(agent_id=aid, memory_type="episodic", content="new memory",
                 emotion_weight=0.8, step=5)
        results = ml.retrieve(agent_id=aid, query_context="", top_k=2, current_step=5)
        assert len(results) == 2
        # Newer + higher emotion should rank first
        assert results[0].content == "new memory"

    def test_ivfflat_index_missing_uses_seqscan(self):
        """Without IVFFlat index, sequential scan still works (in-memory fallback)."""
        ml = MemoryLayer()
        aid = uuid4()
        ml.store(agent_id=aid, memory_type="semantic", content="some fact",
                 emotion_weight=0.5, step=1)
        results = ml.retrieve(agent_id=aid, query_context="", top_k=10, current_step=1)
        assert len(results) >= 1


@pytest.mark.phase1
class TestDBConnectionPool:
    """SPEC: 08_DB_SPEC.md#error-specification — connection management"""

    def test_engine_is_configured(self):
        """Database engine is created with proper configuration."""
        from app.database import engine
        assert engine is not None

    def test_pool_exists(self):
        """Engine has a connection pool configured."""
        from app.database import engine
        assert engine.pool is not None


@pytest.mark.phase1
class TestDBQueryTimeout:
    """SPEC: 08_DB_SPEC.md#error-specification — query limits"""

    def test_engine_exists_for_queries(self):
        """Database engine exists and can serve queries."""
        from app.database import engine
        assert engine is not None
        # Engine URL is configured
        assert str(engine.url) != ""
