"""Tests for pgvector-backed Memory Persistence (KG-1 / SPEC 21 §3 MP-01~04).

Auto-generated from SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md
SPEC Version: 0.1.0
Generated BEFORE implementation — tests define the contract.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from app.engine.agent.memory import MemoryLayer, MemoryRecord, MemoryConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def agent_id() -> UUID:
    return uuid4()


@pytest.fixture
def simulation_id() -> UUID:
    return uuid4()


def _make_embedding(dim: int = 768, seed: float = 0.1) -> list[float]:
    """Generate a deterministic fake embedding."""
    import math
    return [math.sin(seed * (i + 1)) for i in range(dim)]


def _mock_llm_adapter() -> AsyncMock:
    """Create a mock LLM adapter with embed() that returns 768-dim vectors."""
    adapter = AsyncMock()
    adapter.embed = AsyncMock(return_value=_make_embedding(768, 0.5))
    return adapter


# ---------------------------------------------------------------------------
# MP-AC-01: store() in memory mode works identically to current behavior
# ---------------------------------------------------------------------------

class TestMemoryModeBackwardCompat:
    """SPEC: 21_SIMULATION_QUALITY_SPEC.md#§3 MP-AC-01"""

    def test_store_without_session_factory(self, agent_id):
        """store() in memory-only mode works identically to Phase 2 behavior."""
        layer = MemoryLayer()
        record = layer.store(agent_id, "episodic", "test memory", 0.7, step=5)
        assert record.content == "test memory"
        assert record.agent_id == agent_id
        assert record.memory_type == "episodic"

    def test_retrieve_without_session_factory(self, agent_id):
        """retrieve() in memory-only mode returns from in-memory store."""
        layer = MemoryLayer()
        layer.store(agent_id, "episodic", "mem1", 0.5, step=1)
        layer.store(agent_id, "episodic", "mem2", 0.8, step=2)
        results = layer.retrieve(agent_id, "test", top_k=10, current_step=3)
        assert len(results) == 2

    def test_fallback_weights_used_without_session(self):
        """Without session_factory, fallback weights are used."""
        layer = MemoryLayer()
        # Fallback: beta effectively contributes 0 (no pgvector)
        assert layer._beta >= 0.0


# ---------------------------------------------------------------------------
# MP-AC-02: store_async() in db mode creates database record
# ---------------------------------------------------------------------------

class TestStoreAsync:
    """SPEC: 21_SIMULATION_QUALITY_SPEC.md#§3 MP-AC-02"""

    @pytest.mark.asyncio
    async def test_store_async_persists_to_db(self, agent_id, simulation_id):
        """store_async() writes to both in-memory and DB when session_factory available."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_factory = MagicMock(return_value=mock_session)

        layer = MemoryLayer(
            session_factory=mock_factory,
            simulation_id=simulation_id,
        )
        record = await layer.store_async(
            agent_id, "episodic", "test async store", 0.7,
            embedding=_make_embedding(), step=3,
        )

        # In-memory store should have the record
        assert len(layer._store[agent_id]) == 1
        assert record.content == "test async store"

        # DB write should have been attempted
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_async_graceful_on_db_failure(self, agent_id, simulation_id):
        """store_async() still stores in-memory even if DB write fails."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(side_effect=Exception("DB down"))
        mock_session.rollback = AsyncMock()

        mock_factory = MagicMock(return_value=mock_session)

        layer = MemoryLayer(
            session_factory=mock_factory,
            simulation_id=simulation_id,
        )
        record = await layer.store_async(
            agent_id, "episodic", "still stored", 0.5, step=1,
        )
        # In-memory should still work
        assert record.content == "still stored"
        assert len(layer._store[agent_id]) == 1


# ---------------------------------------------------------------------------
# MP-AC-03: retrieve_async() in db mode returns records from database
# ---------------------------------------------------------------------------

