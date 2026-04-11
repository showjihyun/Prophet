"""Community Opinion synthesis service.

SPEC: docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis

Round 8: turns raw simulation numbers (`adoption_rate=0.62`,
`sentiment_variance=0.41`, etc.) into a structured natural-language
narrative explaining "what is happening in this community and why".

Architecture:
  * Pulls evidence from in-memory orchestrator state + step history
  * Builds an anti-hallucination prompt with explicit evidence-only rules
  * Calls Tier-3 EliteLLM via the existing ``LLMGateway``
  * Persists the result so the frontend can re-render without paying for
    a fresh LLM call. Cache key = ``(simulation_id, community_id, step)``
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.llm.gateway import LLMGateway
from app.llm.schema import LLMOptions, LLMPrompt
from app.models.community_opinion import CommunityOpinion
from app.services.ports import SimulationNotFoundError

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# DTOs                                                                         #
# --------------------------------------------------------------------------- #


@dataclass
class CommunityOpinionSnapshot:
    """Read-side projection of a persisted CommunityOpinion row."""

    opinion_id: UUID
    simulation_id: UUID
    community_id: str
    step: int
    summary: str
    sentiment_trend: str
    themes: list[dict]
    divisions: list[dict]
    dominant_emotions: list[str]
    key_quotes: list[dict]
    source_step_count: int
    source_agent_count: int
    llm_provider: str
    llm_model: str
    llm_cost_usd: float
    is_fallback_stub: bool

    @classmethod
    def from_row(cls, row: CommunityOpinion) -> "CommunityOpinionSnapshot":
        return cls(
            opinion_id=row.opinion_id,
            simulation_id=row.simulation_id,
            community_id=row.community_id,
            step=row.step,
            summary=row.summary,
            sentiment_trend=row.sentiment_trend,
            themes=row.themes or [],
            divisions=row.divisions or [],
            dominant_emotions=row.dominant_emotions or [],
            key_quotes=row.key_quotes or [],
            source_step_count=row.source_step_count,
            source_agent_count=row.source_agent_count,
            llm_provider=row.llm_provider,
            llm_model=row.llm_model,
            llm_cost_usd=row.llm_cost_usd,
            is_fallback_stub=row.is_fallback_stub,
        )


# --------------------------------------------------------------------------- #
# Prompt builder (pure function, easy to unit-test)                            #
# --------------------------------------------------------------------------- #


SYSTEM_PROMPT = (
    "You are a research analyst synthesising the collective opinion of a "
    "community in an agent-based social simulation. Your job is to identify "
    "themes, divisions, and dominant sentiment WITHOUT inventing facts.\n\n"
    "CRITICAL RULES\n"
    "1. Only describe what's in the data provided. Never invent quotes or "
    "agent_ids that are not in the input.\n"
    "2. Cite step numbers in your narrative when referring to events.\n"
    "3. If the data is insufficient, say so in the summary instead of "
    "fabricating.\n"
    "4. Output must be valid JSON matching the schema. No prose outside JSON.\n"
)


OVERALL_SYSTEM_PROMPT = (
    "You are a senior research analyst synthesising a CROSS-COMMUNITY "
    "overview of an agent-based social simulation. You are given one "
    "short opinion blurb per community plus aggregate metrics. Your job "
    "is to explain how the campaign played out ACROSS communities — "
    "which cohorts drove adoption, which resisted, and what divisions "
    "emerged between them.\n\n"
    "CRITICAL RULES\n"
    "1. Base every claim on the per-community data provided. Do not "
    "invent community names, factions, or quotes.\n"
    "2. Name specific community_ids when attributing behaviour.\n"
    "3. If communities behave identically, say so honestly — do not "
    "fabricate conflict for narrative effect.\n"
    "4. Output must be valid JSON matching the schema. No prose outside JSON.\n"
)


# Sentinel community_id used to persist the cross-community aggregate
# row in the shared ``community_opinions`` table. The ``__`` prefix
# makes it impossible to collide with real community ids (which are
# UUIDs or short slugs like "S"/"M").
OVERALL_COMMUNITY_ID = "__overall__"


def build_opinion_prompt(
    *,
    community_id: str,
    community_size: int,
    step_metrics_table: str,
    agent_summaries: list[dict],
    dominant_action_breakdown: dict[str, int],
    first_step: int,
    last_step: int,
) -> LLMPrompt:
    """Build the LLM prompt for one community-opinion synthesis call.

    Pure function — no DB / network access. Easy to unit-test.
    """
    agent_block = "\n".join(
        f"  - agent={a['agent_id'][:8]} type={a.get('agent_type', '?')} "
        f"belief={a['belief']:.2f} adopted={a['adopted']} "
        f"action={a.get('action', '?')}"
        for a in agent_summaries[:10]
    ) or "  (no agent samples)"

    action_block = ", ".join(
        f"{a}={c}" for a, c in dominant_action_breakdown.items()
    ) or "(none)"

    user = (
        f"## Community: {community_id} ({community_size} agents)\n"
        f"## Steps analysed: {first_step} → {last_step}\n\n"
        f"## Per-step trend\n{step_metrics_table}\n\n"
        f"## Representative agents (top {min(10, len(agent_summaries))} by influence)\n"
        f"{agent_block}\n\n"
        f"## Dominant action distribution last step\n{action_block}\n\n"
        f"## Task — output JSON only matching this schema:\n"
        '{\n'
        '  "summary": "one or two sentences",\n'
        '  "themes": [{"theme": "...", "weight": 0.0-1.0, "evidence_step": int}],\n'
        '  "divisions": [{"faction": "...", "share": 0.0-1.0, "concerns": ["..."]}],\n'
        '  "sentiment_trend": "rising|stable|polarising|collapsing",\n'
        '  "dominant_emotions": ["..."],\n'
        '  "key_quotes": [{"agent_id": "uuid", "content": "...", "step": int}]\n'
        '}\n'
    )

    return LLMPrompt(
        system=SYSTEM_PROMPT,
        user=user,
        context={"community_id": community_id, "step_range": [first_step, last_step]},
        response_format="json",
        max_tokens=1024,
    )


def build_overall_prompt(
    *,
    simulation_name: str,
    total_agents: int,
    community_briefs: list[dict],
    aggregate_metrics: dict,
    first_step: int,
    last_step: int,
) -> LLMPrompt:
    """Build the cross-community aggregate prompt.

    Pure function — no DB / network access. Takes one short "brief"
    per community (already synthesised or summarised) plus simulation
    totals, and asks the LLM for a narrative explaining how the
    campaign propagated across the communities as a whole.
    """
    briefs_block = "\n".join(
        f"  - [{b['community_id']}] size={b.get('size', '?')} "
        f"adoption={b.get('adoption_rate', 0):.2%} "
        f"sentiment={b.get('mean_belief', 0):+.2f} "
        f"trend={b.get('sentiment_trend', 'unknown')}\n"
        f"    summary: {b.get('summary', '(no per-community summary yet)')}"
        for b in community_briefs
    ) or "  (no community data)"

    metrics_block = (
        f"adoption={aggregate_metrics.get('adoption_rate', 0):.2%}, "
        f"mean_sentiment={aggregate_metrics.get('mean_sentiment', 0):+.2f}, "
        f"sentiment_variance={aggregate_metrics.get('sentiment_variance', 0):.2f}, "
        f"diffusion_rate={aggregate_metrics.get('diffusion_rate', 0):.2%}"
    )

    user = (
        f"## Simulation: {simulation_name} ({total_agents} agents across "
        f"{len(community_briefs)} communities)\n"
        f"## Steps analysed: {first_step} → {last_step}\n\n"
        f"## Aggregate metrics last step\n{metrics_block}\n\n"
        f"## Per-community briefs\n{briefs_block}\n\n"
        f"## Task — output JSON only matching this schema:\n"
        '{\n'
        '  "summary": "two or three sentences — the headline cross-community story",\n'
        '  "themes": [{"theme": "...", "weight": 0.0-1.0, "evidence_step": int}],\n'
        '  "divisions": [{"faction": "community_id_or_coalition", "share": 0.0-1.0, "concerns": ["..."]}],\n'
        '  "sentiment_trend": "rising|stable|polarising|collapsing",\n'
        '  "dominant_emotions": ["..."],\n'
        '  "key_quotes": []\n'
        '}\n'
        "\n"
        "Guidance: use the 'divisions' array to contrast communities "
        "(e.g. {\"faction\": \"early_adopters\", \"share\": 0.42, "
        "\"concerns\": [...]}). Use 'themes' for cross-community "
        "dynamics (e.g. 'rapid cascade in early_adopters stalls "
        "against skeptic resistance')."
    )

    return LLMPrompt(
        system=OVERALL_SYSTEM_PROMPT,
        user=user,
        context={
            "scope": "overall",
            "community_count": len(community_briefs),
            "step_range": [first_step, last_step],
        },
        response_format="json",
        max_tokens=1536,
    )


# --------------------------------------------------------------------------- #
# Service                                                                      #
# --------------------------------------------------------------------------- #


class CommunityOpinionService:
    """Application service for synthesising community opinions.

    Cache strategy: re-uses the persisted ``community_opinions`` row when
    one already exists for the same ``(sim_id, community_id, step)``. This
    means a user clicking "Analyse" twice on the same simulation step pays
    only once for the LLM call.
    """

    def __init__(
        self,
        orchestrator: SimulationOrchestrator,
        gateway: LLMGateway,
    ) -> None:
        self._orch = orchestrator
        self._gateway = gateway

    async def get_or_synthesize(
        self,
        sim_id: UUID,
        community_id: str,
        *,
        session: AsyncSession,
    ) -> CommunityOpinionSnapshot:
        """Return a cached snapshot if one exists for the current step,
        otherwise synthesise a fresh one and persist it."""
        try:
            state = self._orch.get_state(sim_id)
        except (KeyError, ValueError) as exc:
            raise SimulationNotFoundError(sim_id) from exc

        current_step = state.current_step

        # Cache hit?
        cached = await self._find_cached(
            sim_id, community_id, current_step, session=session,
        )
        if cached is not None:
            logger.debug(
                "community-opinion cache hit sim=%s comm=%s step=%d",
                sim_id, community_id, current_step,
            )
            return CommunityOpinionSnapshot.from_row(cached)

        # Build evidence pack from in-memory state
        evidence = self._collect_evidence(state, community_id)
        if evidence is None:
            raise ValueError(
                f"Community {community_id!r} has no agents in simulation {sim_id}"
            )

        prompt = build_opinion_prompt(
            community_id=community_id,
            community_size=evidence["community_size"],
            step_metrics_table=evidence["step_metrics_table"],
            agent_summaries=evidence["agent_summaries"],
            dominant_action_breakdown=evidence["dominant_actions"],
            first_step=evidence["first_step"],
            last_step=evidence["last_step"],
        )

        response = await self._gateway.call(
            prompt,
            task_type="community_opinion",
            tier=3,
            options=LLMOptions(temperature=0.2, timeout_seconds=30.0),
        )

        parsed = self._parse_response(response.parsed, response.content)

        row = CommunityOpinion(
            opinion_id=uuid.uuid4(),
            simulation_id=sim_id,
            community_id=community_id,
            step=current_step,
            themes=parsed.get("themes", []),
            divisions=parsed.get("divisions", []),
            sentiment_trend=parsed.get("sentiment_trend", "stable"),
            dominant_emotions=parsed.get("dominant_emotions", []),
            key_quotes=parsed.get("key_quotes", []),
            summary=parsed.get("summary", ""),
            source_step_count=evidence["source_step_count"],
            source_agent_count=evidence["source_agent_count"],
            llm_provider=response.provider,
            llm_model=response.model,
            llm_cost_usd=0.0,
            is_fallback_stub=response.is_fallback_stub,
        )
        # ``_persist_row_with_retry`` returns either the row we just
        # inserted OR a pre-existing row that another writer won a
        # race for. Either way, the snapshot is the canonical answer.
        persisted = await self._persist_row_with_retry(row, session)
        return CommunityOpinionSnapshot.from_row(persisted)

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    async def _find_cached(
        self,
        sim_id: UUID,
        community_id: str,
        step: int,
        *,
        session: AsyncSession,
    ) -> CommunityOpinion | None:
        result = await session.execute(
            select(CommunityOpinion)
            .where(
                CommunityOpinion.simulation_id == sim_id,
                CommunityOpinion.community_id == community_id,
                CommunityOpinion.step == step,
            )
            .order_by(CommunityOpinion.created_at.desc())
            .limit(1),
        )
        return result.scalar_one_or_none()

    def _collect_evidence(
        self, state: Any, community_id: str,
    ) -> dict[str, Any] | None:
        """Build the evidence pack the LLM prompt needs.

        Pulls a small slice of orchestrator state — recent step history,
        a sample of agents in the community, and dominant actions. Kept
        small (~5 steps × 10 agents) so the prompt fits comfortably in
        any Tier-3 model's context window.
        """
        if state is None or not state.agents:
            return None

        # Filter agents in the requested community
        community_agents = [
            a for a in state.agents if str(a.community_id) == community_id
        ]
        # Fall back: try matching against the human-readable community key
        # if community_id was passed as a slug like "S" or "M".
        if not community_agents and state.config.communities:
            cfg = next(
                (c for c in state.config.communities if c.id == community_id),
                None,
            )
            if cfg is not None:
                community_agents = [
                    a for a in state.agents
                    if hasattr(a, "community_id") and str(a.community_id).startswith(cfg.id)
                ]

        if not community_agents:
            return None

        # Sort by influence_score for representative sampling
        sample = sorted(
            community_agents,
            key=lambda a: getattr(a, "influence_score", 0.0),
            reverse=True,
        )[:10]

        agent_summaries = [
            {
                "agent_id": str(a.agent_id),
                "agent_type": getattr(a.agent_type, "value", str(a.agent_type)),
                "belief": float(a.belief),
                "adopted": bool(a.adopted),
                "action": getattr(a.action, "value", str(a.action)),
            }
            for a in sample
        ]

        dominant_actions: dict[str, int] = {}
        for a in community_agents:
            key = getattr(a.action, "value", str(a.action))
            dominant_actions[key] = dominant_actions.get(key, 0) + 1

        # Step metrics table — last 5 steps for the community
        recent_steps = state.step_history[-5:] if state.step_history else []
        rows = ["step | adoption | belief | dominant"]
        for s in recent_steps:
            metrics = (s.community_metrics or {}).get(community_id)
            if metrics is None:
                # Try to find by uuid match
                for cid, m in (s.community_metrics or {}).items():
                    if str(cid).startswith(community_id):
                        metrics = m
                        break
            if metrics is None:
                continue
            ad = getattr(metrics, "adoption_rate", None) or (
                metrics.get("adoption_rate") if isinstance(metrics, dict) else 0.0
            )
            bel = getattr(metrics, "mean_belief", None) or (
                metrics.get("mean_belief") if isinstance(metrics, dict) else 0.0
            )
            dom = getattr(metrics, "dominant_action", None) or (
                metrics.get("dominant_action") if isinstance(metrics, dict) else "?"
            )
            rows.append(f"{s.step:>4} | {ad:.4f}  | {bel:.3f}  | {dom}")
        if len(rows) == 1:
            rows.append("(no per-step community metrics yet)")

        return {
            "community_size": len(community_agents),
            "step_metrics_table": "\n".join(rows),
            "agent_summaries": agent_summaries,
            "dominant_actions": dominant_actions,
            "first_step": recent_steps[0].step if recent_steps else 0,
            "last_step": recent_steps[-1].step if recent_steps else 0,
            "source_step_count": len(recent_steps),
            "source_agent_count": len(community_agents),
        }

    @staticmethod
    def _parse_response(
        parsed: dict[str, Any] | None, raw_content: str,
    ) -> dict[str, Any]:
        """Best-effort JSON parse + field normalisation.

        Smaller LLMs (llama3.2:1b, phi3:mini) frequently echo the
        prompt schema instead of picking a value — e.g. returning
        ``"rising|stable|polarising|collapsing"`` verbatim in the
        ``sentiment_trend`` field, which then blows past the
        ``VARCHAR(32)`` column limit. They also return single strings
        or objects where the schema says "list of objects", which
        then crashes the frontend ``.map()`` renderers.

        Normalise every field here so persistence and rendering can't
        trip on LLM oddities. Invalid elements are dropped rather than
        coerced — we'd rather lose a bad theme than persist garbage.
        """
        if parsed:
            result = parsed
        elif raw_content:
            try:
                result = json.loads(raw_content)
            except (json.JSONDecodeError, ValueError):
                logger.warning("LLM returned non-JSON content; using fallback")
                result = {"summary": raw_content}
        else:
            result = {}

        return {
            "summary": CommunityOpinionService._clip_str(
                result.get("summary", ""), max_len=2000,
            ),
            "themes": CommunityOpinionService._normalise_themes(
                result.get("themes")
            ),
            "divisions": CommunityOpinionService._normalise_divisions(
                result.get("divisions")
            ),
            "sentiment_trend": CommunityOpinionService._normalise_sentiment_trend(
                result.get("sentiment_trend", "stable")
            ),
            "dominant_emotions": [
                CommunityOpinionService._clip_str(e, max_len=64)
                for e in (result.get("dominant_emotions") or [])
                if isinstance(e, str) and e
            ],
            "key_quotes": CommunityOpinionService._normalise_key_quotes(
                result.get("key_quotes")
            ),
        }

    @staticmethod
    def _clip_str(value: Any, *, max_len: int) -> str:
        """Coerce to a string and hard-clip to max_len characters."""
        if not isinstance(value, str):
            value = str(value) if value is not None else ""
        return value[:max_len]

    @staticmethod
    def _normalise_themes(value: Any) -> list[dict[str, Any]]:
        """Drop any element that isn't a dict with a non-empty ``theme``
        string. Missing ``weight``/``evidence_step`` default to 0."""
        if not isinstance(value, list):
            return []
        out: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            theme = item.get("theme")
            if not isinstance(theme, str) or not theme.strip():
                continue
            try:
                weight = float(item.get("weight", 0.0) or 0.0)
            except (TypeError, ValueError):
                weight = 0.0
            try:
                evidence_step = int(item.get("evidence_step", 0) or 0)
            except (TypeError, ValueError):
                evidence_step = 0
            out.append({
                "theme": CommunityOpinionService._clip_str(theme, max_len=200),
                "weight": max(0.0, min(1.0, weight)),
                "evidence_step": evidence_step,
            })
        return out

    @staticmethod
    def _normalise_divisions(value: Any) -> list[dict[str, Any]]:
        """Drop any element that isn't a dict with a non-empty
        ``faction`` string. Missing ``share`` defaults to 0;
        ``concerns`` defaults to empty list."""
        if not isinstance(value, list):
            return []
        out: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            faction = item.get("faction")
            if not isinstance(faction, str) or not faction.strip():
                continue
            try:
                share = float(item.get("share", 0.0) or 0.0)
            except (TypeError, ValueError):
                share = 0.0
            raw_concerns = item.get("concerns") or []
            concerns = [
                CommunityOpinionService._clip_str(c, max_len=200)
                for c in (raw_concerns if isinstance(raw_concerns, list) else [])
                if isinstance(c, str) and c.strip()
            ]
            out.append({
                "faction": CommunityOpinionService._clip_str(faction, max_len=200),
                "share": max(0.0, min(1.0, share)),
                "concerns": concerns,
            })
        return out

    @staticmethod
    def _normalise_key_quotes(value: Any) -> list[dict[str, Any]]:
        """Drop any element that isn't a dict with non-empty
        ``agent_id`` and ``content`` strings."""
        if not isinstance(value, list):
            return []
        out: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            agent_id = item.get("agent_id")
            content = item.get("content")
            if not isinstance(agent_id, str) or not agent_id.strip():
                continue
            if not isinstance(content, str) or not content.strip():
                continue
            try:
                step = int(item.get("step", 0) or 0)
            except (TypeError, ValueError):
                step = 0
            out.append({
                "agent_id": CommunityOpinionService._clip_str(agent_id, max_len=64),
                "content": CommunityOpinionService._clip_str(content, max_len=500),
                "step": step,
            })
        return out

    @staticmethod
    def _normalise_sentiment_trend(value: Any) -> str:
        """Map any LLM output to one of the four allowed trend values.

        Small LLMs sometimes echo the schema literal
        (``"rising|stable|polarising|collapsing"``). Fall back to
        ``stable`` whenever the value isn't a clean match so the
        ``VARCHAR(32)`` column never overflows.
        """
        allowed = {"rising", "stable", "polarising", "collapsing"}
        if isinstance(value, str):
            v = value.strip().lower()
            if v in allowed:
                return v
            # Tolerate American spelling for the LLM's convenience
            if v in {"polarizing", "polarized"}:
                return "polarising"
            if v in {"collapse", "collapsed", "declining"}:
                return "collapsing"
            if v in {"growing", "accelerating"}:
                return "rising"
        return "stable"

    # ------------------------------------------------------------------ #
    # Cross-community (overall) synthesis                                  #
    # ------------------------------------------------------------------ #

    async def get_or_synthesize_overall(
        self,
        sim_id: UUID,
        *,
        session: AsyncSession,
        synthesize_missing_communities: bool = True,
    ) -> "OverallOpinionSnapshot":
        """Return (or synthesise) a cross-community narrative.

        Pipeline:
          1. Look up cached overall row for ``(sim_id, __overall__, step)``.
             Hit → return immediately (zero LLM cost).
          2. For every community in the simulation, pull its cached
             per-community opinion row. If one is missing AND
             ``synthesize_missing_communities`` is True, trigger a
             per-community synthesis so we have real briefs to feed
             into the aggregate prompt.
          3. Build the aggregate prompt + call the gateway.
          4. Persist a new overall row and return the snapshot plus the
             list of per-community snapshots that fed it.
        """
        try:
            state = self._orch.get_state(sim_id)
        except (KeyError, ValueError) as exc:
            raise SimulationNotFoundError(sim_id) from exc

        current_step = state.current_step

        # Cache hit on the aggregate row itself?
        cached_overall = await self._find_cached(
            sim_id, OVERALL_COMMUNITY_ID, current_step, session=session,
        )

        # Always collect per-community snapshots so the response still
        # includes the breakdown even on a cache hit. These are cheap —
        # most should be DB hits.
        per_community = await self._collect_per_community_snapshots(
            sim_id,
            state,
            current_step,
            session=session,
            synthesize_missing=synthesize_missing_communities,
        )

        if cached_overall is not None:
            logger.debug(
                "overall-opinion cache hit sim=%s step=%d",
                sim_id, current_step,
            )
            return OverallOpinionSnapshot(
                overall=CommunityOpinionSnapshot.from_row(cached_overall),
                communities=per_community,
            )

        if not per_community:
            raise ValueError(
                f"Simulation {sim_id} has no communities to summarise"
            )

        aggregate_metrics = self._aggregate_metrics_from_state(state)
        community_briefs = [
            {
                "community_id": snap.community_id,
                "size": snap.source_agent_count,
                "summary": snap.summary,
                "sentiment_trend": snap.sentiment_trend,
                "adoption_rate": aggregate_metrics.get(
                    "per_community", {}
                ).get(snap.community_id, {}).get("adoption_rate", 0.0),
                "mean_belief": aggregate_metrics.get(
                    "per_community", {}
                ).get(snap.community_id, {}).get("mean_belief", 0.0),
            }
            for snap in per_community
        ]
        first_step = (
            state.step_history[0].step if state.step_history else 0
        )
        last_step = (
            state.step_history[-1].step if state.step_history else 0
        )
        total_agents = sum(snap.source_agent_count for snap in per_community)

        prompt = build_overall_prompt(
            simulation_name=getattr(state.config, "name", "simulation"),
            total_agents=total_agents,
            community_briefs=community_briefs,
            aggregate_metrics=aggregate_metrics,
            first_step=first_step,
            last_step=last_step,
        )

        response = await self._gateway.call(
            prompt,
            task_type="community_opinion",
            tier=3,
            options=LLMOptions(temperature=0.2, timeout_seconds=30.0),
        )
        parsed = self._parse_response(response.parsed, response.content)

        row = CommunityOpinion(
            opinion_id=uuid.uuid4(),
            simulation_id=sim_id,
            community_id=OVERALL_COMMUNITY_ID,
            step=current_step,
            themes=parsed.get("themes", []),
            divisions=parsed.get("divisions", []),
            sentiment_trend=parsed.get("sentiment_trend", "stable"),
            dominant_emotions=parsed.get("dominant_emotions", []),
            key_quotes=parsed.get("key_quotes", []),
            summary=parsed.get("summary", ""),
            source_step_count=len(state.step_history),
            source_agent_count=total_agents,
            llm_provider=response.provider,
            llm_model=response.model,
            llm_cost_usd=0.0,
            is_fallback_stub=response.is_fallback_stub,
        )
        persisted = await self._persist_row_with_retry(row, session)

        return OverallOpinionSnapshot(
            overall=CommunityOpinionSnapshot.from_row(persisted),
            communities=per_community,
        )

    async def _persist_row_with_retry(
        self,
        row: CommunityOpinion,
        session: AsyncSession,
        *,
        max_attempts: int = 3,
    ) -> CommunityOpinion:
        """Add + commit + refresh, handling two distinct race paths.

        **Deadlock retry (sqlstate 40P01).** The
        ``community_opinions.simulation_id`` FK takes a RowShareLock
        on ``simulations``, which can deadlock against the step-runner's
        writer while a simulation is actively running. PostgreSQL's
        deadlock detector picks one victim and aborts it — retrying the
        same transaction usually succeeds on the next attempt because
        one side of the deadlock will have finished by then.

        **Unique violation (sqlstate 23505).** The
        ``uq_community_opinions_sim_comm_step`` constraint rejects
        duplicate ``(sim_id, community_id, step)`` inserts. This can
        happen when two concurrent synthesis requests both miss the
        ``_find_cached`` lookup (the request-before-insert race). When
        this fires, the OTHER writer already persisted a real row;
        fetch it and return that instead of retrying our own doomed
        insert.

        Returns the canonical persisted row — either the one we just
        inserted, or the winner's row if we lost a race. The retry
        loop tracks deadlocks but unique violations terminate the loop
        immediately (there's nothing to retry — the constraint will
        reject us again on the next attempt too).
        """
        for attempt in range(1, max_attempts + 1):
            session.add(row)
            try:
                await session.commit()
                await session.refresh(row)
                return row
            except IntegrityError as exc:
                pgcode = getattr(getattr(exc, "orig", None), "sqlstate", None)
                if pgcode != "23505":
                    # Some other integrity violation (FK, NOT NULL, …)
                    # — roll back and re-raise so the caller sees it.
                    await session.rollback()
                    raise
                await session.rollback()
                existing = await self._find_cached(
                    row.simulation_id, row.community_id, row.step,
                    session=session,
                )
                if existing is not None:
                    logger.info(
                        "community-opinion unique-violation race — "
                        "returning existing row sim=%s comm=%s step=%d",
                        row.simulation_id, row.community_id, row.step,
                    )
                    return existing
                # Constraint says a row exists but our query didn't find
                # it (transaction isolation quirk). Propagate the error
                # rather than silently losing data.
                raise
            except DBAPIError as exc:
                # asyncpg wraps PG deadlock as DeadlockDetectedError;
                # SQLAlchemy wraps that as DBAPIError. We match on the
                # pgcode 40P01 ("deadlock_detected") rather than the
                # Python class name to stay provider-agnostic.
                pgcode = getattr(getattr(exc, "orig", None), "sqlstate", None)
                if pgcode != "40P01" or attempt == max_attempts:
                    # Non-deadlock error (or last attempt) — roll back so
                    # the session isn't left dirty for the caller before
                    # we propagate the exception upward.
                    await session.rollback()
                    raise
                logger.warning(
                    "community-opinion persist deadlock (attempt %d/%d) — "
                    "rolling back and retrying",
                    attempt, max_attempts,
                )
                await session.rollback()
                # Jittered back-off to avoid another head-on collision
                await asyncio.sleep(0.1 * attempt)
        # Unreachable: the loop either returns or raises.
        raise RuntimeError("unreachable: persist retry loop exited without result")

    async def _collect_per_community_snapshots(
        self,
        sim_id: UUID,
        state: Any,
        step: int,
        *,
        session: AsyncSession,
        synthesize_missing: bool,
    ) -> list[CommunityOpinionSnapshot]:
        """Fetch (or synthesise) one snapshot per community in the sim.

        Skips the ``__overall__`` sentinel and any community with no
        agents. Returns snapshots in community-id sort order for stable
        downstream rendering.
        """
        community_ids = self._list_community_ids(state)
        snapshots: list[CommunityOpinionSnapshot] = []
        for cid in sorted(community_ids):
            if cid == OVERALL_COMMUNITY_ID:
                continue
            cached = await self._find_cached(sim_id, cid, step, session=session)
            if cached is not None:
                snapshots.append(CommunityOpinionSnapshot.from_row(cached))
                continue
            if not synthesize_missing:
                continue
            try:
                snap = await self.get_or_synthesize(sim_id, cid, session=session)
            except ValueError as exc:
                # Community has no agents — skip it silently instead of
                # failing the whole overall request.
                logger.info(
                    "overall synthesis: skipping community %s — %s", cid, exc,
                )
                continue
            snapshots.append(snap)
        return snapshots

    @staticmethod
    def _list_community_ids(state: Any) -> list[str]:
        """Best-effort enumeration of community ids from state.

        Reads directly from ``state.agents`` rather than
        ``state.config.communities`` because the two often use
        different identifier schemes: the config stores human-readable
        slugs (``"early_adopters"``) while agents carry UUID strings
        (``"64077f57-…"``). The ``community_opinions`` cache is keyed
        by whatever ``community_id`` per-community callers pass —
        which is always the agent-side id — so the overall synthesis
        has to use the same vocabulary or it'll miss every cache hit.
        """
        ids: set[str] = set()
        for a in getattr(state, "agents", []) or []:
            cid = getattr(a, "community_id", None)
            if cid is not None:
                ids.add(str(cid))
        # Only fall back to config if state.agents somehow had nothing
        if not ids:
            for c in getattr(state.config, "communities", []) or []:
                ids.add(str(getattr(c, "id", "")))
        ids.discard("")
        return list(ids)

    @staticmethod
    def _aggregate_metrics_from_state(state: Any) -> dict[str, Any]:
        """Extract the aggregate metrics the overall prompt needs."""
        last_step = state.step_history[-1] if state.step_history else None
        if last_step is None:
            return {
                "adoption_rate": 0.0,
                "mean_sentiment": 0.0,
                "sentiment_variance": 0.0,
                "diffusion_rate": 0.0,
                "per_community": {},
            }
        per_community: dict[str, dict[str, float]] = {}
        for cid, m in (last_step.community_metrics or {}).items():
            per_community[str(cid)] = {
                "adoption_rate": float(getattr(m, "adoption_rate", 0.0) or 0.0),
                "mean_belief": float(getattr(m, "mean_belief", 0.0) or 0.0),
            }
        return {
            "adoption_rate": float(getattr(last_step, "adoption_rate", 0.0) or 0.0),
            "mean_sentiment": float(getattr(last_step, "mean_sentiment", 0.0) or 0.0),
            "sentiment_variance": float(
                getattr(last_step, "sentiment_variance", 0.0) or 0.0
            ),
            "diffusion_rate": float(
                getattr(last_step, "diffusion_rate", 0.0) or 0.0
            ),
            "per_community": per_community,
        }


@dataclass
class OverallOpinionSnapshot:
    """Aggregate opinion snapshot: cross-community headline + per-community list.

    SPEC: docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis
    """

    overall: CommunityOpinionSnapshot
    communities: list[CommunityOpinionSnapshot]


__all__ = [
    "CommunityOpinionService",
    "CommunityOpinionSnapshot",
    "OverallOpinionSnapshot",
    "OVERALL_COMMUNITY_ID",
    "build_opinion_prompt",
    "build_overall_prompt",
]
