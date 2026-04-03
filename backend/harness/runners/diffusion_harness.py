"""F18 Unit Test Hooks — Diffusion Harness.
SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks
"""
from uuid import UUID, uuid4

from app.engine.agent.schema import AgentState
from app.engine.diffusion.exposure_model import ExposureModel
from app.engine.diffusion.cascade_detector import CascadeDetector, StepResult as CascadeStepResult
from app.engine.diffusion.schema import CampaignEvent, RecSysConfig
from app.engine.network.schema import SocialNetwork
from app.engine.simulation.schema import CampaignConfig, StepResult


def _campaign_config_to_event(
    campaign: CampaignConfig,
    agents: list[AgentState],
    step: int,
) -> list[CampaignEvent]:
    """Convert a CampaignConfig into CampaignEvent list for a given step."""
    end_step = campaign.end_step if campaign.end_step is not None else step + 1
    if step < campaign.start_step or step > end_step:
        return []

    all_community_ids = list({a.community_id for a in agents})
    if "all" in campaign.target_communities:
        target_ids = all_community_ids
    else:
        target_ids = [
            cid for cid in all_community_ids
            if str(cid) in campaign.target_communities
        ] or all_community_ids

    campaign_id = UUID(int=hash(campaign.name) % (2**128))
    return [
        CampaignEvent(
            campaign_id=campaign_id,
            name=campaign.name,
            message=campaign.message,
            channels=campaign.channels,
            novelty=campaign.novelty,
            controversy=campaign.controversy,
            utility=campaign.utility,
            budget=campaign.budget,
            target_communities=target_ids,
            start_step=campaign.start_step,
            end_step=end_step,
        )
    ]


class DiffusionHarness:
    """Per-layer test entry point for Diffusion engine.

    SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks
    """

    def run_single_step(
        self,
        agents: list[AgentState],
        network: SocialNetwork,
        campaign: CampaignConfig,
    ) -> StepResult:
        """Run one diffusion step in isolation.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f18-unit-test-hooks

        Computes exposure results and cascade detection for the given agents,
        network, and campaign without running the full simulation orchestrator.
        """
        if not agents:
            raise ValueError("agents list must not be empty")

        sim_id = agents[0].simulation_id
        step = 0

        # Build campaign events for this step
        active_events = _campaign_config_to_event(campaign, agents, step)

        # Run exposure model
        exposure_model = ExposureModel(recsys_config=RecSysConfig())
        exposure_results = exposure_model.compute_exposure(
            agents=agents,
            graph=network,
            active_events=active_events,
            step=step,
        )

        # Compute aggregate metrics
        adopted = [a for a in agents if a.adopted]
        adoption_rate = len(adopted) / len(agents) if agents else 0.0
        total_adoption = len(adopted)

        beliefs = [a.belief for a in agents]
        mean_sentiment = sum(beliefs) / len(beliefs) if beliefs else 0.0

        # Run cascade detection
        detector = CascadeDetector()
        cascade_step = CascadeStepResult(
            step=step,
            total_agents=len(agents),
            adopted_count=total_adoption,
            adoption_rate=adoption_rate,
            community_sentiments={},
            community_variances={},
            community_adoption_rates={},
            internal_links={},
            external_links={},
            adopted_agent_ids=[a.agent_id for a in adopted],
        )
        emergent_events = detector.detect(step_results=cascade_step, history=[])

        return StepResult(
            simulation_id=sim_id,
            step=step,
            total_adoption=total_adoption,
            adoption_rate=adoption_rate,
            diffusion_rate=adoption_rate,
            mean_sentiment=mean_sentiment,
            sentiment_variance=0.0,
            community_metrics={},
            emergent_events=emergent_events,
            action_distribution={},
            llm_calls_this_step=0,
            llm_tier_distribution={},
            step_duration_ms=0.0,
        )


__all__ = ["DiffusionHarness"]
