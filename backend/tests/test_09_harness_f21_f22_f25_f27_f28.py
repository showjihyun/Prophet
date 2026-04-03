"""
Auto-generated from SPEC: docs/spec/09_HARNESS_SPEC.md
SPEC Version: 0.1.0
Covers: F21 MetricLogger, F22 ModuleRegistry, F25 AgentDecisionDebugger,
        F27 SimulationProfiler, F28 FailureRecoveryManager, HarnessRunner
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# F21 — Metric Logging API
# ---------------------------------------------------------------------------

@pytest.mark.phase2
@pytest.mark.unit
class TestMetricLogger:
    """SPEC: 09_HARNESS_SPEC.md#6-f21--metric-logging-api"""

    def _make_logger(self, path=None):
        from harness.metric_logger import MetricLogger
        return MetricLogger(simulation_id=uuid4(), output_path=path)

    def test_imports(self):
        """MetricLogger is importable from harness.metric_logger."""
        from harness.metric_logger import MetricLogger  # noqa: F401

    def test_log_performance_stores_event(self):
        """log_performance should store a performance event in memory."""
        ml = self._make_logger()
        ml.log_performance(step=1, duration_ms=42.5, agent_count=500)
        summary = ml.get_summary()
        assert summary["total_events"] == 1

    def test_log_agent_action_stores_event(self):
        from app.engine.agent.schema import AgentAction
        ml = self._make_logger()
        ml.log_agent_action(agent_id=uuid4(), step=0, action=AgentAction.LIKE)
        summary = ml.get_summary()
        assert summary["agent_action_count"] == 1

    def test_log_emergent_event_stored(self):
        from app.engine.diffusion.schema import EmergentEvent
        ml = self._make_logger()
        event = EmergentEvent(
            event_type="viral_cascade",
            step=1,
            community_id=None,
            severity=0.8,
            description="test cascade",
            affected_agent_ids=[],
        )
        ml.log_emergent_event(event)
        summary = ml.get_summary()
        assert summary["emergent_event_count"] == 1

    def test_get_summary_returns_dict_with_required_keys(self):
        ml = self._make_logger()
        ml.log_performance(step=0, duration_ms=10.0, agent_count=100)
        summary = ml.get_summary()
        required_keys = {
            "simulation_id", "total_events", "step_count",
            "agent_action_count", "llm_call_count", "emergent_event_count",
            "total_duration_ms", "avg_step_duration_ms", "final_adoption_rate",
        }
        assert required_keys <= set(summary.keys())

    def test_export_jsonl_writes_file(self, tmp_path: Path):
        ml = self._make_logger()
        ml.log_performance(step=0, duration_ms=5.0, agent_count=10)
        out = tmp_path / "export.jsonl"
        ml.export_jsonl(out)
        lines = out.read_text().strip().split("\n")
        assert len(lines) == 1
        obj = json.loads(lines[0])
        assert obj["event_type"] == "performance"

    def test_output_path_streams_events_incrementally(self, tmp_path: Path):
        """Events written to output_path file as they are logged."""
        out = tmp_path / "stream.jsonl"
        ml = self._make_logger(path=out)
        ml.log_performance(step=0, duration_ms=1.0, agent_count=1)
        ml.log_performance(step=1, duration_ms=2.0, agent_count=1)
        lines = [l for l in out.read_text().strip().split("\n") if l]
        assert len(lines) == 2

    def test_log_llm_call_increments_count(self):
        from app.llm.schema import LLMCallLog
        from datetime import datetime, timezone
        ml = self._make_logger()
        log = LLMCallLog(
            call_id=uuid4(),
            simulation_id=uuid4(),
            agent_id=uuid4(),
            step=0,
            provider="mock",
            model="mock-1.0",
            prompt_hash="abc",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=1.0,
            cached=False,
        )
        ml.log_llm_call(log)
        summary = ml.get_summary()
        assert summary["llm_call_count"] == 1


# ---------------------------------------------------------------------------
# F22 — Module Hot-Swap
# ---------------------------------------------------------------------------

