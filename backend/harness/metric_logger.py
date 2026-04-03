"""F21 — Metric Logging API.
SPEC: docs/spec/09_HARNESS_SPEC.md#6-f21--metric-logging-api
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID


@dataclass
class MetricLogger:
    """Structured logging of all simulation events.

    Writes to: in-memory list + optional JSONL file.
    SPEC: docs/spec/09_HARNESS_SPEC.md#6-f21--metric-logging-api
    """

    simulation_id: UUID
    output_path: Path | None = None

    _events: list[dict[str, Any]] = field(default_factory=list, init=False)

    def _append(self, event_type: str, payload: dict[str, Any]) -> None:
        entry = {
            "simulation_id": str(self.simulation_id),
            "logged_at": datetime.now(timezone.utc).isoformat(),
            **payload,
            "event_type": event_type,  # must come last to override any field named event_type
        }
        self._events.append(entry)
        if self.output_path is not None:
            with open(self.output_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, default=str) + "\n")

    def log_step(self, step_result: Any) -> None:
        """Log a full StepResult.

        SPEC: docs/spec/09_HARNESS_SPEC.md#6-f21--metric-logging-api
        """
        try:
            payload = asdict(step_result)
        except TypeError:
            payload = {"raw": repr(step_result)}
        self._append("step", payload)

    def log_agent_action(self, agent_id: UUID, step: int, action: Any) -> None:
        """Log a single agent action.

        SPEC: docs/spec/09_HARNESS_SPEC.md#6-f21--metric-logging-api
        """
        self._append("agent_action", {
            "agent_id": str(agent_id),
            "step": step,
            "action": action.value if hasattr(action, "value") else str(action),
        })

    def log_llm_call(self, call_log: Any) -> None:
        """Log an LLM call record.

        SPEC: docs/spec/09_HARNESS_SPEC.md#6-f21--metric-logging-api
        """
        try:
            payload = asdict(call_log)
        except TypeError:
            payload = {"raw": repr(call_log)}
        self._append("llm_call", payload)

    def log_emergent_event(self, event: Any) -> None:
        """Log an emergent event detected during simulation.

        SPEC: docs/spec/09_HARNESS_SPEC.md#6-f21--metric-logging-api
        """
        try:
            payload = asdict(event)
        except TypeError:
            payload = {"raw": repr(event)}
        self._append("emergent_event", payload)

    def log_performance(self, step: int, duration_ms: float, agent_count: int) -> None:
        """Log per-step performance metrics.

        SPEC: docs/spec/09_HARNESS_SPEC.md#6-f21--metric-logging-api
        """
        self._append("performance", {
            "step": step,
            "duration_ms": duration_ms,
            "agent_count": agent_count,
        })

    def export_jsonl(self, output_path: Path) -> None:
        """Export all logged events as JSONL for external analysis.

        SPEC: docs/spec/09_HARNESS_SPEC.md#6-f21--metric-logging-api
        """
        with open(output_path, "w", encoding="utf-8") as fh:
            for entry in self._events:
                fh.write(json.dumps(entry, default=str) + "\n")

    def get_summary(self) -> dict[str, Any]:
        """Return aggregated statistics across all logged steps.

        SPEC: docs/spec/09_HARNESS_SPEC.md#6-f21--metric-logging-api
        """
        steps = [e for e in self._events if e["event_type"] == "step"]
        perf = [e for e in self._events if e["event_type"] == "performance"]
        llm_calls = [e for e in self._events if e["event_type"] == "llm_call"]
        emergent = [e for e in self._events if e["event_type"] == "emergent_event"]
        agent_actions = [e for e in self._events if e["event_type"] == "agent_action"]

        total_duration_ms = sum(p["duration_ms"] for p in perf)
        avg_duration_ms = total_duration_ms / len(perf) if perf else 0.0

        adoption_rates = [s.get("adoption_rate", 0.0) for s in steps]
        final_adoption_rate = adoption_rates[-1] if adoption_rates else 0.0

        return {
            "simulation_id": str(self.simulation_id),
            "total_events": len(self._events),
            "step_count": len(steps),
            "agent_action_count": len(agent_actions),
            "llm_call_count": len(llm_calls),
            "emergent_event_count": len(emergent),
            "total_duration_ms": total_duration_ms,
            "avg_step_duration_ms": avg_duration_ms,
            "final_adoption_rate": final_adoption_rate,
        }


__all__ = ["MetricLogger"]
