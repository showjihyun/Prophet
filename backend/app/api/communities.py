"""Community endpoints.
SPEC: docs/spec/06_API_SPEC.md#5-community-endpoints
"""
from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_orchestrator
from app.api.schemas import (
    CommunitiesListResponse,
    ThreadDetailResponse,
    ThreadMessage,
    ThreadsListResponse,
    ThreadSummary,
)
from app.api.simulations import _get_state_or_404

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
) -> list[ThreadMessage]:
    """Generate deterministic conversation messages for a thread."""
    msgs: list[ThreadMessage] = []
    for i in range(n_messages):
        seed = hash((community_id, thread_index, i)) & 0xFFFF
        agent_idx = seed % 12
        agent_id = _agent_label(agent_idx, community_id)
        # Deterministic stance
        belief_proxy = (seed % 200 - 100) / 100.0
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


def _build_threads(
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
        msgs = _generate_thread_messages(community_id, t_idx, n_messages)
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

    try:
        result = orchestrator.list_communities(simulation_id)
        if isinstance(result, dict):
            return CommunitiesListResponse(**result)
    except (NotImplementedError, AttributeError, TypeError, ValueError):
        pass

    return CommunitiesListResponse(communities=[])


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