@pytest.mark.phase2
@pytest.mark.unit
class TestModuleRegistry:
    """SPEC: 09_HARNESS_SPEC.md#7-f22--module-hot-swap"""

    def test_imports(self):
        from harness.hotswap import ModuleRegistry  # noqa: F401

    def test_register_and_get(self):
        from harness.hotswap import ModuleRegistry
        reg = ModuleRegistry()
        obj = object()
        reg.register("my_module", obj)
        assert reg.get("my_module") is obj

    def test_swap_returns_old_module(self):
        from harness.hotswap import ModuleRegistry
        reg = ModuleRegistry()
        original = object()
        replacement = object()
        reg.register("mod", original)
        old = reg.swap("mod", replacement)
        assert old is original
        assert reg.get("mod") is replacement

    def test_swap_on_unregistered_name_returns_none(self):
        from harness.hotswap import ModuleRegistry
        reg = ModuleRegistry()
        old = reg.swap("nonexistent", "value")
        assert old is None
        assert reg.get("nonexistent") == "value"

    def test_get_raises_key_error_for_unknown(self):
        from harness.hotswap import ModuleRegistry
        reg = ModuleRegistry()
        with pytest.raises(KeyError):
            reg.get("does_not_exist")

    def test_contains(self):
        from harness.hotswap import ModuleRegistry
        reg = ModuleRegistry()
        reg.register("foo", 42)
        assert "foo" in reg
        assert "bar" not in reg

    def test_registered_names(self):
        from harness.hotswap import ModuleRegistry
        reg = ModuleRegistry()
        reg.register("z", 1)
        reg.register("a", 2)
        names = reg.registered_names()
        assert names == ["a", "z"]


# ---------------------------------------------------------------------------
# F25 — Debug Visualization
# ---------------------------------------------------------------------------

@pytest.mark.phase3
@pytest.mark.unit
class TestAgentDecisionDebugger:
    """SPEC: 09_HARNESS_SPEC.md#9-f25--debug-visualization"""

    def test_imports(self):
        from harness.debug_viz import AgentDecisionDebugger, AgentDecisionTrace  # noqa: F401

    def _make_tick_result(self):
        """Build a minimal AgentTickResult for testing explain_tick."""
        from app.engine.agent.schema import (
            AgentAction, AgentEmotion, AgentPersonality, AgentState, AgentType,
        )
        from app.engine.agent.tick import AgentTickResult

        sim_id = uuid4()
        agent_id = uuid4()
        community_id = uuid4()
        personality = AgentPersonality(
            openness=0.5, skepticism=0.5, trend_following=0.5,
            brand_loyalty=0.5, social_influence=0.5,
        )
        emotion = AgentEmotion(interest=0.5, trust=0.5, skepticism=0.5, excitement=0.5)
        state = AgentState(
            agent_id=agent_id,
            simulation_id=sim_id,
            agent_type=AgentType.CONSUMER,
            step=1,
            personality=personality,
            emotion=emotion,
            belief=0.1,
            action=AgentAction.LIKE,
            exposure_count=3,
            adopted=False,
            community_id=community_id,
            influence_score=0.2,
            llm_tier_used=1,
        )
        return AgentTickResult(
            updated_state=state,
            propagation_events=[],
            memory_stored=None,
            llm_call_log=None,
            action=AgentAction.LIKE,
            llm_tier_used=1,
        )

    def test_explain_tick_returns_trace(self):
        from harness.debug_viz import AgentDecisionDebugger, AgentDecisionTrace
        debugger = AgentDecisionDebugger()
        tick = self._make_tick_result()
        trace = debugger.explain_tick(tick)
        assert isinstance(trace, AgentDecisionTrace)

    def test_trace_has_required_fields(self):
        from harness.debug_viz import AgentDecisionDebugger
        debugger = AgentDecisionDebugger()
        tick = self._make_tick_result()
        trace = debugger.explain_tick(tick)
        assert trace.agent_id is not None
        assert trace.step == 1
        assert trace.tier_used == 1
        assert isinstance(trace.perception_summary, str)
        assert isinstance(trace.memories_retrieved, list)
        assert isinstance(trace.action_probabilities, dict)

    def test_trace_chosen_action_matches_tick(self):
        from app.engine.agent.schema import AgentAction
        from harness.debug_viz import AgentDecisionDebugger
        debugger = AgentDecisionDebugger()
        tick = self._make_tick_result()
        trace = debugger.explain_tick(tick)
        assert trace.chosen_action == AgentAction.LIKE

    def test_trace_to_dict_is_json_serialisable(self):
        from harness.debug_viz import AgentDecisionDebugger
        debugger = AgentDecisionDebugger()
        tick = self._make_tick_result()
        trace = debugger.explain_tick(tick)
        d = trace.to_dict()
        assert json.dumps(d)  # must not raise


# ---------------------------------------------------------------------------
# F27 — Performance Monitor
# ---------------------------------------------------------------------------

