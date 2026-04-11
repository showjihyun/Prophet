"""Expert intervention engine — generates expert opinions via rule-based + LLM.
SPEC: docs/spec/01_AGENT_SPEC.md#expert-agents
SPEC: docs/spec/23_EXPERT_LLM_SPEC.md
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from uuid import UUID

from app.engine.agent.schema import AgentState, AgentType
from app.engine.diffusion.schema import ExpertOpinion

logger = logging.getLogger(__name__)


@dataclass
class ExpertInterventionEngine:
    """Generates expert opinions for EXPERT-type agents.

    SPEC: docs/spec/01_AGENT_SPEC.md#expert-agents
    SPEC: docs/spec/23_EXPERT_LLM_SPEC.md

    Dual-mode:
    - Heuristic (sync): score = belief * skepticism
    - LLM (async): structured reasoning via gateway for Tier 3
    """

    def generate_expert_opinion(
        self,
        agent: AgentState,
        campaign: object,  # CampaignConfig or CampaignEvent — used for community list
        step: int,
    ) -> ExpertOpinion | None:
        """Generate an expert opinion for an EXPERT agent.

        SPEC: docs/spec/01_AGENT_SPEC.md#expert-agents

        Args:
            agent:    The agent state (must be AgentType.EXPERT).
            campaign: Campaign context (provides community targeting info).
            step:     Current simulation step.

        Returns:
            ExpertOpinion dataclass, or None if the agent is not an expert.
        """
        if agent.agent_type != AgentType.EXPERT:
            logger.debug(
                "generate_expert_opinion: agent %s is not EXPERT (type=%s), skipping",
                agent.agent_id,
                agent.agent_type,
            )
            return None

        score = agent.belief * agent.personality.skepticism
        confidence = abs(score)

        # Determine affected communities from campaign if possible
        affects_communities: list[UUID] = []
        if hasattr(campaign, "target_communities"):
            raw = campaign.target_communities  # list[UUID] or list[str]
            for c in raw:
                if isinstance(c, UUID):
                    affects_communities.append(c)
                else:
                    try:
                        affects_communities.append(UUID(str(c)))
                    except (ValueError, AttributeError):
                        pass  # non-UUID community key; skip

        # Fallback: include the expert's own community
        if not affects_communities:
            affects_communities = [agent.community_id]

        reasoning = (
            f"Expert assessment at step {step}: "
            f"belief={agent.belief:.3f}, skepticism={agent.personality.skepticism:.3f}, "
            f"score={score:.3f}"
        )

        opinion = ExpertOpinion(
            expert_agent_id=agent.agent_id,
            score=score,
            reasoning=reasoning,
            step=step,
            affects_communities=affects_communities,
            confidence=confidence,
        )

        logger.debug(
            "Expert opinion generated: agent=%s score=%.4f confidence=%.4f",
            agent.agent_id,
            score,
            confidence,
        )

        return opinion

    async def generate_expert_opinion_async(
        self,
        agent: AgentState,
        campaign: object,
        step: int,
        gateway: object | None = None,
    ) -> ExpertOpinion | None:
        """Generate expert opinion using LLM for Tier 3, heuristic fallback.

        SPEC: docs/spec/23_EXPERT_LLM_SPEC.md#EX-01

        Args:
            agent:    Agent state (must be AgentType.EXPERT).
            campaign: Campaign context.
            step:     Current simulation step.
            gateway:  LLMGateway for Tier 3 LLM calls. If None, uses heuristic.

        Returns:
            ExpertOpinion or None if agent is not EXPERT.
        """
        if agent.agent_type != AgentType.EXPERT:
            return None

        # Heuristic baseline
        heuristic_score = agent.belief * agent.personality.skepticism
        heuristic_confidence = abs(heuristic_score)

        # Determine affected communities
        affects_communities: list[UUID] = []
        if hasattr(campaign, "target_communities"):
            raw = campaign.target_communities
            for c in raw:
                if isinstance(c, UUID):
                    affects_communities.append(c)
                else:
                    try:
                        affects_communities.append(UUID(str(c)))
                    except (ValueError, AttributeError):
                        pass
        if not affects_communities:
            affects_communities = [agent.community_id]

        # LLM path: use gateway if available
        if gateway is not None:
            try:
                llm_result = await self._call_llm_expert(agent, campaign, step, gateway)
                if llm_result is not None:
                    score, reasoning, confidence = llm_result
                    return ExpertOpinion(
                        expert_agent_id=agent.agent_id,
                        score=score,
                        reasoning=reasoning,
                        step=step,
                        affects_communities=affects_communities,
                        confidence=confidence,
                    )
            except Exception:
                logger.warning(
                    "LLM expert opinion failed for agent %s, falling back to heuristic",
                    agent.agent_id,
                )

        # Fallback: heuristic (same as sync path)
        reasoning = (
            f"Expert assessment at step {step}: "
            f"belief={agent.belief:.3f}, skepticism={agent.personality.skepticism:.3f}, "
            f"score={heuristic_score:.3f}"
        )
        return ExpertOpinion(
            expert_agent_id=agent.agent_id,
            score=heuristic_score,
            reasoning=reasoning,
            step=step,
            affects_communities=affects_communities,
            confidence=heuristic_confidence,
        )

    async def _call_llm_expert(
        self,
        agent: AgentState,
        campaign: object,
        step: int,
        gateway: object,
    ) -> tuple[float, str, float] | None:
        """Call LLM gateway for expert opinion and parse response.

        SPEC: docs/spec/23_EXPERT_LLM_SPEC.md#EX-02

        Returns (score, reasoning, confidence) or None on failure.
        """
        from app.llm.prompt_builder import PromptBuilder

        builder = PromptBuilder()

        # Build a compact expert opinion prompt
        campaign_message = getattr(campaign, "message", str(campaign))
        prompt = builder.build_expert_analysis_prompt(
            expert=agent,
            campaign=campaign,
            sentiment=type("S", (), {"mean_belief": agent.belief, "adoption_rate": 0.0})(),
            memories=[],
        )

        response = await gateway.complete(prompt, tier=3)
        if response is None or not hasattr(response, "text"):
            return None

        return self._parse_llm_response(response.text, agent)

    @staticmethod
    def _parse_llm_response(
        text: str,
        agent: AgentState,
    ) -> tuple[float, str, float] | None:
        """Parse LLM response into (score, reasoning, confidence).

        SPEC: docs/spec/23_EXPERT_LLM_SPEC.md#EX-02

        Expected formats:
        1. JSON: {"score": float, "reasoning": str, "confidence": float}
        2. Text: "SCORE: float\\nREASONING: text"
        """
        if not text or not text.strip():
            return None

        # Try JSON parsing first
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                score = float(data.get("score", 0.0))
                score = max(-1.0, min(1.0, score))
                reasoning = str(data.get("reasoning", ""))
                confidence = float(data.get("confidence", abs(score)))
                confidence = max(0.0, min(1.0, confidence))
                return (score, reasoning, confidence)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # Try SCORE:/REASONING: format
        score_match = re.search(r"SCORE:\s*([+-]?\d+\.?\d*)", text, re.IGNORECASE)
        if score_match:
            score = max(-1.0, min(1.0, float(score_match.group(1))))
            reasoning_match = re.search(r"REASONING:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
            reasoning = reasoning_match.group(1).strip() if reasoning_match else text
            confidence = abs(score)
            return (score, reasoning, confidence)

        # Fallback: use heuristic score with raw LLM text as reasoning
        heuristic_score = agent.belief * agent.personality.skepticism
        return (heuristic_score, text.strip()[:500], abs(heuristic_score))


__all__ = ["ExpertInterventionEngine"]
