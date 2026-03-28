"""
Auto-generated from SPEC: docs/spec/08_DB_SPEC.md#error-specification
SPEC Version: 0.1.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest
from uuid import uuid4


class TestDBConstraintViolations:
    """SPEC: 08_DB_SPEC.md#error-specification — constraint handling"""

    def test_unique_violation_returns_existing_or_409(self):
        """UNIQUE constraint violation → idempotent upsert or 409 error."""
        from app.db.repository import SimulationRepository
        repo = SimulationRepository()
        sim_id = uuid4()
        # First insert succeeds
        repo.create_simulation(simulation_id=sim_id, name="test1", config={})
        # Second insert with same ID → should return existing or raise 409
        result = repo.create_simulation(simulation_id=sim_id, name="test1", config={})
        assert result.simulation_id == sim_id  # idempotent

    def test_foreign_key_violation_raises(self):
        """Foreign key violation → IntegrityError with descriptive message."""
        from app.db.repository import AgentStateRepository
        from sqlalchemy.exc import IntegrityError
        repo = AgentStateRepository()
        with pytest.raises(IntegrityError):
            repo.insert_agent_state(
                agent_id=uuid4(),
                simulation_id=uuid4(),  # non-existent simulation
                step=1,
                state={},
            )

    def test_agent_state_null_community_id_raises(self):
        """agent_states INSERT with NULL community_id → IntegrityError."""
        from app.db.repository import AgentStateRepository
        from sqlalchemy.exc import IntegrityError
        repo = AgentStateRepository()
        with pytest.raises(IntegrityError):
            repo.insert_agent_state(
                agent_id=uuid4(),
                simulation_id=uuid4(),
                step=1,
                state={"community_id": None},
            )

    def test_embedding_dimension_mismatch_raises(self):
        """Embedding with wrong dimension → ValueError."""
        from app.db.repository import MemoryRepository
        repo = MemoryRepository()
        with pytest.raises(ValueError):
            repo.store_memory(
                agent_id=uuid4(),
                simulation_id=uuid4(),
                content="test",
                embedding=[0.1] * 512,  # expect 768
            )


class TestDBCascadeDelete:
    """SPEC: 08_DB_SPEC.md#error-specification — cascade safety"""

    def test_cascade_delete_without_force_rejected(self):
        """CASCADE DELETE >10K rows without force=True is rejected."""
        from app.db.repository import SimulationRepository
        repo = SimulationRepository()
        sim_id = uuid4()
        # Mock a simulation with many child records
        repo.create_simulation(simulation_id=sim_id, name="large_sim", config={})
        # Attempting delete without force should raise when child count > 10K
        with pytest.raises(ValueError, match="force"):
            repo.delete_simulation(simulation_id=sim_id, force=False,
                                   estimated_children=15000)

    def test_cascade_delete_with_force_succeeds(self):
        """CASCADE DELETE with force=True proceeds regardless of count."""
        from app.db.repository import SimulationRepository
        repo = SimulationRepository()
        sim_id = uuid4()
        repo.create_simulation(simulation_id=sim_id, name="large_sim", config={})
        repo.delete_simulation(simulation_id=sim_id, force=True,
                               estimated_children=15000)


class TestDBPgVectorFallback:
    """SPEC: 08_DB_SPEC.md#error-specification — pgvector degradation"""

    def test_pgvector_unavailable_falls_back_to_recency(self):
        """pgvector extension missing → fallback to recency-only retrieval."""
        from app.db.repository import MemoryRepository
        from unittest.mock import patch
        repo = MemoryRepository()
        with patch.object(repo, '_pgvector_available', return_value=False):
            results = repo.retrieve_similar(
                agent_id=uuid4(), simulation_id=uuid4(),
                query_embedding=[0.1] * 768, top_k=5,
            )
        # Should return results ordered by recency, not cosine similarity
        assert all(hasattr(r, 'created_at') for r in results)

    def test_ivfflat_index_missing_uses_seqscan(self):
        """IVFFlat index not built → sequential scan (slower, still works)."""
        from app.db.repository import MemoryRepository
        from unittest.mock import patch
        repo = MemoryRepository()
        with patch.object(repo, '_ivfflat_index_exists', return_value=False):
            results = repo.retrieve_similar(
                agent_id=uuid4(), simulation_id=uuid4(),
                query_embedding=[0.1] * 768, top_k=5,
            )
        # Should still return results (via sequential scan)
        assert isinstance(results, list)


class TestDBConnectionPool:
    """SPEC: 08_DB_SPEC.md#error-specification — connection management"""

    def test_pool_exhausted_raises_after_timeout(self):
        """Connection pool exhausted → queue 5s → 503 error."""
        from app.db.pool import ConnectionPool
        from app.db.exceptions import ConnectionPoolExhaustedError
        pool = ConnectionPool(max_size=1, timeout=0.1)  # tiny pool, short timeout
        # Acquire the only connection
        conn1 = pool.acquire()
        # Second acquire should timeout and raise
        with pytest.raises(ConnectionPoolExhaustedError):
            pool.acquire()
        pool.release(conn1)

    def test_deadlock_retries_automatically(self):
        """Concurrent write deadlock → auto-retry (max 3)."""
        from app.db.repository import AgentStateRepository
        from unittest.mock import patch, MagicMock
        from sqlalchemy.exc import OperationalError
        repo = AgentStateRepository()
        # First 2 calls: deadlock, 3rd: success
        mock_session = MagicMock()
        mock_session.execute = MagicMock(
            side_effect=[
                OperationalError("deadlock", {}, None),
                OperationalError("deadlock", {}, None),
                MagicMock(),  # success
            ]
        )
        with patch.object(repo, '_get_session', return_value=mock_session):
            repo.insert_agent_state(
                agent_id=uuid4(), simulation_id=uuid4(), step=1, state={},
            )
        assert mock_session.execute.call_count == 3


class TestDBQueryTimeout:
    """SPEC: 08_DB_SPEC.md#error-specification — query limits"""

    def test_slow_query_cancelled_after_timeout(self):
        """Query exceeding 10s → cancel and return 504."""
        from app.db.repository import BaseRepository
        from unittest.mock import patch, MagicMock
        repo = BaseRepository()
        mock_session = MagicMock()
        mock_session.execute = MagicMock(side_effect=TimeoutError("query timeout"))
        with patch.object(repo, '_get_session', return_value=mock_session):
            with pytest.raises(TimeoutError):
                repo.execute_with_timeout("SELECT * FROM agent_states", timeout=10)
