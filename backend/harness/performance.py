"""F27 — Performance Monitor.
SPEC: docs/spec/09_HARNESS_SPEC.md#10-f27--performance-monitor
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator

try:
    import psutil  # optional — gracefully absent
    _PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PSUTIL_AVAILABLE = False


@dataclass
class StepProfile:
    """Timing and resource breakdown for a single simulation step.

    SPEC: docs/spec/09_HARNESS_SPEC.md#10-f27--performance-monitor
    """
    step: int
    total_duration_ms: float = 0.0
    exposure_ms: float = 0.0
    agent_tick_ms: float = 0.0
    propagation_ms: float = 0.0
    cascade_detection_ms: float = 0.0
    db_write_ms: float = 0.0
    ws_broadcast_ms: float = 0.0
    llm_calls_ms: float = 0.0
    agent_count: int = 0
    llm_call_count: int = 0
    memory_mb: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """Return JSON-safe representation."""
        return {
            "step": self.step,
            "total_duration_ms": self.total_duration_ms,
            "exposure_ms": self.exposure_ms,
            "agent_tick_ms": self.agent_tick_ms,
            "propagation_ms": self.propagation_ms,
            "cascade_detection_ms": self.cascade_detection_ms,
            "db_write_ms": self.db_write_ms,
            "ws_broadcast_ms": self.ws_broadcast_ms,
            "llm_calls_ms": self.llm_calls_ms,
            "agent_count": self.agent_count,
            "llm_call_count": self.llm_call_count,
            "memory_mb": self.memory_mb,
        }


class SimulationProfiler:
    """Instruments step execution for performance analysis.

    SPEC: docs/spec/09_HARNESS_SPEC.md#10-f27--performance-monitor

    Usage::

        profiler = SimulationProfiler()
        async with profiler.profile_step(step=1) as profile:
            await run_step()
        print(profile.total_duration_ms)
    """

    def __init__(self) -> None:
        self._profiles: list[StepProfile] = []

    @asynccontextmanager
    async def profile_step(self, step: int) -> AsyncIterator[StepProfile]:
        """Async context manager that measures total wall-clock time for a step.

        SPEC: docs/spec/09_HARNESS_SPEC.md#10-f27--performance-monitor

        Yields a :class:`StepProfile` whose ``total_duration_ms`` is populated
        on context exit.  Sub-timings (agent_tick_ms, propagation_ms, …) remain
        0.0 unless the caller fills them in directly on the yielded object.
        """
        profile = StepProfile(step=step)

        # Capture memory before
        if _PSUTIL_AVAILABLE:
            try:
                proc = psutil.Process()
                profile.memory_mb = proc.memory_info().rss / (1024 * 1024)
            except Exception:
                pass

        start = time.perf_counter()
        try:
            yield profile
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            profile.total_duration_ms = elapsed_ms

            # Re-sample memory after step to reflect peak usage
            if _PSUTIL_AVAILABLE:
                try:
                    proc = psutil.Process()
                    profile.memory_mb = proc.memory_info().rss / (1024 * 1024)
                except Exception:
                    pass

            self._profiles.append(profile)

    def all_profiles(self) -> list[StepProfile]:
        """Return all recorded step profiles in insertion order."""
        return list(self._profiles)

    def summary(self) -> dict[str, object]:
        """Aggregate summary across all recorded steps."""
        if not self._profiles:
            return {"step_count": 0}
        durations = [p.total_duration_ms for p in self._profiles]
        return {
            "step_count": len(self._profiles),
            "total_duration_ms": sum(durations),
            "avg_step_duration_ms": sum(durations) / len(durations),
            "max_step_duration_ms": max(durations),
            "min_step_duration_ms": min(durations),
            "total_llm_calls": sum(p.llm_call_count for p in self._profiles),
        }


__all__ = ["SimulationProfiler", "StepProfile"]
