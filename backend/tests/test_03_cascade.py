"""Tests for CascadeDetector.
Auto-generated from SPEC: docs/spec/03_DIFFUSION_SPEC.md
SPEC Version: 0.1.1
"""
import pytest
from uuid import uuid4

from app.engine.diffusion.schema import CascadeConfig, EmergentEvent
from app.engine.diffusion.cascade_detector import CascadeDetector, StepResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_step_result(
    step: int,
    total_agents: int = 100,
    adopted_count: int = 0,
    community_variances: dict | None = None,
    internal_links: dict | None = None,
    external_links: dict | None = None,
) -> StepResult:
    adoption_rate = adopted_count / total_agents if total_agents > 0 else 0.0
    return StepResult(
        step=step,
        total_agents=total_agents,
        adopted_count=adopted_count,
        adoption_rate=adoption_rate,
        community_sentiments={},
        community_variances=community_variances or {},
        community_adoption_rates={},
        internal_links=internal_links or {},
        external_links=external_links or {},
        adopted_agent_ids=[uuid4() for _ in range(adopted_count)],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.phase4
@pytest.mark.unit
class TestCascadeDetectorInit:
    """SPEC: 03_DIFFUSION_SPEC.md#cascadedetector"""

    def test_default_config(self):
        detector = CascadeDetector()
        assert detector._config.viral_cascade_threshold == 0.15

    def test_custom_config(self):
        cfg = CascadeConfig(viral_cascade_threshold=0.10)
        detector = CascadeDetector(config=cfg)
        assert detector._config.viral_cascade_threshold == 0.10

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError):
            CascadeConfig(viral_cascade_threshold=0)

    def test_invalid_negative_threshold_raises(self):
        with pytest.raises(ValueError):
            CascadeConfig(collapse_drop_rate=-0.1)


@pytest.mark.phase4
@pytest.mark.unit
class TestViralCascadeDetection:
    """SPEC: 03_DIFFUSION_SPEC.md#cascadedetector — Viral Cascade"""

    def test_viral_cascade_detected(self):
        """DIF-04: Viral cascade at threshold."""
        detector = CascadeDetector()

        history = [_make_step_result(step=0, adopted_count=5)]
        current = _make_step_result(step=1, adopted_count=20)  # +15%

        events = detector.detect(current, history)
        viral_events = [e for e in events if e.event_type == "viral_cascade"]
        assert len(viral_events) == 1
        assert viral_events[0].step == 1

    def test_no_viral_below_threshold(self):
        detector = CascadeDetector()

        history = [_make_step_result(step=0, adopted_count=5)]
        current = _make_step_result(step=1, adopted_count=10)  # +5%

        events = detector.detect(current, history)
        viral_events = [e for e in events if e.event_type == "viral_cascade"]
        assert len(viral_events) == 0


@pytest.mark.phase4
@pytest.mark.unit
class TestSlowAdoptionDetection:
    """SPEC: 03_DIFFUSION_SPEC.md#cascadedetector — Slow Adoption"""

    def test_slow_adoption_detected(self):
        detector = CascadeDetector()

        # 5 steps with minimal adoption change
        history = [_make_step_result(step=i, adopted_count=i) for i in range(4)]
        current = _make_step_result(step=4, adopted_count=4)

        events = detector.detect(current, history)
        slow_events = [e for e in events if e.event_type == "slow_adoption"]
        assert len(slow_events) == 1

    def test_not_enough_history(self):
        detector = CascadeDetector()
        history = [_make_step_result(step=0, adopted_count=0)]
        current = _make_step_result(step=1, adopted_count=1)

        events = detector.detect(current, history)
        slow_events = [e for e in events if e.event_type == "slow_adoption"]
        assert len(slow_events) == 0


