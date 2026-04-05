"""F30 Hybrid Execution Mode — per-step LLM provider routing.
Auto-generated from SPEC: docs/spec/09_HARNESS_SPEC.md#13-f30
SPEC Version: 0.1.0
Generated BEFORE implementation — tests define the contract.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Imports smoke test
# ---------------------------------------------------------------------------


@pytest.mark.phase3
@pytest.mark.unit
class TestHybridExecImports:
    """SPEC: 09_HARNESS_SPEC.md#13-f30 — importability"""

    def test_import_hybrid_schedule(self):
        from harness.hybrid_exec import HybridSchedule  # noqa: F401

    def test_import_hybrid_step_result(self):
        from harness.hybrid_exec import HybridStepResult  # noqa: F401

    def test_import_hybrid_exec_router(self):
        from harness.hybrid_exec import HybridExecRouter  # noqa: F401


# ---------------------------------------------------------------------------
# HybridSchedule dataclass contracts
# ---------------------------------------------------------------------------


@pytest.mark.phase3
@pytest.mark.unit
class TestHybridSchedule:
    """SPEC: 09_HARNESS_SPEC.md#13-f30 — HybridSchedule defaults"""

    def test_default_provider_is_ollama(self):
        from harness.hybrid_exec import HybridSchedule

        schedule = HybridSchedule()
        assert schedule.default_provider == "ollama"

    def test_step_provider_map_default_empty(self):
        from harness.hybrid_exec import HybridSchedule

        schedule = HybridSchedule()
        assert schedule.step_provider_map == {}

    def test_dynamic_selector_default_none(self):
        from harness.hybrid_exec import HybridSchedule

        schedule = HybridSchedule()
        assert schedule.dynamic_selector is None

    def test_custom_step_provider_map(self):
        from harness.hybrid_exec import HybridSchedule

        schedule = HybridSchedule(
            step_provider_map={1: "claude", 5: "openai"},
            default_provider="mock",
        )
        assert schedule.step_provider_map[1] == "claude"
        assert schedule.step_provider_map[5] == "openai"
        assert schedule.default_provider == "mock"

    def test_dynamic_selector_is_callable(self):
        from harness.hybrid_exec import HybridSchedule

        selector = lambda step, count: "claude" if step > 5 else "ollama"
        schedule = HybridSchedule(dynamic_selector=selector)
        assert callable(schedule.dynamic_selector)


# ---------------------------------------------------------------------------
# HybridExecRouter — select_provider (F30-01, F30-02, F30-03)
# ---------------------------------------------------------------------------


@pytest.mark.phase3
@pytest.mark.unit
class TestSelectProvider:
    """SPEC: 09_HARNESS_SPEC.md#13-f30 — select_provider routing priority"""

    def test_f30_01_step_provider_map_used(self):
        """F30-01: select_provider returns correct provider from step_provider_map."""
        from harness.hybrid_exec import HybridExecRouter, HybridSchedule

        schedule = HybridSchedule(
            step_provider_map={1: "claude", 2: "openai", 3: "gemini"},
            default_provider="ollama",
        )
        router = HybridExecRouter(schedule)

        assert router.select_provider(1) == "claude"
        assert router.select_provider(2) == "openai"
        assert router.select_provider(3) == "gemini"

    def test_f30_03_default_provider_for_unmapped_step(self):
        """F30-03: default_provider used when step has no mapping."""
        from harness.hybrid_exec import HybridExecRouter, HybridSchedule

        schedule = HybridSchedule(
            step_provider_map={1: "claude"},
            default_provider="mock",
        )
        router = HybridExecRouter(schedule)

        assert router.select_provider(99) == "mock"

    def test_f30_02_dynamic_selector_overrides_map(self):
        """F30-02: dynamic_selector takes precedence over step_provider_map."""
        from harness.hybrid_exec import HybridExecRouter, HybridSchedule

        schedule = HybridSchedule(
            step_provider_map={1: "claude"},
            default_provider="ollama",
            dynamic_selector=lambda step, count: "gemini",
        )
        router = HybridExecRouter(schedule)

        # dynamic_selector always returns "gemini", overriding map's "claude"
        assert router.select_provider(1) == "gemini"

    def test_dynamic_selector_receives_agent_count(self):
        """dynamic_selector receives both step and agent_count."""
        from harness.hybrid_exec import HybridExecRouter, HybridSchedule

        calls = []

        def selector(step: int, agent_count: int) -> str:
            calls.append((step, agent_count))
            return "openai" if agent_count > 500 else "ollama"

        schedule = HybridSchedule(dynamic_selector=selector)
        router = HybridExecRouter(schedule)

        assert router.select_provider(1, agent_count=100) == "ollama"
        assert router.select_provider(2, agent_count=1000) == "openai"
        assert calls == [(1, 100), (2, 1000)]