class TestRetrieveAsyncPgvector:
    """SPEC: 21_SIMULATION_QUALITY_SPEC.md#§3 MP-AC-03"""

    @pytest.mark.asyncio
    async def test_retrieve_async_uses_pgvector(self, agent_id, simulation_id):
        """retrieve_async() with session_factory uses pgvector cosine search."""
        # Mock DB returning rows with cosine similarity
        mock_row = MagicMock()
        mock_row.memory_id = uuid4()
        mock_row.agent_id = agent_id
        mock_row.memory_type = "episodic"
        mock_row.content = "DB memory"
        mock_row.step = 2
        mock_row.emotion_weight = 0.6
        mock_row.social_weight = 0.3
        mock_row.cosine_sim = 0.85

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_factory = MagicMock(return_value=mock_session)

        adapter = _mock_llm_adapter()
        layer = MemoryLayer(
            llm_adapter=adapter,
            session_factory=mock_factory,
            simulation_id=simulation_id,
        )

        results = await layer.retrieve_async(
            agent_id, "query context", top_k=5,
            current_step=5, query_text="test query",
        )

        # Should have returned the DB memory
        assert len(results) >= 1
        assert any(r.content == "DB memory" for r in results)

    @pytest.mark.asyncio
    async def test_retrieve_async_fallback_on_db_error(self, agent_id, simulation_id):
        """retrieve_async() falls back to in-memory if pgvector query fails."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(side_effect=Exception("pgvector error"))

        mock_factory = MagicMock(return_value=mock_session)

        adapter = _mock_llm_adapter()
        layer = MemoryLayer(
            llm_adapter=adapter,
            session_factory=mock_factory,
            simulation_id=simulation_id,
        )
        # Store something in-memory first
        layer.store(agent_id, "episodic", "in-memory only", 0.5, step=1)

        results = await layer.retrieve_async(
            agent_id, "query", top_k=5,
            current_step=3, query_text="test",
        )
        # Should fall back to in-memory
        assert len(results) == 1
        assert results[0].content == "in-memory only"


# ---------------------------------------------------------------------------
# MP-AC-04: Cold start — retrieve() loads from DB when _store is empty
# ---------------------------------------------------------------------------

class TestColdStartRetrieval:
    """SPEC: 21_SIMULATION_QUALITY_SPEC.md#§3 MP-AC-04"""

    @pytest.mark.asyncio
    async def test_cold_start_retrieves_from_db(self, agent_id, simulation_id):
        """On cold start (empty _store), pgvector retrieval returns DB records."""
        mock_row = MagicMock()
        mock_row.memory_id = uuid4()
        mock_row.agent_id = agent_id
        mock_row.memory_type = "episodic"
        mock_row.content = "persisted memory from previous session"
        mock_row.step = 10
        mock_row.emotion_weight = 0.7
        mock_row.social_weight = 0.2
        mock_row.cosine_sim = 0.9

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_factory = MagicMock(return_value=mock_session)

        adapter = _mock_llm_adapter()
        layer = MemoryLayer(
            llm_adapter=adapter,
            session_factory=mock_factory,
            simulation_id=simulation_id,
        )

        # _store is empty (cold start)
        assert len(layer._store) == 0

        results = await layer.retrieve_async(
            agent_id, "context", top_k=5,
            current_step=15, query_text="query text",
        )
        assert len(results) == 1
        assert results[0].content == "persisted memory from previous session"


# ---------------------------------------------------------------------------
# Weight validation
# ---------------------------------------------------------------------------

class TestWeightValidation:
    """Ensure scoring weights are valid."""

    def test_full_weights_sum_to_one(self):
        """With pgvector enabled, alpha+beta+gamma+delta == 1.0."""
        layer = MemoryLayer(
            session_factory=MagicMock(),
            simulation_id=uuid4(),
        )
        total = layer._alpha + layer._beta + layer._gamma + layer._delta
        assert abs(total - 1.0) < 0.01

    def test_fallback_weights_effective_sum(self):
        """Without pgvector, beta is effectively 0 (no cosine available)."""
        layer = MemoryLayer()
        # beta contributes 0 to scoring since relevance_score is always 0.0
        effective = layer._alpha + layer._gamma + layer._delta
        # Should be close to 1.0 for meaningful scoring
        assert effective > 0.5


# ---------------------------------------------------------------------------
# Composite scoring with cosine similarity
# ---------------------------------------------------------------------------

class TestCompositeScoring:
    """Verify that beta (cosine) actually affects retrieval ranking."""

    @pytest.mark.asyncio
    async def test_cosine_similarity_affects_ranking(self, agent_id, simulation_id):
        """Memories with higher cosine similarity to query should rank higher."""
        import math

        # Two DB rows: one with high cosine sim, one with low
        high_sim_row = MagicMock()
        high_sim_row.memory_id = uuid4()
        high_sim_row.agent_id = agent_id
        high_sim_row.memory_type = "episodic"
        high_sim_row.content = "highly relevant memory"
        high_sim_row.step = 1
        high_sim_row.emotion_weight = 0.3
        high_sim_row.social_weight = 0.1
        high_sim_row.cosine_sim = 0.95

        low_sim_row = MagicMock()
        low_sim_row.memory_id = uuid4()
        low_sim_row.agent_id = agent_id
        low_sim_row.memory_type = "episodic"
        low_sim_row.content = "irrelevant memory"
        low_sim_row.step = 1
        low_sim_row.emotion_weight = 0.3
        low_sim_row.social_weight = 0.1
        low_sim_row.cosine_sim = 0.1

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [low_sim_row, high_sim_row]

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_factory = MagicMock(return_value=mock_session)

        adapter = _mock_llm_adapter()
        layer = MemoryLayer(
            llm_adapter=adapter,
            session_factory=mock_factory,
            simulation_id=simulation_id,
        )

        results = await layer.retrieve_async(
            agent_id, "context", top_k=2,
            current_step=5, query_text="relevant query",
        )

        assert len(results) == 2
        # Highly relevant memory should rank first (higher cosine → higher score)
        assert results[0].content == "highly relevant memory"
        assert results[1].content == "irrelevant memory"
