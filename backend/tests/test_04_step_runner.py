"""
Auto-generated from SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
SPEC Version: 0.1.1
Interface tests for StepRunner.
"""
import pytest
from uuid import uuid4

from app.engine.network.schema import CommunityConfig
from app.engine.simulation.schema import (
    SimulationConfig,
    CampaignConfig,
    StepResult,
)
from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.engine.simulation.step_runner import StepRunner


def _make_config(seed=42, max_steps=5) -> SimulationConfig:
    return SimulationConfig(
        simulation_id=uuid4(),
        communities=[
            CommunityConfig(id="c0", name="Comm0", size=30, agent_type="consumer"),
            CommunityConfig(id="c1", name="Comm1", size=30, agent_type="consumer"),
        ],
        campaign=CampaignConfig(name="test", message="test msg"),
        max_steps=max_steps,
        random_seed=seed,
        enable_dynamic_edges=False,
    )


@pytest.mark.phase6
class TestStepRunner:
    """SPEC: 04_SIMULATION_SPEC.md — StepRunner.execute_step"""

    @pytest.mark.asyncio
    async def test_execute_step_returns_step_result(self):
        """execute_step returns StepResult."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        runner = StepRunner()
        result = await runner.execute_step(state, 0)
        assert isinstance(result, StepResult)

    @pytest.mark.asyncio
    async def test_step_result_has_required_fields(self):
        """StepResult has all required fields."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        runner = StepRunner()
        result = await runner.execute_step(state, 0)

        assert result.simulation_id == state.simulation_id
        assert result.step == 0
        assert isinstance(result.total_adoption, int)
        assert isinstance(result.adoption_rate, float)
        assert isinstance(result.diffusion_rate, float)
        assert isinstance(result.mean_sentiment, float)
        assert isinstance(result.sentiment_variance, float)
        assert isinstance(result.community_metrics, dict)
        assert isinstance(result.emergent_events, list)
        assert isinstance(result.action_distribution, dict)
        assert isinstance(result.llm_calls_this_step, int)
        assert isinstance(result.llm_tier_distribution, dict)
        assert result.step_duration_ms > 0

    @pytest.mark.asyncio
    async def test_adoption_rate_in_range(self):
        """adoption_rate should be in [0, 1]."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        runner = StepRunner()
        result = await runner.execute_step(state, 0)
        assert 0.0 <= result.adoption_rate <= 1.0

    @pytest.mark.asyncio
    async def test_action_distribution_sums_to_agent_count(self):
        """Action distribution values should sum to total agents."""
        orch = SimulationOrchestrator()
        config = _make_config()
        state = orch.create_simulation(config)
        runner = StepRunner()
        result = await runner.execute_step(state, 0)
        total = sum(result.action_distribution.values())
        assert total == len(state.agents)

    @pytest.mark.asyncio
    async def test_community_metrics_populated(self):
        """Community metrics should be populated for each community."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        runner = StepRunner()
        result = await runner.execute_step(state, 0)
        assert len(result.community_metrics) > 0

    @pytest.mark.asyncio
    async def test_agents_updated_after_step(self):
        """Agent states should be updated after a step."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        runner = StepRunner()
        await runner.execute_step(state, 0)
        # Agents should have step=1 after execution
        for agent in state.agents:
            assert agent.step == 1

    @pytest.mark.asyncio
    async def test_multiple_steps_sequential(self):
        """Multiple sequential steps should work correctly."""
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        runner = StepRunner()

        results = []
        for step in range(3):
            result = await runner.execute_step(state, step)
            results.append(result)
            state.step_history.append(result)
            state.current_step = step + 1

        assert len(results) == 3
        assert results[0].step == 0
        assert results[1].step == 1
        assert results[2].step == 2

    @pytest.mark.asyncio
    async def test_injected_events_consumed(self):
        """Injected events should be consumed during step execution."""
        from app.engine.agent.perception import EnvironmentEvent
        orch = SimulationOrchestrator()
        state = orch.create_simulation(_make_config())
        state.injected_events.append(
            EnvironmentEvent(
                event_type="campaign_ad",
                content_id=uuid4(),
                message="injected event",
                source_agent_id=None,
                channel="direct",
                timestamp=0,
            )
        )
        runner = StepRunner()
        await runner.execute_step(state, 0)
        assert len(state.injected_events) == 0


@pytest.mark.phase6
class TestCampaignFramingAffectsOutcome:
    """SPEC: docs/spec/26_DIFFUSION_CALIBRATION_SPEC.md (Round 8-6)

    Regression test for the pre-Round-8-6 wire gap where
    ``CampaignConfig.{novelty, utility, controversy}`` were silently
    dropped before reaching ``AgentTick.tick()``. When the bug was
    present, two simulations with identical seeds + populations but
    radically different campaign framings produced *identical*
    step-by-step trajectories. Today's assertion:

        "Two sims with the same seed and population but opposite
        campaign framings must produce measurably different adoption
        curves by step 4."

    If this test ever goes green again with ``abs(delta) < 0.02``,
    something in the campaign → tick wire has regressed.
    """

    def _config(
        self,
        *,
        novelty: float,
        utility: float,
        controversy: float,
        seed: int = 1234,
    ) -> SimulationConfig:
        return SimulationConfig(
            simulation_id=uuid4(),
            communities=[
                CommunityConfig(
                    id="early", name="early_adopters",
                    size=60, agent_type="early_adopter",
                ),
                CommunityConfig(
                    id="main", name="mainstream",
                    size=120, agent_type="consumer",
                ),
                CommunityConfig(
                    id="skeptic", name="skeptics",
                    size=40, agent_type="skeptic",
                ),
            ],
            campaign=CampaignConfig(
                name="test",
                message="test msg",
                novelty=novelty,
                utility=utility,
                controversy=controversy,
            ),
            max_steps=6,
            random_seed=seed,
            enable_dynamic_edges=False,
        )

    async def _run_n_steps(self, config: SimulationConfig, n: int) -> list:
        orch = SimulationOrchestrator()
        state = orch.create_simulation(config)
        runner = StepRunner()
        results = []
        for step in range(n):
            result = await runner.execute_step(state, step)
            results.append(result)
            state.step_history.append(result)
            state.current_step = step + 1
        return results

    @pytest.mark.asyncio
    async def test_campaign_framing_changes_adoption_curve(self):
        """Friendly framing (low controversy, high utility/novelty) must
        produce meaningfully different adoption than hostile framing
        (high controversy, low utility/novelty) when everything else is
        held constant. This regression test caught the pre-8-6 bug where
        campaign attrs were silently ignored."""
        friendly = await self._run_n_steps(
            self._config(novelty=0.85, utility=0.85, controversy=0.15),
            n=5,
        )
        hostile = await self._run_n_steps(
            self._config(novelty=0.15, utility=0.15, controversy=0.85),
            n=5,
        )

        # Seed is identical; without the wire fix the trajectories
        # were bit-identical through step 4.
        adopt_friendly = friendly[-1].adoption_rate
        adopt_hostile = hostile[-1].adoption_rate
        delta = adopt_friendly - adopt_hostile
        assert abs(delta) >= 0.02, (
            f"Campaign framing had no measurable effect: friendly="
            f"{adopt_friendly:.4f} vs hostile={adopt_hostile:.4f} "
            f"(delta={delta:+.4f}). Check that campaign.novelty/"
            f"utility/controversy are being passed through "
            f"step_runner → community_orchestrator → AgentTick.tick()."
        )
        # Friendly framing should beat hostile framing (not just differ).
        assert delta > 0, (
            f"Friendly framing produced LOWER adoption than hostile "
            f"({adopt_friendly:.4f} vs {adopt_hostile:.4f}). The "
            f"MessageStrength formula is inverted or the blend weights "
            f"are wrong."
        )