# ---------------------------------------------------------------------------
# HybridExecRouter — execute_step (F30-04)
# ---------------------------------------------------------------------------


@pytest.mark.phase3
@pytest.mark.unit
class TestExecuteStep:
    """SPEC: 09_HARNESS_SPEC.md#13-f30 — execute_step with fallback"""

    @pytest.mark.asyncio
    async def test_execute_step_uses_selected_provider(self):
        """execute_step routes to the correct provider."""
        from harness.hybrid_exec import HybridExecRouter, HybridSchedule

        schedule = HybridSchedule(
            step_provider_map={1: "mock"},
            default_provider="ollama",
        )
        router = HybridExecRouter(schedule)

        # Mock registry with healthy "mock" adapter
        registry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.health_check = AsyncMock(return_value=True)
        registry.get.return_value = mock_adapter

        result = await router.execute_step(step=1, agent_count=10, registry=registry)
        assert result.step == 1
        assert result.provider_used == "mock"
        assert result.was_fallback is False

    @pytest.mark.asyncio
    async def test_f30_04_fallback_on_unhealthy_provider(self):
        """F30-04: Unhealthy provider triggers fallback with was_fallback=True."""
        from harness.hybrid_exec import HybridExecRouter, HybridSchedule

        schedule = HybridSchedule(
            step_provider_map={1: "claude"},
            default_provider="mock",
        )
        router = HybridExecRouter(schedule)

        # Mock registry: "claude" unhealthy, "mock" healthy
        def mock_get(name):
            adapter = MagicMock()
            if name == "claude":
                adapter.health_check = AsyncMock(return_value=False)
            else:
                adapter.health_check = AsyncMock(return_value=True)
            return adapter

        registry = MagicMock()
        registry.get.side_effect = mock_get

        result = await router.execute_step(step=1, agent_count=10, registry=registry)
        assert result.provider_used == "mock"  # fell back
        assert result.was_fallback is True
        assert result.fallback_reason is not None

    @pytest.mark.asyncio
    async def test_execute_step_default_when_no_mapping(self):
        """execute_step uses default_provider for unmapped steps."""
        from harness.hybrid_exec import HybridExecRouter, HybridSchedule

        schedule = HybridSchedule(default_provider="mock")
        router = HybridExecRouter(schedule)

        registry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.health_check = AsyncMock(return_value=True)
        registry.get.return_value = mock_adapter

        result = await router.execute_step(step=99, agent_count=5, registry=registry)
        assert result.provider_used == "mock"
        assert result.was_fallback is False


# ---------------------------------------------------------------------------
# execution_log (F30-05)
# ---------------------------------------------------------------------------


@pytest.mark.phase3
@pytest.mark.unit
class TestExecutionLog:
    """SPEC: 09_HARNESS_SPEC.md#13-f30 — execution_log records steps"""

    @pytest.mark.asyncio
    async def test_f30_05_log_records_every_step(self):
        """F30-05: execution_log records every step in order."""
        from harness.hybrid_exec import HybridExecRouter, HybridSchedule

        schedule = HybridSchedule(
            step_provider_map={1: "mock", 2: "mock", 3: "mock"},
            default_provider="mock",
        )
        router = HybridExecRouter(schedule)

        registry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.health_check = AsyncMock(return_value=True)
        registry.get.return_value = mock_adapter

        await router.execute_step(step=1, agent_count=10, registry=registry)
        await router.execute_step(step=2, agent_count=10, registry=registry)
        await router.execute_step(step=3, agent_count=10, registry=registry)

        log = router.execution_log()
        assert len(log) == 3
        assert [r.step for r in log] == [1, 2, 3]
        assert all(r.provider_used == "mock" for r in log)

    def test_execution_log_empty_initially(self):
        """execution_log is empty before any steps are executed."""
        from harness.hybrid_exec import HybridExecRouter, HybridSchedule

        router = HybridExecRouter(HybridSchedule())
        assert router.execution_log() == []


# ---------------------------------------------------------------------------
# Error handling (SPEC §13.3)
# ---------------------------------------------------------------------------


@pytest.mark.phase3
@pytest.mark.unit
class TestHybridExecErrors:
    """SPEC: 09_HARNESS_SPEC.md#13-f30 — error specification"""

    @pytest.mark.asyncio
    async def test_no_providers_healthy_raises(self):
        """No healthy providers must raise LLMProviderError."""
        from harness.hybrid_exec import HybridExecRouter, HybridSchedule

        schedule = HybridSchedule(default_provider="mock")
        router = HybridExecRouter(schedule)

        registry = MagicMock()
        unhealthy = MagicMock()
        unhealthy.health_check = AsyncMock(return_value=False)
        registry.get.return_value = unhealthy

        from app.llm.schema import LLMProviderError

        with pytest.raises(LLMProviderError):
            await router.execute_step(step=1, agent_count=10, registry=registry)
