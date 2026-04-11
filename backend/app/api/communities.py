"""Community endpoints.
SPEC: docs/spec/06_API_SPEC.md#5-community-endpoints
"""
from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_community_opinion_service, get_orchestrator, get_session
from app.api.schemas import (
    CommunitiesListResponse,
    CommunityOpinionResponse,
    OverallOpinionResponse,
    ThreadDetailResponse,
    ThreadMessage,
    ThreadsListResponse,
    ThreadSummary,
)
from app.api.simulations import _get_state_or_404
from app.services.community_opinion_service import (
    OVERALL_COMMUNITY_ID,
    CommunityOpinionService,
    CommunityOpinionSnapshot,
    OverallOpinionSnapshot,
)
from app.services.ports import SimulationNotFoundError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/api/v1/simulations/{simulation_id}/communities",
    tags=["communities"],
)

# ---------------------------------------------------------------------------
# Deterministic content generation helpers
# ---------------------------------------------------------------------------

_TOPICS_BY_ACTION = {
    "share": "Viral spread of the campaign message in community {cid}",
    "adopt": "Adoption wave: members embrace the campaign in community {cid}",
    "discuss": "Active debate on campaign impact in community {cid}",
    "reject": "Pushback against campaign messaging in community {cid}",
    "observe": "Early observers tracking campaign signals in community {cid}",
    "idle": "Ambient discussion in community {cid}",
}

_PROGRESSIVE_MSGS = [
    "The campaign message resonates strongly with community values. We should amplify it further.",
    "Empirical data supports rapid adoption here — the engagement metrics are compelling.",
    "This is exactly the kind of initiative that drives meaningful social change in our network.",
    "The early signals are positive. Spreading this further will benefit the broader ecosystem.",
]

_CONSERVATIVE_MSGS = [
    "We should evaluate the long-term implications before committing to full adoption.",
    "The data looks promising, but our community has seen similar campaigns fail before.",
    "Let's ensure we're not overstating the impact without more rigorous validation.",
    "Caution is warranted — not every viral signal translates to genuine community value.",
]

_NEUTRAL_MSGS = [
    "Both perspectives have merit. A balanced approach to adoption may serve us best.",
    "Evidence suggests moderate engagement is optimal for community cohesion here.",
    "The community is divided — a measured response lets us adapt as new data comes in.",
    "Worth monitoring. Neither full adoption nor rejection seems clearly optimal right now.",
]

_REPLY_MSGS = [
    "That's a fair point. Looking at the diffusion metrics, the pattern does support your reading.",
    "I see your concern, but the community influence scores suggest otherwise.",
    "Agreed on the fundamentals — the propagation data here is unusually clear.",
    "Respectfully, the sentiment variance indicates more uncertainty than that framing suggests.",
]


def _agent_label(agent_index: int, community_id: str) -> str:
    h = hashlib.sha256(f"{community_id}:{agent_index}".encode()).hexdigest()[:4].upper()
    return f"Agent-{community_id}{h}"


def _pick(lst: list[str], seed: int) -> str:
    return lst[seed % len(lst)]


def _stance_from_belief(belief: float) -> str:
    if belief > 0.1:
        return "Progressive"
    if belief < -0.1:
        return "Conservative"
    return "Neutral"


def _generate_thread_messages(
    community_id: str,
    thread_index: int,
    n_messages: int,
    mean_belief: float = 0.0,
    adoption_rate: float = 0.0,
) -> list[ThreadMessage]:
    """Generate conversation messages reflecting actual community state.

    Uses mean_belief from simulation data to bias stance distribution,
    making threads more representative of actual agent behavior.
    """
    msgs: list[ThreadMessage] = []
    for i in range(n_messages):
        seed = hash((community_id, thread_index, i)) & 0xFFFF
        agent_idx = seed % 12
        agent_id = _agent_label(agent_idx, community_id)
        # Stance biased by actual community mean_belief (not pure random)
        belief_noise = (seed % 60 - 30) / 100.0  # ±0.3 variation
        belief_proxy = max(-1.0, min(1.0, mean_belief + belief_noise))
        stance = _stance_from_belief(belief_proxy)
        # Content
        if i > 0 and (seed % 3) == 0:
            content = _pick(_REPLY_MSGS, seed)
            is_reply = True
            reply_to_id = msgs[i - 1].message_id
        else:
            if stance == "Progressive":
                content = _pick(_PROGRESSIVE_MSGS, seed)
            elif stance == "Conservative":
                content = _pick(_CONSERVATIVE_MSGS, seed)
            else:
                content = _pick(_NEUTRAL_MSGS, seed)
            is_reply = False
            reply_to_id = None
        msgs.append(
            ThreadMessage(
                message_id=f"t{thread_index}-m{i}",
                agent_id=agent_id,
                community_id=community_id,
                stance=stance,
                content=content,
                reactions={
                    "agree": (seed * 7) % 20,
                    "disagree": (seed * 3) % 12,
                    "nuanced": (seed * 5) % 10,
                },
                is_reply=is_reply,
                reply_to_id=reply_to_id,
            )
        )
    return msgs


