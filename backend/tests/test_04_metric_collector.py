"""
Auto-generated from SPEC: docs/spec/04_SIMULATION_SPEC.md#metriccollector
SPEC Version: 0.1.1
Interface tests for MetricCollector.
"""
import pytest
from uuid import uuid4

from app.engine.agent.schema import (
    AgentAction,
    AgentEmotion,
    AgentPersonality,
    AgentState,
    AgentType,
)
from app.engine.agent.tick import AgentTickResult
from app.engine.agent.influence import PropagationEvent
from app.engine.agent.memory import MemoryRecord
from app.engine.simulation.metric_collector import MetricCollector
from app.engine.simulation.schema import StepResult


def _make_agent_state(adopted: bool = False, belief: float = 0.0) -> AgentState:
    return AgentState(
        agent_id=uuid4(),
        simulation_id=uuid4(),
        agent_type=AgentType.CONSUMER,
        step=0,
        personality=AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5),
        emotion=AgentEmotion(0.5, 0.5, 0.3, 0.4),
        belief=belief,
        action=AgentAction.LIKE if adopted else AgentAction.IGNORE,
        exposure_count=1,
        adopted=adopted,
        community_id=uuid4(),
        influence_score=0.3,
        llm_tier_used=1,
    )


def _make_tick_result(adopted: bool = False, belief: float = 0.0) -> AgentTickResult:
    state = _make_agent_state(adopted=adopted, belief=belief)
    return AgentTickResult(
        updated_state=state,
        propagation_events=[],
        memory_stored=None,
        llm_call_log=None,
        action=state.action,
        llm_tier_used=1,
    )


@pytest.mark.phase6
class TestMetricCollector:
    """SPEC: 04_SIMULATION_SPEC.md#metriccollector"""

    def test_record_returns_step_result(self):
        """record() returns a StepResult."""
        collector = MetricCollector()
        sim_id = uuid4()
        results = [_make_tick_result() for _ in range(10)]
        sr = collector.record(sim_id, 0, results, [], 100.0)
        assert isinstance(sr, StepResult)

    def test_record_computes_adoption_rate(self):
        """record() correctly computes adoption_rate."""
        collector = MetricCollector()
        sim_id = uuid4()
        # 3 out of 10 adopted
        results = [_make_tick_result(adopted=True) for _ in range(3)]
        results += [_make_tick_result(adopted=False) for _ in range(7)]
        sr = collector.record(sim_id, 0, results, [], 50.0)
        assert sr.total_adoption == 3
        assert abs(sr.adoption_rate - 0.3) < 1e-6

    def test_record_computes_action_distribution(self):
        """record() tallies action distribution."""
        collector = MetricCollector()
        sim_id = uuid4()
        results = [_make_tick_result() for _ in range(5)]
        sr = collector.record(sim_id, 0, results, [], 50.0)
        total_actions = sum(sr.action_distribution.values())
        assert total_actions == 5

    def test_record_computes_mean_sentiment(self):
        """record() computes mean_sentiment from beliefs."""
        collector = MetricCollector()
        sim_id = uuid4()
        results = [
            _make_tick_result(belief=0.5),
            _make_tick_result(belief=-0.5),
        ]
        sr = collector.record(sim_id, 0, results, [], 50.0)
        assert abs(sr.mean_sentiment - 0.0) < 1e-6

    def test_record_stores_emergent_events(self):
        """record() includes emergent_events."""
        from app.engine.diffusion.schema import EmergentEvent
        collector = MetricCollector()
        sim_id = uuid4()
        events = [
            EmergentEvent(
                event_type="viral_cascade",
                step=0,
                community_id=None,
                severity=0.8,
                description="test",
                affected_agent_ids=[],
            )
        ]
        sr = collector.record(sim_id, 0, [_make_tick_result()], events, 50.0)
        assert len(sr.emergent_events) == 1
        assert sr.emergent_events[0].event_type == "viral_cascade"

    def test_get_metric_history(self):
        """get_metric_history returns metric values by step."""
        collector = MetricCollector()
        sim_id = uuid4()
        # Record 3 steps
        for step in range(3):
            results = [_make_tick_result(adopted=(step > 0)) for _ in range(5)]
            collector.record(sim_id, step, results, [], 50.0)

        history = collector.get_metric_history(sim_id, "adoption_rate")
        assert len(history) == 3
        assert all(isinstance(h, tuple) and len(h) == 2 for h in history)

    def test_get_metric_history_with_range(self):
        """get_metric_history respects from_step/to_step."""
        collector = MetricCollector()
        sim_id = uuid4()
        for step in range(5):
            collector.record(sim_id, step, [_make_tick_result()], [], 50.0)

        history = collector.get_metric_history(sim_id, "adoption_rate", from_step=1, to_step=3)
        steps = [h[0] for h in history]
        assert all(1 <= s <= 3 for s in steps)

    def test_get_metric_history_unknown_simulation(self):
        """get_metric_history returns empty for unknown simulation."""
        collector = MetricCollector()
        history = collector.get_metric_history(uuid4(), "adoption_rate")
        assert history == []

    def test_diffusion_rate_computed(self):
        """record() computes diffusion_rate correctly."""
        collector = MetricCollector()
        sim_id = uuid4()
        # Step 0: 0 adopted
        collector.record(sim_id, 0, [_make_tick_result(adopted=False)], [], 50.0)
        # Step 1: 1 adopted
        sr = collector.record(sim_id, 1, [_make_tick_result(adopted=True)], [], 50.0)
        assert sr.diffusion_rate >= 0.0