@pytest.mark.phase2
@pytest.mark.unit
class TestSimulationProfiler:
    """SPEC: 09_HARNESS_SPEC.md#10-f27--performance-monitor"""

    def test_imports(self):
        from harness.performance import SimulationProfiler, StepProfile  # noqa: F401

    @pytest.mark.asyncio
    async def test_profile_step_records_duration(self):
        from harness.performance import SimulationProfiler
        profiler = SimulationProfiler()
        async with profiler.profile_step(step=1) as profile:
            pass
        assert profile.step == 1
        assert profile.total_duration_ms >= 0.0

    @pytest.mark.asyncio
    async def test_profile_yields_step_profile(self):
        from harness.performance import SimulationProfiler, StepProfile
        profiler = SimulationProfiler()
        async with profiler.profile_step(step=5) as profile:
            assert isinstance(profile, StepProfile)
            assert profile.step == 5

    @pytest.mark.asyncio
    async def test_all_profiles_accumulates(self):
        from harness.performance import SimulationProfiler
        profiler = SimulationProfiler()
        for step in range(3):
            async with profiler.profile_step(step=step):
                pass
        assert len(profiler.all_profiles()) == 3

    @pytest.mark.asyncio
    async def test_summary_aggregates_correctly(self):
        from harness.performance import SimulationProfiler
        profiler = SimulationProfiler()
        for step in range(5):
            async with profiler.profile_step(step=step):
                pass
        s = profiler.summary()
        assert s["step_count"] == 5
        assert s["total_duration_ms"] >= 0.0

    def test_step_profile_to_dict_has_required_keys(self):
        from harness.performance import StepProfile
        profile = StepProfile(step=0, total_duration_ms=123.4, agent_count=50)
        d = profile.to_dict()
        required = {
            "step", "total_duration_ms", "agent_tick_ms", "propagation_ms",
            "cascade_detection_ms", "db_write_ms", "llm_calls_ms",
            "agent_count", "llm_call_count", "memory_mb",
        }
        assert required <= set(d.keys())

    @pytest.mark.asyncio
    async def test_caller_can_set_sub_timings(self):
        """Caller should be able to set sub-timing fields on the yielded profile."""
        from harness.performance import SimulationProfiler
        profiler = SimulationProfiler()
        async with profiler.profile_step(step=0) as profile:
            profile.agent_tick_ms = 50.0
            profile.llm_calls_ms = 30.0
            profile.agent_count = 100
        assert profile.agent_tick_ms == 50.0
        assert profile.llm_calls_ms == 30.0


# ---------------------------------------------------------------------------
# F28 — Failure Recovery
# ---------------------------------------------------------------------------

@pytest.mark.phase2
@pytest.mark.unit
class TestFailureRecoveryManager:
    """SPEC: 09_HARNESS_SPEC.md#11-f28--failure-recovery"""

    def test_imports(self):
        from harness.recovery import FailureRecoveryManager  # noqa: F401

    @pytest.mark.asyncio
    async def test_with_llm_fallback_success(self):
        """Successful coroutine is returned as-is."""
        from app.engine.agent.cognition import CognitionResult
        from app.engine.agent.schema import AgentAction
        from harness.recovery import FailureRecoveryManager

        async def good_call() -> CognitionResult:
            return CognitionResult(
                evaluation_score=0.5,
                reasoning="ok",
                recommended_action=AgentAction.LIKE,
                confidence=0.8,
                tier_used=3,
            )

        mgr = FailureRecoveryManager()
        result = await mgr.with_llm_fallback(good_call())
        assert result.tier_used == 3
        assert result.evaluation_score == 0.5

    @pytest.mark.asyncio
    async def test_with_llm_fallback_on_timeout(self):
        """LLMTimeoutError triggers fallback."""
        from app.llm.schema import LLMTimeoutError
        from harness.recovery import FailureRecoveryManager

        async def failing_call():
            raise LLMTimeoutError("timeout")

        mgr = FailureRecoveryManager()
        result = await mgr.with_llm_fallback(failing_call(), fallback_tier=2)
        assert result.tier_used == 2

    @pytest.mark.asyncio
    async def test_with_agent_retry_success(self):
        from app.engine.agent.schema import AgentAction
        from app.engine.agent.tick import AgentTickResult
        from harness.recovery import FailureRecoveryManager

        async def good_tick() -> AgentTickResult:
            return AgentTickResult(
                updated_state=None,  # type: ignore
                propagation_events=[],
                memory_stored=None,
                llm_call_log=None,
                action=AgentAction.LIKE,
                llm_tier_used=1,
            )

        mgr = FailureRecoveryManager()
        result = await mgr.with_agent_retry(good_tick())
        assert result.action == AgentAction.LIKE

    @pytest.mark.asyncio
    async def test_with_agent_retry_failure_returns_safe_default(self):
        from app.engine.agent.schema import AgentAction
        from harness.recovery import FailureRecoveryManager

        async def bad_tick():
            raise RuntimeError("agent boom")

        mgr = FailureRecoveryManager()
        result = await mgr.with_agent_retry(bad_tick(), max_retries=1)
        assert result.action == AgentAction.IGNORE

    def test_checkpoint_stores_state(self):
        from harness.recovery import FailureRecoveryManager
        from app.engine.agent.schema import (
            AgentAction, AgentEmotion, AgentPersonality, AgentState, AgentType,
        )

        sim_id = uuid4()
        agent_id = uuid4()
        community_id = uuid4()
        personality = AgentPersonality(
            openness=0.5, skepticism=0.5, trend_following=0.5,
            brand_loyalty=0.5, social_influence=0.5,
        )
        emotion = AgentEmotion(interest=0.5, trust=0.5, skepticism=0.5, excitement=0.5)
        state = AgentState(
            agent_id=agent_id,
            simulation_id=sim_id,
            agent_type=AgentType.CONSUMER,
            step=3,
            personality=personality,
            emotion=emotion,
            belief=0.0,
            action=AgentAction.IGNORE,
            exposure_count=0,
            adopted=False,
            community_id=community_id,
            influence_score=0.0,
            llm_tier_used=None,
        )
        mgr = FailureRecoveryManager()
        mgr.checkpoint(sim_id, step=3, agent_states=[state])
        ckpt = mgr.load_checkpoint(sim_id, step=3)
        assert ckpt is not None
        assert ckpt["step"] == 3
        assert ckpt["agent_count"] == 1

    def test_latest_step_returns_none_when_no_checkpoints(self):
        from harness.recovery import FailureRecoveryManager
        mgr = FailureRecoveryManager()
        assert mgr.latest_step(uuid4()) is None

    def test_latest_step_returns_highest_step(self):
        from harness.recovery import FailureRecoveryManager
        mgr = FailureRecoveryManager()
        sim_id = uuid4()
        mgr.checkpoint(sim_id, step=1, agent_states=[])
        mgr.checkpoint(sim_id, step=5, agent_states=[])
        mgr.checkpoint(sim_id, step=3, agent_states=[])
        assert mgr.latest_step(sim_id) == 5