def _build_real_threads(
    state: Any,
    community_id: str,
) -> list[tuple[ThreadSummary, list[ThreadMessage]]] | None:
    """Build threads from real captured agent messages if available.
    SPEC: docs/spec/22_CONVERSATION_THREAD_SPEC.md#CT-06
    """
    step_history = getattr(state, "step_history", [])
    if not step_history:
        return None

    # Collect all thread messages for this community across steps
    all_msgs = []
    for sr in step_history:
        for msg in getattr(sr, "thread_messages", []):
            if str(getattr(msg, "community_id", "")) == community_id or str(msg.community_id) == community_id:
                all_msgs.append(msg)

    if not all_msgs:
        return None

    # Group messages into threads by step ranges (every 5 steps = 1 thread)
    from collections import defaultdict
    step_groups: dict[int, list] = defaultdict(list)
    for msg in all_msgs:
        group_key = msg.step // 5
        step_groups[group_key].append(msg)

    threads = []
    for group_key in sorted(step_groups.keys()):
        group = step_groups[group_key]
        step_start = group_key * 5
        step_end = step_start + 4

        # Build ThreadMessage list
        participants = set()
        msgs = []
        total_belief = 0.0
        for m in group:
            participants.add(str(m.agent_id))
            total_belief += m.belief
            msgs.append(ThreadMessage(
                message_id=str(m.message_id),
                agent_id=str(m.agent_id),
                community_id=community_id,
                stance=_stance_from_belief(m.belief),
                content=m.content,
                reactions={
                    "agree": max(0, int(m.emotion_valence * 10)),
                    "disagree": max(0, int((1 - m.emotion_valence) * 5)),
                    "nuanced": 2,
                },
                is_reply=m.reply_to_id is not None,
                reply_to_id=str(m.reply_to_id) if m.reply_to_id else None,
            ))

        avg_sentiment = total_belief / len(group) if group else 0.0
        dominant = max(set(m.action for m in group), key=lambda a: sum(1 for x in group if x.action == a)) if group else "idle"
        topic_tmpl = _TOPICS_BY_ACTION.get(dominant, _TOPICS_BY_ACTION["idle"])
        topic = topic_tmpl.format(cid=community_id)

        summary = ThreadSummary(
            thread_id=f"{community_id}-thread-{group_key}",
            topic=f"Steps {step_start}-{step_end}: {topic}",
            participant_count=len(participants),
            message_count=len(msgs),
            avg_sentiment=round(avg_sentiment, 2),
        )
        threads.append((summary, msgs))

    return threads if threads else None


def _build_threads(
    state: Any,
    community_id: str,
) -> list[tuple[ThreadSummary, list[ThreadMessage]]]:
    """Build threads from real agent messages, falling back to synthetic.
    SPEC: docs/spec/22_CONVERSATION_THREAD_SPEC.md#CT-06
    """
    # Try real threads first
    real = _build_real_threads(state, community_id)
    if real:
        return real

    # Fallback: synthetic threads from simulation state
    return _build_synthetic_threads(state, community_id)


