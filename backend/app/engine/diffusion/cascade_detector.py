"""Cascade Detector — detects emergent behavior patterns.
SPEC: docs/spec/03_DIFFUSION_SPEC.md#cascadedetector
"""
import logging
from dataclasses import dataclass
from uuid import UUID

from app.engine.diffusion.schema import CascadeConfig, EmergentEvent

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """Result of a single simulation step, used by CascadeDetector.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#cascadedetector
    """
    step: int
    total_agents: int
    adopted_count: int
    adoption_rate: float  # adopted_count / total_agents
    community_sentiments: dict[UUID, float]  # community_id -> mean_belief
    community_variances: dict[UUID, float]   # community_id -> sentiment_variance
    community_adoption_rates: dict[UUID, float]  # community_id -> adoption_rate
    internal_links: dict[UUID, int]  # community_id -> intra-community edges
    external_links: dict[UUID, int]  # community_id -> cross-community edges
    adopted_agent_ids: list[UUID]


class CascadeDetector:
    """Detects emergent behavior patterns in simulation history.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#cascadedetector

    Checks for:
        - Viral Cascade: 15% adoption in single step
        - Slow Adoption: 5 steps below threshold
        - Polarization: variance > 0.4
        - Collapse: 20% drop in 3 steps
        - Echo Chamber: internal/external > 10

    Returns list of EmergentEvent (may be empty).
    Fewer steps than window_size -> return empty.
    """

    def __init__(self, config: CascadeConfig | None = None) -> None:
        self._config = config or CascadeConfig()
        self._slow_adoption_fired: bool = False

    def detect(
        self,
        step_results: StepResult,
        history: list[StepResult],
        config: CascadeConfig | None = None,
    ) -> list[EmergentEvent]:
        """Detect emergent behaviors at current step.

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#cascadedetector

        Returns list of EmergentEvent (may be empty).
        """
        cfg = config or self._config
        events: list[EmergentEvent] = []

        # Check viral cascade
        viral = self._check_viral_cascade(step_results, history, cfg)
        if viral is not None:
            events.append(viral)

        # Check slow adoption
        slow = self._check_slow_adoption(step_results, history, cfg)
        if slow is not None:
            events.append(slow)

        # Check polarization
        polarization = self._check_polarization(step_results, cfg)
        if polarization is not None:
            events.append(polarization)

        # Check collapse
        collapse = self._check_collapse(step_results, history, cfg)
        if collapse is not None:
            events.append(collapse)

        # Check echo chamber
        echo = self._check_echo_chamber(step_results, cfg)
        if echo is not None:
            events.append(echo)

        return events

    def _check_viral_cascade(
        self,
        current: StepResult,
        history: list[StepResult],
        config: CascadeConfig,
    ) -> EmergentEvent | None:
        """Viral: >= threshold adoption in single step.

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#cascadedetector
        """
        if not history:
            # First step: check if adoption_rate itself exceeds threshold
            if current.adoption_rate >= config.viral_cascade_threshold:
                return EmergentEvent(
                    event_type="viral_cascade",
                    step=current.step,
                    community_id=None,
                    severity=min(1.0, current.adoption_rate / config.viral_cascade_threshold),
                    description=(
                        f"Viral cascade detected: {current.adoption_rate:.1%} adoption "
                        f"at step {current.step}"
                    ),
                    affected_agent_ids=current.adopted_agent_ids,
                )
            return None

        prev = history[-1]
        delta = current.adoption_rate - prev.adoption_rate

        if delta >= config.viral_cascade_threshold:
            return EmergentEvent(
                event_type="viral_cascade",
                step=current.step,
                community_id=None,
                severity=min(1.0, delta / config.viral_cascade_threshold),
                description=(
                    f"Viral cascade detected: {delta:.1%} adoption increase "
                    f"at step {current.step}"
                ),
                affected_agent_ids=current.adopted_agent_ids,
            )
        return None

    def _check_slow_adoption(
        self,
        current: StepResult,
        history: list[StepResult],
        config: CascadeConfig,
    ) -> EmergentEvent | None:
        """Slow adoption: N steps below threshold (fires once, resets on recovery).

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#cascadedetector
        """
        # Need enough history
        window = config.slow_adoption_steps
        all_steps = history + [current]

        if len(all_steps) < window:
            logger.debug(
                "Not enough steps (%d < %d) for slow adoption detection",
                len(all_steps), window,
            )
            return None

        recent = all_steps[-window:]

        # Check if all recent steps have low adoption rate change
        slow = True
        for i in range(1, len(recent)):
            delta = recent[i].adoption_rate - recent[i - 1].adoption_rate
            if delta >= config.slow_adoption_threshold:
                slow = False
                break

        if not slow:
            # Adoption recovering — reset one-shot guard
            self._slow_adoption_fired = False
            return None

        # Only fire once per slow-adoption episode (False → True transition)
        if self._slow_adoption_fired:
            return None

        self._slow_adoption_fired = True
        return EmergentEvent(
            event_type="slow_adoption",
            step=current.step,
            community_id=None,
            severity=0.3,
            description=(
                f"Slow adoption: adoption rate below threshold "
                f"for {window} consecutive steps"
            ),
            affected_agent_ids=[],
        )

    def _check_polarization(
        self,
        current: StepResult,
        config: CascadeConfig,
    ) -> EmergentEvent | None:
        """Polarization: variance > threshold.

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#cascadedetector
        SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#6.5
        """
        # Collect ALL polarized communities (P6 fix — was return-on-first)
        polarized: list[tuple] = []
        for community_id, variance in current.community_variances.items():
            if variance > config.polarization_variance_threshold:
                polarized.append((community_id, variance))
        if polarized:
            max_var = max(v for _, v in polarized)
            cids = ", ".join(str(cid) for cid, _ in polarized)
            return EmergentEvent(
                event_type="polarization",
                step=current.step,
                community_id=polarized[0][0],
                severity=min(1.0, max_var),
                description=(
                    f"Polarization in {len(polarized)} community(ies) [{cids}]: "
                    f"max variance={max_var:.3f}"
                ),
                affected_agent_ids=current.adopted_agent_ids,
            )
        return None

    def _check_collapse(
        self,
        current: StepResult,
        history: list[StepResult],
        config: CascadeConfig,
    ) -> EmergentEvent | None:
        """Collapse: 20% drop in 3 steps.

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#cascadedetector
        """
        all_steps = history + [current]
        if len(all_steps) < 3:
            return None

        recent_3 = all_steps[-3:]
        start_rate = recent_3[0].adoption_rate
        end_rate = recent_3[-1].adoption_rate

        if start_rate <= 0:
            return None

        drop = (start_rate - end_rate) / start_rate

        if drop >= config.collapse_drop_rate:
            return EmergentEvent(
                event_type="collapse",
                step=current.step,
                community_id=None,
                severity=min(1.0, drop),
                description=(
                    f"Collapse detected: {drop:.1%} adoption drop over 3 steps"
                ),
                affected_agent_ids=current.adopted_agent_ids,
            )
        return None

    def _check_echo_chamber(
        self,
        current: StepResult,
        config: CascadeConfig,
    ) -> EmergentEvent | None:
        """Echo chamber: internal/external ratio > threshold.

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#cascadedetector
        SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#6.5
        """
        # Collect ALL echo chamber communities (P6 fix — was return-on-first)
        echo_chambers: list[tuple] = []
        for community_id in current.internal_links:
            internal = current.internal_links.get(community_id, 0)
            external = current.external_links.get(community_id, 0)

            if external == 0:
                if internal > 0:
                    ratio = float("inf")
                else:
                    continue
            else:
                ratio = internal / external

            if ratio > config.echo_chamber_ratio:
                echo_chambers.append((community_id, ratio))

        if echo_chambers:
            max_ratio = max(r for _, r in echo_chambers)
            cids = ", ".join(str(cid) for cid, _ in echo_chambers)
            return EmergentEvent(
                event_type="echo_chamber",
                step=current.step,
                community_id=echo_chambers[0][0],
                severity=min(1.0, max_ratio / (config.echo_chamber_ratio * 2)),
                description=(
                    f"Echo chamber in {len(echo_chambers)} community(ies) [{cids}]: "
                    f"max ratio={max_ratio:.1f}"
                ),
                affected_agent_ids=[],
            )
        return None


__all__ = ["CascadeDetector", "StepResult"]
