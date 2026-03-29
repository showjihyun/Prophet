"""Tests for G2 (Validation Pipeline) and G3 (vLLM Adapter).

Auto-generated from SPEC: docs/spec/10_VALIDATION_SPEC.md
SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md
SPEC: docs/spec/05_LLM_SPEC.md
"""
import pytest

from app.engine.validation.comparator import CascadeComparator, SimulatedCascade
from app.engine.validation.twitter_dataset import (
    CascadeTree,
    TwitterDatasetLoader,
    ValidationMetrics,
)
from app.llm.vllm_client import VLLMAdapter


# ---------------------------------------------------------------------------
# G2: Validation Pipeline
# ---------------------------------------------------------------------------


@pytest.mark.phase8
class TestCascadeComparator:
    """SPEC: docs/spec/10_VALIDATION_SPEC.md"""

    def test_nrmse_perfect_match(self) -> None:
        """NRMSE should be 0.0 when predicted == actual."""
        assert CascadeComparator.nrmse([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0

    def test_nrmse_with_difference(self) -> None:
        """NRMSE should be between 0 and 1 for close values."""
        result = CascadeComparator.nrmse([1.0, 2.0, 3.0], [2.0, 3.0, 4.0])
        assert 0 < result < 1

    def test_nrmse_empty_lists(self) -> None:
        """NRMSE should be inf for empty lists."""
        assert CascadeComparator.nrmse([], []) == float("inf")

    def test_nrmse_mismatched_lengths(self) -> None:
        """NRMSE should be inf for mismatched lengths."""
        assert CascadeComparator.nrmse([1.0, 2.0], [1.0]) == float("inf")

    def test_nrmse_constant_actual(self) -> None:
        """NRMSE should be inf when actual range is 0 but values differ."""
        assert CascadeComparator.nrmse([2.0, 3.0], [1.0, 1.0]) == float("inf")

    def test_nrmse_constant_both_equal(self) -> None:
        """NRMSE should be 0.0 when both are identical constants."""
        assert CascadeComparator.nrmse([5.0, 5.0], [5.0, 5.0]) == 0.0

    def test_compare_returns_metrics(self) -> None:
        """compare() should return ValidationMetrics with correct fields."""
        comparator = CascadeComparator()
        simulated = [
            SimulatedCascade(cascade_id="s1", scale=10, depth=3, max_breadth=5),
            SimulatedCascade(cascade_id="s2", scale=20, depth=4, max_breadth=8),
        ]
        real = [
            CascadeTree(
                root_id="r1", category="non-rumor", scale=12, depth=3,
                max_breadth=6, timestamps=[0.0], edges=[("a", "b")],
            ),
            CascadeTree(
                root_id="r2", category="false", scale=18, depth=5,
                max_breadth=7, timestamps=[0.0], edges=[("a", "b")],
            ),
        ]
        metrics = comparator.compare(simulated, real)
        assert isinstance(metrics, ValidationMetrics)
        assert metrics.sample_count == 2
        assert metrics.overall_nrmse >= 0
        assert "non-rumor" in metrics.category_breakdown
        assert "false" in metrics.category_breakdown

    def test_compare_empty_lists(self) -> None:
        """compare() with empty inputs should return inf metrics."""
        comparator = CascadeComparator()
        metrics = comparator.compare([], [])
        assert metrics.sample_count == 0
        assert metrics.overall_nrmse == float("inf")


@pytest.mark.phase8
class TestTwitterDatasetLoader:
    """SPEC: docs/spec/10_VALIDATION_SPEC.md"""

    def test_missing_dataset_raises(self) -> None:
        """Loading from nonexistent path should raise FileNotFoundError."""
        loader = TwitterDatasetLoader("/nonexistent")
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_init_default_path(self) -> None:
        """Loader should accept custom data_dir."""
        loader = TwitterDatasetLoader("/tmp/test_data")
        assert loader._data_dir.name == "test_data"


# ---------------------------------------------------------------------------
# G3: vLLM Adapter
# ---------------------------------------------------------------------------


@pytest.mark.phase8
class TestVLLMAdapter:
    """SPEC: docs/spec/05_LLM_SPEC.md#2-llmadapter-interface-abstract"""

    def test_provider_name(self) -> None:
        """VLLMAdapter.provider_name should be 'vllm'."""
        adapter = VLLMAdapter()
        assert adapter.provider_name == "vllm"

    def test_default_config(self) -> None:
        """VLLMAdapter should have sensible defaults."""
        adapter = VLLMAdapter()
        assert adapter._base_url == "http://localhost:8080"
        assert "Llama" in adapter._default_model
        assert adapter._max_concurrent == 64

    def test_custom_config(self) -> None:
        """VLLMAdapter should accept custom configuration."""
        adapter = VLLMAdapter(
            base_url="http://gpu-server:9000",
            default_model="custom-model",
            max_concurrent=128,
        )
        assert adapter._base_url == "http://gpu-server:9000"
        assert adapter._default_model == "custom-model"
        assert adapter._max_concurrent == 128

    @pytest.mark.asyncio
    async def test_health_check_unreachable(self) -> None:
        """health_check() should return False for unreachable server."""
        adapter = VLLMAdapter(base_url="http://localhost:99999")
        assert await adapter.health_check() is False

    @pytest.mark.asyncio
    async def test_embed_unreachable(self) -> None:
        """embed() should return None for unreachable server."""
        adapter = VLLMAdapter(base_url="http://localhost:99999")
        result = await adapter.embed("test text")
        assert result is None