def _build_synthetic_threads(
    state: Any,
    community_id: str,
) -> list[tuple[ThreadSummary, list[ThreadMessage]]]:
    """Derive synthetic threads from simulation state for the given community."""
    # Determine dominant action to pick topic
    dominant_action = "idle"
    mean_belief = 0.0
    adoption_rate = 0.0
    step_count = 0

    step_history = getattr(state, "step_history", [])
    if step_history:
        latest = step_history[-1]
        step_count = len(step_history)
        cm = {}
        if hasattr(latest, "community_metrics"):
            cm = latest.community_metrics or {}
        elif isinstance(latest, dict):
            cm = latest.get("community_metrics", {})
        comm_data = cm.get(community_id, {})
        if isinstance(comm_data, dict):
            dominant_action = comm_data.get("dominant_action", "idle")
            mean_belief = comm_data.get("mean_belief", 0.0)
            adoption_rate = comm_data.get("adoption_rate", 0.0)
        else:
            dominant_action = getattr(comm_data, "dominant_action", "idle")
            mean_belief = getattr(comm_data, "mean_belief", 0.0)
            adoption_rate = getattr(comm_data, "adoption_rate", 0.0)

    # Generate 3 threads per community
    threads = []
    n_threads = 3
    for t_idx in range(n_threads):
        seed = hash((community_id, t_idx)) & 0xFF
        topic_tmpl = _TOPICS_BY_ACTION.get(dominant_action, _TOPICS_BY_ACTION["idle"])
        topic = topic_tmpl.format(cid=community_id)
        if t_idx == 1:
            topic = f"Step {max(step_count, 1)}: {dominant_action} dynamics — {int(adoption_rate * 100)}% adoption"
        elif t_idx == 2:
            topic = f"Sentiment analysis: mean belief {mean_belief:+.2f} in community {community_id}"
        n_messages = 4 + (seed % 5)
        msgs = _generate_thread_messages(
            community_id, t_idx, n_messages,
            mean_belief=mean_belief, adoption_rate=adoption_rate,
        )
        avg_sentiment = round(mean_belief + (seed % 20 - 10) / 100.0, 2)
        summary = ThreadSummary(
            thread_id=f"{community_id}-thread-{t_idx}",
            topic=topic,
            participant_count=len({m.agent_id for m in msgs}),
            message_count=len(msgs),
            avg_sentiment=avg_sentiment,
        )
        threads.append((summary, msgs))
    return threads


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/", response_model=CommunitiesListResponse)
async def list_communities(
    simulation_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> CommunitiesListResponse:
    """List all communities with current metrics.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idcommunities
    """
    _get_state_or_404(orchestrator, simulation_id)

    # Real errors (TypeError, AttributeError from orchestrator bugs) MUST
    # surface as 500. Only ValueError ("sim not found") is a clean path
    # that returns empty — and _get_state_or_404 already handles that.
    result = orchestrator.list_communities(simulation_id)
    if not isinstance(result, dict):
        return CommunitiesListResponse(communities=[])
    return CommunitiesListResponse(**result)


@router.get("/{community_id}/threads", response_model=ThreadsListResponse)
async def list_community_threads(
    simulation_id: str,
    community_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> ThreadsListResponse:
    """List conversation threads derived from agent interactions in a community.
    SPEC: docs/spec/06_API_SPEC.md#5-community-endpoints
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    threads = _build_threads(state, community_id)
    return ThreadsListResponse(threads=[s for s, _ in threads])


@router.get("/{community_id}/threads/{thread_id}", response_model=ThreadDetailResponse)
async def get_community_thread(
    simulation_id: str,
    community_id: str,
    thread_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> ThreadDetailResponse:
    """Return messages for a specific conversation thread.
    SPEC: docs/spec/06_API_SPEC.md#5-community-endpoints
    """
    state = _get_state_or_404(orchestrator, simulation_id)
    threads = _build_threads(state, community_id)

    for summary, messages in threads:
        if summary.thread_id == thread_id:
            return ThreadDetailResponse(
                thread_id=summary.thread_id,
                topic=summary.topic,
                participant_count=summary.participant_count,
                message_count=summary.message_count,
                avg_sentiment=summary.avg_sentiment,
                messages=messages,
            )

    raise HTTPException(status_code=404, detail=f"Thread {thread_id!r} not found in community {community_id!r}")


# ---------------------------------------------------------------------------
# Community Management Endpoints (CRUD)
# SPEC: docs/spec/16_COMMUNITY_MGMT_SPEC.md
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field


class UpdateCommunityRequest(BaseModel):
    name: str | None = None
    personality_profile: dict[str, float] | None = None


class CreateCommunityRequest(BaseModel):
    name: str
    agent_type: str = "consumer"
    size: int = Field(ge=1, le=10000)
    personality_profile: dict[str, float] = {}


class ReassignAgentsRequest(BaseModel):
    agent_ids: list[str]
    target_community_id: str


@router.patch("/{community_id}")
async def update_community(
    simulation_id: str,
    community_id: str,
    body: UpdateCommunityRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> dict:
    """Update community properties (name, personality).
    SPEC: docs/spec/16_COMMUNITY_MGMT_SPEC.md#2-1
    """
    from uuid import UUID
    from app.engine.simulation.exceptions import InvalidStateError

    _get_state_or_404(orchestrator, simulation_id)
    try:
        result = await orchestrator.update_community(
            UUID(simulation_id),
            community_id,
            name=body.name,
            personality_profile=body.personality_profile,
        )
        return result
    except InvalidStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/", status_code=201)
async def add_community(
    simulation_id: str,
    body: CreateCommunityRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> dict:
    """Add a new community with agents to the simulation.
    SPEC: docs/spec/16_COMMUNITY_MGMT_SPEC.md#2-2
    """
    from uuid import UUID
    from app.engine.simulation.exceptions import InvalidStateError

    _get_state_or_404(orchestrator, simulation_id)
    try:
        result = await orchestrator.add_community(
            UUID(simulation_id),
            name=body.name,
            agent_type=body.agent_type,
            size=body.size,
            personality_profile=body.personality_profile or {
                "openness": 0.5, "skepticism": 0.5, "trend_following": 0.5,
                "brand_loyalty": 0.5, "social_influence": 0.4,
            },
        )
        return result
    except InvalidStateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{community_id}")
async def delete_community(
    simulation_id: str,
    community_id: str,
    orchestrator: Any = Depends(get_orchestrator),
) -> dict:
    """Remove a community and its agents from the simulation.
    SPEC: docs/spec/16_COMMUNITY_MGMT_SPEC.md#2-3
    """
    from uuid import UUID
    from app.engine.simulation.exceptions import InvalidStateError

    _get_state_or_404(orchestrator, simulation_id)
    try:
        result = await orchestrator.remove_community(UUID(simulation_id), community_id)
        return result
    except InvalidStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/__overall__/opinion-summary",
    response_model=OverallOpinionResponse,
)
async def synthesize_overall_opinion(
    simulation_id: str,
    service: CommunityOpinionService = Depends(get_community_opinion_service),
    session: AsyncSession = Depends(get_session),
) -> OverallOpinionResponse:
    """Synthesize (or return cached) cross-community EliteLLM narrative.

    SPEC: docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis

    Semantics:
      * Idempotent on ``(simulation_id, current_step)`` — once the
        overall row exists for this step we return the cached copy.
      * Synthesises any missing per-community opinions as a side-effect
        so the aggregate prompt always has real briefs to chew on.
      * Route is declared before ``/{community_id}/opinion-summary`` so
        FastAPI matches ``__overall__`` as a literal path segment, not
        a community_id.
    """
    from uuid import UUID

    try:
        sim_uuid = UUID(simulation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid simulation_id: {exc}")

    try:
        agg = await service.get_or_synthesize_overall(
            sim_uuid, session=session,
        )
    except SimulationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return OverallOpinionResponse(
        overall=_snapshot_to_response(agg.overall),
        communities=[_snapshot_to_response(s) for s in agg.communities],
    )


def _snapshot_to_response(snap: CommunityOpinionSnapshot) -> CommunityOpinionResponse:
    return CommunityOpinionResponse(
        opinion_id=str(snap.opinion_id),
        simulation_id=str(snap.simulation_id),
        community_id=snap.community_id,
        step=snap.step,
        summary=snap.summary,
        sentiment_trend=snap.sentiment_trend,
        themes=snap.themes,
        divisions=snap.divisions,
        dominant_emotions=snap.dominant_emotions,
        key_quotes=snap.key_quotes,
        source_step_count=snap.source_step_count,
        source_agent_count=snap.source_agent_count,
        llm_provider=snap.llm_provider,
        llm_model=snap.llm_model,
        is_fallback_stub=snap.is_fallback_stub,
    )


@router.post(
    "/{community_id}/opinion-summary",
    response_model=CommunityOpinionResponse,
)
async def synthesize_community_opinion(
    simulation_id: str,
    community_id: str,
    service: CommunityOpinionService = Depends(get_community_opinion_service),
    session: AsyncSession = Depends(get_session),
) -> CommunityOpinionResponse:
    """Synthesize (or return cached) EliteLLM narrative for a community.

    SPEC: docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis

    Idempotent on ``(simulation_id, community_id, current_step)``: two
    calls at the same step return the same persisted row without paying
    for a second LLM call.
    """
    from uuid import UUID

    try:
        sim_uuid = UUID(simulation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid simulation_id: {exc}")

    try:
        snap = await service.get_or_synthesize(
            sim_uuid, community_id, session=session,
        )
    except SimulationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        # Community not found in this simulation's state
        raise HTTPException(status_code=404, detail=str(exc))

    return _snapshot_to_response(snap)


@router.post("/{community_id}/reassign")
async def reassign_agents(
    simulation_id: str,
    community_id: str,
    body: ReassignAgentsRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> dict:
    """Reassign agents from this community to another.
    SPEC: docs/spec/16_COMMUNITY_MGMT_SPEC.md#2-4
    """
    from uuid import UUID
    from app.engine.simulation.exceptions import InvalidStateError

    _get_state_or_404(orchestrator, simulation_id)
    try:
        result = await orchestrator.reassign_agents(
            UUID(simulation_id),
            community_id,
            agent_ids=[UUID(aid) for aid in body.agent_ids],
            target_community_id=body.target_community_id,
        )
        return result
    except InvalidStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