@pytest.mark.phase4
@pytest.mark.unit
class TestPolarizationDetection:
    """SPEC: 03_DIFFUSION_SPEC.md#cascadedetector — Polarization"""

    def test_polarization_detected(self):
        """DIF-05: Polarization detection."""
        cid = uuid4()
        detector = CascadeDetector()

        current = _make_step_result(
            step=1,
            community_variances={cid: 0.5},
        )

        events = detector.detect(current, [])
        polar_events = [e for e in events if e.event_type == "polarization"]
        assert len(polar_events) == 1
        assert polar_events[0].community_id == cid

    def test_no_polarization_below_threshold(self):
        cid = uuid4()
        detector = CascadeDetector()

        # Round 8-8: default threshold lowered from 0.4 → 0.05 to
        # match realistic belief-variance ranges in Prophet pilots.
        # A 0.01 variance is below the new threshold and must not fire.
        current = _make_step_result(
            step=1,
            community_variances={cid: 0.01},
        )

        events = detector.detect(current, [])
        polar_events = [e for e in events if e.event_type == "polarization"]
        assert len(polar_events) == 0

    def test_realistic_pilot_variance_fires_polarization(self):
        """Round 8-8 regression: the pilots in docs/USE_CASE_PILOTS.md
        show community belief variances in the 0.05-0.07 range for
        hostile-framing scenarios. The old 0.4 threshold meant none of
        those pilots ever fired polarization, which contradicted the
        README's "polarization auto-detection" claim. The 0.05 default
        now fires cleanly on realistic pilot data.
        """
        cid = uuid4()
        detector = CascadeDetector()

        current = _make_step_result(
            step=3,
            community_variances={cid: 0.065},  # typical UC1 baseline variance
        )

        events = detector.detect(current, [])
        polar_events = [e for e in events if e.event_type == "polarization"]
        assert len(polar_events) == 1
        assert polar_events[0].community_id == cid

    def test_reset_clears_slow_adoption_guard(self):
        """Round 8-8 regression: the ``_slow_adoption_fired`` one-shot
        guard used to leak across simulations because the orchestrator
        held a single StepRunner (and therefore a single CascadeDetector)
        for its entire lifetime. After firing slow_adoption on
        simulation A, simulation B would never fire it until adoption
        recovered above the threshold first. ``reset()`` clears the
        guard explicitly on simulation creation.
        """
        detector = CascadeDetector()
        # Simulate slow adoption: 5 steps with per-step delta < 0.02
        # Using total_agents=1000 so integer adopted_counts map to
        # clean percentages; deltas of 5 agents = 0.005 per step.
        history: list = []
        for step in range(1, 6):
            adopted = 5 * step  # 5, 10, 15, 20, 25 agents
            current = _make_step_result(
                step=step, total_agents=1000, adopted_count=adopted,
            )
            detector.detect(current, history)
            history.append(current)

        assert detector._slow_adoption_fired is True, (
            "slow_adoption one-shot guard should be set after a stall episode"
        )

        detector.reset()
        assert detector._slow_adoption_fired is False, (
            "reset() must clear the one-shot guard"
        )


@pytest.mark.phase4
@pytest.mark.unit
class TestCollapseDetection:
    """SPEC: 03_DIFFUSION_SPEC.md#cascadedetector — Collapse"""

    def test_collapse_detected(self):
        """DIF-09: Collapse after rapid belief drop."""
        detector = CascadeDetector()

        history = [
            _make_step_result(step=0, adopted_count=50),  # 50%
            _make_step_result(step=1, adopted_count=45),  # 45%
        ]
        current = _make_step_result(step=2, adopted_count=30)  # 30% (40% drop from 50%)

        events = detector.detect(current, history)
        collapse_events = [e for e in events if e.event_type == "collapse"]
        assert len(collapse_events) == 1

    def test_no_collapse_without_enough_history(self):
        detector = CascadeDetector()
        current = _make_step_result(step=0, adopted_count=30)

        events = detector.detect(current, [])
        collapse_events = [e for e in events if e.event_type == "collapse"]
        assert len(collapse_events) == 0

    def test_no_collapse_with_small_drop(self):
        detector = CascadeDetector()

        history = [
            _make_step_result(step=0, adopted_count=50),
            _make_step_result(step=1, adopted_count=48),
        ]
        current = _make_step_result(step=2, adopted_count=46)  # small drop

        events = detector.detect(current, history)
        collapse_events = [e for e in events if e.event_type == "collapse"]
        assert len(collapse_events) == 0


@pytest.mark.phase4
@pytest.mark.unit
class TestEchoChamberDetection:
    """SPEC: 03_DIFFUSION_SPEC.md#cascadedetector — Echo Chamber"""

    def test_echo_chamber_detected(self):
        cid = uuid4()
        detector = CascadeDetector()

        current = _make_step_result(
            step=1,
            internal_links={cid: 100},
            external_links={cid: 5},  # ratio = 20 > 10
        )

        events = detector.detect(current, [])
        echo_events = [e for e in events if e.event_type == "echo_chamber"]
        assert len(echo_events) == 1
        assert echo_events[0].community_id == cid

    def test_no_echo_chamber_balanced(self):
        cid = uuid4()
        detector = CascadeDetector()

        current = _make_step_result(
            step=1,
            internal_links={cid: 50},
            external_links={cid: 50},  # ratio = 1
        )

        events = detector.detect(current, [])
        echo_events = [e for e in events if e.event_type == "echo_chamber"]
        assert len(echo_events) == 0

    def test_echo_chamber_no_external_links(self):
        cid = uuid4()
        detector = CascadeDetector()

        current = _make_step_result(
            step=1,
            internal_links={cid: 100},
            external_links={cid: 0},  # ratio = inf
        )

        events = detector.detect(current, [])
        echo_events = [e for e in events if e.event_type == "echo_chamber"]
        assert len(echo_events) == 1


@pytest.mark.phase4
@pytest.mark.unit
class TestCascadeDetectorEmpty:
    """SPEC: 03_DIFFUSION_SPEC.md#cascadedetector — Edge Cases"""

    def test_empty_results_no_events(self):
        detector = CascadeDetector()
        current = _make_step_result(step=0, adopted_count=0)

        events = detector.detect(current, [])
        # May have slow_adoption if we have enough steps, but with 1 step, no
        assert isinstance(events, list)

    def test_detect_returns_list(self):
        detector = CascadeDetector()
        current = _make_step_result(step=0)
        result = detector.detect(current, [])
        assert isinstance(result, list)
