"""
Auto-generated from SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer
SPEC Version: 0.2.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest
from uuid import uuid4


@pytest.mark.phase2
class TestMemoryLayerRetrieve:
    """SPEC: 01_AGENT_SPEC.md#layer-2-memorylayer — retrieve()"""

    def test_returns_top_k_sorted_by_score(self):
        """AGT-06: len(result) <= top_k, sorted by score DESC."""
        from app.engine.agent.memory import MemoryLayer
        layer = MemoryLayer()
        agent_id = uuid4()
        # Store 20 memories first
        for i in range(20):
            layer.store(agent_id, "episodic", f"memory {i}", emotion_weight=i / 20.0, step=i)
        result = layer.retrieve(agent_id, "test query", top_k=10, current_step=20)
        assert len(result) <= 10
        scores = [m.relevance_score for m in result]
        assert scores == sorted(scores, reverse=True)

    def test_empty_memories_returns_empty(self):
        """Agent with no memories returns empty list."""
        from app.engine.agent.memory import MemoryLayer
        layer = MemoryLayer()
        result = layer.retrieve(uuid4(), "query", top_k=10, current_step=0)
        assert result == []

    def test_top_k_zero_raises(self):
        """top_k <= 0 raises ValueError."""
        from app.engine.agent.memory import MemoryLayer
        layer = MemoryLayer()
        with pytest.raises(ValueError):
            layer.retrieve(uuid4(), "query", top_k=0)

    def test_empty_query_context_uses_recency_only(self):
        """Empty query_context -> relevance_score=0.0 for all, recency dominates."""
        from app.engine.agent.memory import MemoryLayer
        layer = MemoryLayer()
        agent_id = uuid4()
        layer.store(agent_id, "episodic", "old memory", emotion_weight=0.9, step=0)
        layer.store(agent_id, "episodic", "new memory", emotion_weight=0.1, step=10)
        result = layer.retrieve(agent_id, "", top_k=10, current_step=10)
        # With empty query, recency should dominate -> newer memory first
        assert len(result) == 2
        assert result[0].content == "new memory"


@pytest.mark.phase2
class TestMemoryLayerStore:
    """SPEC: 01_AGENT_SPEC.md#layer-2-memorylayer — store()"""

    def test_store_returns_memory_record(self):
        from app.engine.agent.memory import MemoryLayer
        layer = MemoryLayer()
        agent_id = uuid4()
        record = layer.store(agent_id, "episodic", "test content", emotion_weight=0.5, step=1)
        assert record.agent_id == agent_id
        assert record.memory_type == "episodic"
        assert record.content == "test content"
        assert record.emotion_weight == 0.5
        assert record.relevance_score is None  # None on store

    def test_empty_content_raises(self):
        """Empty content raises ValueError."""
        from app.engine.agent.memory import MemoryLayer
        layer = MemoryLayer()
        with pytest.raises(ValueError):
            layer.store(uuid4(), "episodic", "", emotion_weight=0.5)

    def test_wrong_embedding_dimension_raises(self):
        """Embedding length != 768 raises ValueError."""
        from app.engine.agent.memory import MemoryLayer
        layer = MemoryLayer()
        with pytest.raises(ValueError):
            layer.store(uuid4(), "episodic", "content", emotion_weight=0.5,
                        embedding=[0.1] * 100)  # wrong dim

    def test_valid_embedding_accepted(self):
        """768-dim embedding is accepted."""
        from app.engine.agent.memory import MemoryLayer
        layer = MemoryLayer()
        record = layer.store(uuid4(), "episodic", "content", emotion_weight=0.5,
                             embedding=[0.1] * 768)
        assert record.embedding is not None
        assert len(record.embedding) == 768

    def test_emotion_weight_clamped(self):
        """Out-of-range emotion_weight is clamped to [0.0, 1.0]."""
        from app.engine.agent.memory import MemoryLayer
        layer = MemoryLayer()
        record = layer.store(uuid4(), "episodic", "content", emotion_weight=1.5)
        assert record.emotion_weight == 1.0