# ---------------------------------------------------------------------------
# HarnessRunner
# ---------------------------------------------------------------------------

@pytest.mark.phase2
@pytest.mark.unit
class TestHarnessRunner:
    """SPEC: 09_HARNESS_SPEC.md#12-harness-test-runner"""

    def test_imports(self):
        from harness.runners.harness_runner import HarnessRunner, HarnessReport  # noqa: F401

    def test_run_phase_returns_report(self):
        from harness.runners.harness_runner import HarnessRunner
        runner = HarnessRunner()
        report = runner.run_phase(2)
        assert report.phase == 2
        assert report.total >= 0
        assert isinstance(report.is_passing, bool)

    def test_run_all_returns_report(self):
        from harness.runners.harness_runner import HarnessRunner
        runner = HarnessRunner()
        report = runner.run_all()
        assert report.total >= 0
        assert report.duration_ms >= 0.0

    def test_harness_report_is_passing_true_when_no_failures(self):
        from harness.runners.harness_runner import HarnessReport
        report = HarnessReport(
            phase=1, total=3, passed=3, failed=0, skipped=0,
            results=[], duration_ms=10.0,
        )
        assert report.is_passing is True

    def test_harness_report_is_passing_false_when_failures(self):
        from harness.runners.harness_runner import HarnessReport
        report = HarnessReport(
            phase=1, total=3, passed=2, failed=1, skipped=0,
            results=[], duration_ms=10.0,
        )
        assert report.is_passing is False

    def test_harness_report_to_dict(self):
        from harness.runners.harness_runner import HarnessReport
        report = HarnessReport(
            phase=2, total=4, passed=4, failed=0, skipped=0,
            results=[], duration_ms=55.0,
        )
        d = report.to_dict()
        assert d["is_passing"] is True
        assert d["total"] == 4
        assert d["duration_ms"] == 55.0

    def test_phase_2_all_checks_pass(self):
        """All F21/F22/F27/F28 checks in phase 2 must pass."""
        from harness.runners.harness_runner import HarnessRunner
        runner = HarnessRunner()
        report = runner.run_phase(2)
        failed_names = [r.name for r in report.results if not r.passed]
        assert failed_names == [], f"Phase 2 failures: {failed_names}"

    def test_phase_3_all_checks_pass(self):
        """All F25 checks in phase 3 must pass."""
        from harness.runners.harness_runner import HarnessRunner
        runner = HarnessRunner()
        report = runner.run_phase(3)
        failed_names = [r.name for r in report.results if not r.passed]
        assert failed_names == [], f"Phase 3 failures: {failed_names}"
