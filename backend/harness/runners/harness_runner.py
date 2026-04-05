"""Harness Test Runner — F18–F30 orchestration.
SPEC: docs/spec/09_HARNESS_SPEC.md#12-harness-test-runner
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class HarnessTestResult:
    """Result of a single harness acceptance test.

    SPEC: docs/spec/09_HARNESS_SPEC.md#12-harness-test-runner
    """
    name: str
    passed: bool
    skipped: bool = False
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class HarnessReport:
    """Aggregated report from a harness run.

    SPEC: docs/spec/09_HARNESS_SPEC.md#12-harness-test-runner
    """
    phase: int
    total: int
    passed: int
    failed: int
    skipped: int
    results: list[HarnessTestResult]
    duration_ms: float

    @property
    def is_passing(self) -> bool:
        """True when no tests failed.

        SPEC: docs/spec/09_HARNESS_SPEC.md#12-harness-test-runner
        """
        return self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe representation."""
        return {
            "phase": self.phase,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "is_passing": self.is_passing,
            "duration_ms": self.duration_ms,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "skipped": r.skipped,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                }
                for r in self.results
            ],
        }


# Registry of all known phases and their test callables.
# Each entry: (phase: int, name: str, fn: Callable[[], bool])
_PHASE_TESTS: dict[int, list[tuple[str, Callable[[], bool]]]] = {}


def _register(phase: int, name: str, fn: Callable[[], bool]) -> None:
    _PHASE_TESTS.setdefault(phase, []).append((name, fn))


# ---------------------------------------------------------------------------
# Built-in acceptance checks (lightweight, no external deps)
# ---------------------------------------------------------------------------

def _check_f21_metric_logger() -> bool:
    from harness.metric_logger import MetricLogger
    from uuid import uuid4
    ml = MetricLogger(simulation_id=uuid4())
    ml.log_performance(step=0, duration_ms=10.0, agent_count=100)
    summary = ml.get_summary()
    return summary["step_count"] == 0 and summary["agent_action_count"] == 0


def _check_f22_module_registry() -> bool:
    from harness.hotswap import ModuleRegistry
    reg = ModuleRegistry()
    reg.register("adapter", object())
    old = reg.swap("adapter", "new_adapter")
    return old is not None and reg.get("adapter") == "new_adapter"


def _check_f25_debug_viz() -> bool:
    from harness.debug_viz import AgentDecisionDebugger, AgentDecisionTrace
    return callable(getattr(AgentDecisionDebugger, "explain_tick", None))


def _check_f27_profiler() -> bool:
    import asyncio
    from harness.performance import SimulationProfiler

    async def _inner() -> bool:
        profiler = SimulationProfiler()
        async with profiler.profile_step(step=0) as profile:
            pass
        return profile.total_duration_ms >= 0.0

    return asyncio.get_event_loop().run_until_complete(_inner())


def _check_f28_recovery() -> bool:
    from harness.recovery import FailureRecoveryManager
    mgr = FailureRecoveryManager()
    return callable(getattr(mgr, "with_llm_fallback", None))


# Register F21, F22, F25, F27, F28 under phase 2 / phase 3
_register(2, "F21:MetricLogger", _check_f21_metric_logger)
_register(2, "F22:ModuleRegistry", _check_f22_module_registry)
_register(2, "F27:SimulationProfiler", _check_f27_profiler)
_register(2, "F28:FailureRecoveryManager", _check_f28_recovery)
_register(3, "F25:AgentDecisionDebugger", _check_f25_debug_viz)


def _check_f30_hybrid_exec() -> bool:
    """F30: Hybrid Execution Mode — HybridExecRouter importable and functional."""
    from harness.hybrid_exec import HybridExecRouter, HybridSchedule, HybridStepResult
    schedule = HybridSchedule(
        step_provider_map={1: "mock"},
        default_provider="ollama",
    )
    router = HybridExecRouter(schedule)
    assert router.select_provider(1) == "mock"
    assert router.select_provider(99) == "ollama"
    assert router.execution_log() == []
    return True


_register(3, "F30:HybridExecRouter", _check_f30_hybrid_exec)


# ---------------------------------------------------------------------------
# HarnessRunner
# ---------------------------------------------------------------------------

class HarnessRunner:
    """Orchestrates running all harness acceptance tests for a phase.

    SPEC: docs/spec/09_HARNESS_SPEC.md#12-harness-test-runner

    Usage::

        runner = HarnessRunner()
        report = runner.run_phase(2)
        assert report.is_passing
    """

    def run_phase(self, phase: int) -> HarnessReport:
        """Run all acceptance criteria tests for *phase*.

        SPEC: docs/spec/09_HARNESS_SPEC.md#12-harness-test-runner

        Returns:
            :class:`HarnessReport` with pass/fail per test and overall status.
        """
        tests = _PHASE_TESTS.get(phase, [])
        results: list[HarnessTestResult] = []
        start = time.perf_counter()

        for name, fn in tests:
            t0 = time.perf_counter()
            try:
                ok = fn()
                duration_ms = (time.perf_counter() - t0) * 1000.0
                results.append(HarnessTestResult(
                    name=name,
                    passed=bool(ok),
                    duration_ms=duration_ms,
                    error=None if ok else "returned False",
                ))
            except Exception as exc:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                results.append(HarnessTestResult(
                    name=name,
                    passed=False,
                    duration_ms=duration_ms,
                    error=str(exc),
                ))

        total_ms = (time.perf_counter() - start) * 1000.0
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed and not r.skipped)
        skipped = sum(1 for r in results if r.skipped)

        return HarnessReport(
            phase=phase,
            total=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            results=results,
            duration_ms=total_ms,
        )

    def run_all(self) -> HarnessReport:
        """Run all registered phases and aggregate into a single report.

        SPEC: docs/spec/09_HARNESS_SPEC.md#12-harness-test-runner
        """
        all_results: list[HarnessTestResult] = []
        start = time.perf_counter()

        for phase in sorted(_PHASE_TESTS):
            report = self.run_phase(phase)
            all_results.extend(report.results)

        total_ms = (time.perf_counter() - start) * 1000.0
        passed = sum(1 for r in all_results if r.passed)
        failed = sum(1 for r in all_results if not r.passed and not r.skipped)
        skipped = sum(1 for r in all_results if r.skipped)

        return HarnessReport(
            phase=0,  # 0 = all phases
            total=len(all_results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            results=all_results,
            duration_ms=total_ms,
        )


__all__ = ["HarnessRunner", "HarnessReport", "HarnessTestResult"]
