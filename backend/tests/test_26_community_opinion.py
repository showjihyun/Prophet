"""Unit tests for CommunityOpinionService.

SPEC: docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis

Covers:
  * ``build_opinion_prompt`` pure function (deterministic, no I/O)
  * ``CommunityOpinionService.get_or_synthesize`` happy path + caching
  * Simulation-not-found + community-not-found error paths
  * Fallback-stub persistence (when every adapter fails the gateway
    returns ``is_fallback_stub=True`` and we still persist the snapshot)
  * JSON parse fallback (``_parse_response``)

The service is exercised against:
  * a real in-memory orchestrator (via factory fixtures already used in
    other suites) so we don't have to fake SimulationState
  * a stub gateway that returns a canned ``LLMResponse`` — lets us
    inspect the prompt that would have been sent
"""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from app.engine.agent.schema import AgentAction, AgentType
from app.llm.schema import LLMOptions, LLMPrompt, LLMResponse
from app.services.community_opinion_service import (
    OVERALL_COMMUNITY_ID,
    CommunityOpinionService,
    build_opinion_prompt,
    build_overall_prompt,
)
from app.services.ports import SimulationNotFoundError


# ===========================================================================
# Prompt builder — pure function, no I/O
# ===========================================================================


class TestBuildOpinionPrompt:
    """SPEC: 25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis"""

    def _agent(self, belief: float = 0.5, adopted: bool = True) -> dict:
        return {
            "agent_id": "abcdef1234567890",
            "agent_type": "consumer",
            "belief": belief,
            "adopted": adopted,
            "action": "share",
        }

    def test_includes_community_header_and_step_range(self):
        prompt = build_opinion_prompt(
            community_id="early-adopters",
            community_size=42,
            step_metrics_table="step | adoption\n   0 | 0.10",
            agent_summaries=[self._agent()],
            dominant_action_breakdown={"share": 10, "ignore": 2},
            first_step=0,
            last_step=5,
        )
        assert isinstance(prompt, LLMPrompt)
        assert "early-adopters" in prompt.user
        assert "42 agents" in prompt.user
        assert "0 → 5" in prompt.user
        # Context metadata preserved
        assert prompt.context["community_id"] == "early-adopters"
        assert prompt.context["step_range"] == [0, 5]
        # JSON response format (anti-hallucination requires structured output)
        assert prompt.response_format == "json"

    def test_system_prompt_has_antihallucination_rules(self):
        prompt = build_opinion_prompt(
            community_id="c1",
            community_size=1,
            step_metrics_table="",
            agent_summaries=[],
            dominant_action_breakdown={},
            first_step=0,
            last_step=0,
        )
        assert "Never invent quotes" in prompt.system
        assert "JSON" in prompt.system

    def test_handles_empty_agent_sample(self):
        prompt = build_opinion_prompt(
            community_id="c1",
            community_size=0,
            step_metrics_table="",
            agent_summaries=[],
            dominant_action_breakdown={},
            first_step=0,
            last_step=0,
        )
        assert "(no agent samples)" in prompt.user

    def test_truncates_agent_sample_to_10(self):
        agents = [
            {
                "agent_id": f"{i:016x}" * 2,  # 32 hex chars — UUID-like
                "agent_type": "consumer",
                "belief": 0.5 + i * 0.01,
                "adopted": True,
                "action": "share",
            }
            for i in range(20)
        ]
        prompt = build_opinion_prompt(
            community_id="c1",
            community_size=20,
            step_metrics_table="",
            agent_summaries=agents,
            dominant_action_breakdown={"share": 20},
            first_step=0,
            last_step=0,
        )
        # Only first 10 should appear (by design — keeps prompt small)
        lines = [l for l in prompt.user.splitlines() if l.startswith("  - agent=")]
        assert len(lines) == 10


# ===========================================================================
# Service happy path + caching
# ===========================================================================


def _make_state(
    community_id: str,
    *,
    current_step: int = 5,
    agents_in_community: int = 3,
) -> Any:
    """Build a minimal SimulationState-shaped object the service reads from.

    Only the attributes the service actually touches are populated —
    that keeps this test independent from the real SimulationState
    dataclass shape (which evolves frequently).
    """
    agents = []
    for i in range(agents_in_community):
        agents.append(
            SimpleNamespace(
                agent_id=uuid4(),
                community_id=community_id,
                agent_type=AgentType.CONSUMER,
                belief=0.5 + i * 0.1,
                adopted=bool(i % 2),
                action=AgentAction.SHARE,
                influence_score=0.1 + i * 0.1,
            )
        )

    # One unrelated agent in a different community — service must filter it out
    agents.append(
        SimpleNamespace(
            agent_id=uuid4(),
            community_id="other-community",
            agent_type=AgentType.SKEPTIC,
            belief=0.1,
            adopted=False,
            action=AgentAction.IGNORE,
            influence_score=0.0,
        )
    )

    step_history = [
        SimpleNamespace(
            step=s,
            community_metrics={
                community_id: SimpleNamespace(
                    adoption_rate=0.1 * s,
                    mean_belief=0.4 + 0.02 * s,
                    dominant_action=AgentAction.SHARE,
                )
            },
        )
        for s in range(1, current_step + 1)
    ]

    config = SimpleNamespace(communities=[SimpleNamespace(id=community_id)])

    return SimpleNamespace(
        current_step=current_step,
        agents=agents,
        step_history=step_history,
        config=config,
    )


class StubOrchestrator:
    """Implements the tiny surface the service uses: ``get_state``."""

    def __init__(self, state: Any | None) -> None:
        self._state = state
        self.calls: list[uuid.UUID] = []

    def get_state(self, sim_id: uuid.UUID) -> Any:
        self.calls.append(sim_id)
        if self._state is None:
            raise ValueError(f"Simulation {sim_id} not found")
        return self._state


class StubGateway:
    """Captures the prompt and returns a canned LLMResponse."""

    def __init__(self, content: str, *, is_fallback_stub: bool = False) -> None:
        self._content = content
        self._is_fallback = is_fallback_stub
        self.calls: list[dict] = []

    async def call(
        self,
        prompt: LLMPrompt,
        task_type: str = "cognition",
        tier: int = 3,
        options: LLMOptions | None = None,
        prompt_embedding: list[float] | None = None,
        budget_remaining: float | None = None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "task_type": task_type,
                "tier": tier,
                "temperature": options.temperature if options else None,
                "prompt_user": prompt.user,
            }
        )
        try:
            parsed = json.loads(self._content)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        return LLMResponse(
            provider="stub",
            model="stub-gpt",
            content=self._content,
            parsed=parsed,
            prompt_tokens=10,
            completion_tokens=20,
            latency_ms=5.0,
            is_fallback_stub=self._is_fallback,
        )


@pytest.fixture
def session_stub():
    """In-memory fake for AsyncSession.

    Records ``add``/``commit``/``refresh`` calls and lets a fake
    ``execute`` be monkey-patched per test.
    """

    class _FakeResult:
        def __init__(self, row: Any | None):
            self._row = row

        def scalar_one_or_none(self) -> Any | None:
            return self._row

    class _FakeSession:
        def __init__(self) -> None:
            self.added: list[Any] = []
            self.committed = False
            self.refreshed: list[Any] = []
            self._cached_row: Any | None = None

        def set_cached(self, row: Any | None) -> None:
            self._cached_row = row

        def add(self, row: Any) -> None:
            self.added.append(row)

        async def commit(self) -> None:
            self.committed = True

        async def refresh(self, row: Any) -> None:
            self.refreshed.append(row)

        async def execute(self, _stmt: Any) -> Any:
            return _FakeResult(self._cached_row)

    return _FakeSession()


VALID_LLM_JSON = json.dumps(
    {
        "summary": "Community is polarising around the campaign — early enthusiasm fades as sceptics push back.",
        "themes": [
            {"theme": "rapid early adoption", "weight": 0.6, "evidence_step": 1},
            {"theme": "resistance from long-time members", "weight": 0.4, "evidence_step": 4},
        ],
        "divisions": [
            {"faction": "enthusiasts", "share": 0.55, "concerns": ["value"]},
            {"faction": "holdouts", "share": 0.45, "concerns": ["trust"]},
        ],
        "sentiment_trend": "polarising",
        "dominant_emotions": ["excitement", "skepticism"],
        "key_quotes": [],
    }
)


class TestCommunityOpinionService:
    """SPEC: 25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis"""

    @pytest.mark.asyncio
    async def test_simulation_not_found_raises_domain_error(self, session_stub):
        orch = StubOrchestrator(state=None)
        gw = StubGateway(content=VALID_LLM_JSON)
        service = CommunityOpinionService(orchestrator=orch, gateway=gw)

        with pytest.raises(SimulationNotFoundError):
            await service.get_or_synthesize(
                uuid4(), "community-x", session=session_stub,
            )
        # Gateway must not be called if the sim doesn't exist
        assert gw.calls == []

    @pytest.mark.asyncio
    async def test_unknown_community_raises_value_error(self, session_stub):
        state = _make_state("known-community")
        orch = StubOrchestrator(state=state)
        gw = StubGateway(content=VALID_LLM_JSON)
        service = CommunityOpinionService(orchestrator=orch, gateway=gw)

        with pytest.raises(ValueError, match="has no agents"):
            await service.get_or_synthesize(
                uuid4(), "nonexistent-community", session=session_stub,
            )
        assert gw.calls == []

    @pytest.mark.asyncio
    async def test_happy_path_calls_gateway_and_persists(self, session_stub):
        cid = "consumer"
        state = _make_state(cid, current_step=5)
        orch = StubOrchestrator(state=state)
        gw = StubGateway(content=VALID_LLM_JSON)
        service = CommunityOpinionService(orchestrator=orch, gateway=gw)

        sim_id = uuid4()
        snap = await service.get_or_synthesize(sim_id, cid, session=session_stub)

        # Gateway called with tier=3, task_type="community_opinion"
        assert len(gw.calls) == 1
        call = gw.calls[0]
        assert call["task_type"] == "community_opinion"
        assert call["tier"] == 3
        assert call["temperature"] == 0.2
        # Prompt mentions the community and the step range
        assert cid in call["prompt_user"]

        # Row was added + committed
        assert len(session_stub.added) == 1
        assert session_stub.committed

        # Snapshot reflects the parsed LLM output
        assert snap.summary.startswith("Community is polarising")
        assert snap.sentiment_trend == "polarising"
        assert len(snap.themes) == 2
        assert snap.source_agent_count == 3
        assert snap.source_step_count == 5
        assert snap.is_fallback_stub is False
        assert snap.llm_provider == "stub"

    @pytest.mark.asyncio
    async def test_cache_hit_short_circuits_gateway(self, session_stub):
        cid = "consumer"
        state = _make_state(cid, current_step=5)
        orch = StubOrchestrator(state=state)
        gw = StubGateway(content=VALID_LLM_JSON)
        service = CommunityOpinionService(orchestrator=orch, gateway=gw)

        # Pre-seed the "cache hit" row
        cached_row = SimpleNamespace(
            opinion_id=uuid4(),
            simulation_id=uuid4(),
            community_id=cid,
            step=5,
            summary="CACHED — do not call LLM",
            sentiment_trend="stable",
            themes=[],
            divisions=[],
            dominant_emotions=[],
            key_quotes=[],
            source_step_count=5,
            source_agent_count=3,
            llm_provider="cached",
            llm_model="cached-model",
            llm_cost_usd=0.0,
            is_fallback_stub=False,
        )
        session_stub.set_cached(cached_row)

        snap = await service.get_or_synthesize(uuid4(), cid, session=session_stub)

        # Gateway must NOT have been called — this is the point of the cache
        assert gw.calls == []
        assert snap.summary == "CACHED — do not call LLM"
        # Nothing new persisted
        assert session_stub.added == []

    @pytest.mark.asyncio
    async def test_fallback_stub_still_persists(self, session_stub):
        """Even when every LLM adapter fails, we persist the stub response
        so the UI can show 'we couldn't reach an LLM' instead of silently
        retrying forever.
        """
        cid = "consumer"
        state = _make_state(cid)
        orch = StubOrchestrator(state=state)
        gw = StubGateway(content="{}", is_fallback_stub=True)
        service = CommunityOpinionService(orchestrator=orch, gateway=gw)

        snap = await service.get_or_synthesize(uuid4(), cid, session=session_stub)

        assert snap.is_fallback_stub is True
        assert len(session_stub.added) == 1

    @pytest.mark.asyncio
    async def test_parse_response_handles_nonjson_content(self, session_stub):
        """LLM returned free-text instead of JSON — we must fall back to a
        structured snapshot rather than blowing up.
        """
        cid = "consumer"
        state = _make_state(cid)
        orch = StubOrchestrator(state=state)
        gw = StubGateway(content="Sorry, I cannot help with that.")
        service = CommunityOpinionService(orchestrator=orch, gateway=gw)

        snap = await service.get_or_synthesize(uuid4(), cid, session=session_stub)

        # The free-text content became the summary (truncated)
        assert "Sorry, I cannot help" in snap.summary
        # All structured fields default to sentinel values — not None
        assert snap.themes == []
        assert snap.divisions == []
        assert snap.sentiment_trend == "stable"


# ===========================================================================
# Overall (cross-community) synthesis
# ===========================================================================


def _make_multi_state(
    community_ids: list[str],
    *,
    current_step: int = 5,
    agents_per_community: int = 2,
) -> Any:
    """Build a minimal SimulationState spanning multiple communities."""
    agents = []
    per_community_metrics = {}
    for idx, cid in enumerate(community_ids):
        for i in range(agents_per_community):
            agents.append(
                SimpleNamespace(
                    agent_id=uuid4(),
                    community_id=cid,
                    agent_type=AgentType.CONSUMER,
                    belief=0.3 + idx * 0.1 + i * 0.05,
                    adopted=bool((idx + i) % 2),
                    action=AgentAction.SHARE,
                    influence_score=0.1 + idx * 0.1,
                )
            )
        per_community_metrics[cid] = SimpleNamespace(
            adoption_rate=0.2 + idx * 0.1,
            mean_belief=0.4 + idx * 0.05,
            dominant_action=AgentAction.SHARE,
        )

    step_history = [
        SimpleNamespace(
            step=s,
            adoption_rate=0.3,
            mean_sentiment=0.4,
            sentiment_variance=0.1,
            diffusion_rate=0.05,
            community_metrics=per_community_metrics,
        )
        for s in range(1, current_step + 1)
    ]

    config = SimpleNamespace(
        name="test-sim",
        communities=[SimpleNamespace(id=cid) for cid in community_ids],
    )

    return SimpleNamespace(
        current_step=current_step,
        agents=agents,
        step_history=step_history,
        config=config,
    )


class TestBuildOverallPrompt:
    """SPEC: 25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis"""

    def test_includes_community_count_and_step_range(self):
        prompt = build_overall_prompt(
            simulation_name="sustainability-launch",
            total_agents=500,
            community_briefs=[
                {
                    "community_id": "early-adopters",
                    "size": 100,
                    "summary": "Rapid early uptake",
                    "sentiment_trend": "rising",
                    "adoption_rate": 0.82,
                    "mean_belief": 0.6,
                },
                {
                    "community_id": "skeptics",
                    "size": 200,
                    "summary": "Resistance around pricing",
                    "sentiment_trend": "stable",
                    "adoption_rate": 0.12,
                    "mean_belief": -0.1,
                },
            ],
            aggregate_metrics={
                "adoption_rate": 0.32,
                "mean_sentiment": 0.2,
                "sentiment_variance": 0.15,
                "diffusion_rate": 0.04,
            },
            first_step=0,
            last_step=10,
        )
        assert isinstance(prompt, LLMPrompt)
        assert "sustainability-launch" in prompt.user
        assert "500 agents" in prompt.user
        assert "2 communities" in prompt.user
        assert "0 → 10" in prompt.user
        # Per-community briefs must be in the prompt
        assert "early-adopters" in prompt.user
        assert "skeptics" in prompt.user
        assert "Rapid early uptake" in prompt.user
        assert "Resistance around pricing" in prompt.user
        assert prompt.context["scope"] == "overall"
        assert prompt.context["community_count"] == 2

    def test_uses_overall_system_prompt(self):
        prompt = build_overall_prompt(
            simulation_name="x",
            total_agents=0,
            community_briefs=[],
            aggregate_metrics={},
            first_step=0,
            last_step=0,
        )
        assert "CROSS-COMMUNITY" in prompt.system
        assert "community_ids" in prompt.system


class TestOverallSynthesis:
    """SPEC: 25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis"""

    @pytest.mark.asyncio
    async def test_simulation_not_found_raises(self, session_stub):
        orch = StubOrchestrator(state=None)
        gw = StubGateway(content=VALID_LLM_JSON)
        service = CommunityOpinionService(orchestrator=orch, gateway=gw)

        with pytest.raises(SimulationNotFoundError):
            await service.get_or_synthesize_overall(uuid4(), session=session_stub)

    @pytest.mark.asyncio
    async def test_happy_path_synthesizes_all_tiers(self, session_stub):
        """First call must:
          1. Synthesise each community (one LLM call per community)
          2. Synthesise the overall aggregate (one additional LLM call)
        Total = N+1 LLM calls.
        """
        cids = ["alpha", "beta"]
        state = _make_multi_state(cids, current_step=4)
        orch = StubOrchestrator(state=state)
        gw = StubGateway(content=VALID_LLM_JSON)
        service = CommunityOpinionService(orchestrator=orch, gateway=gw)

        agg = await service.get_or_synthesize_overall(
            uuid4(), session=session_stub,
        )

        # N communities + 1 aggregate call
        assert len(gw.calls) == len(cids) + 1
        # Aggregate call prompt must mention both communities
        overall_call = gw.calls[-1]
        for cid in cids:
            assert cid in overall_call["prompt_user"]

        # Response payload shape
        assert agg.overall.community_id == OVERALL_COMMUNITY_ID
        assert len(agg.communities) == len(cids)
        assert {c.community_id for c in agg.communities} == set(cids)

        # DB writes: one per community + one aggregate
        assert len(session_stub.added) == len(cids) + 1

    @pytest.mark.asyncio
    async def test_no_communities_raises_value_error(self, session_stub):
        state = _make_multi_state([], current_step=2)
        orch = StubOrchestrator(state=state)
        gw = StubGateway(content=VALID_LLM_JSON)
        service = CommunityOpinionService(orchestrator=orch, gateway=gw)

        with pytest.raises(ValueError, match="no communities"):
            await service.get_or_synthesize_overall(
                uuid4(), session=session_stub,
            )

    @pytest.mark.asyncio
    async def test_overall_prompt_uses_community_summaries(self, session_stub):
        """The aggregate prompt must embed each community's summary so
        the LLM can reason about cross-community dynamics."""
        cids = ["alpha", "beta"]
        state = _make_multi_state(cids)
        orch = StubOrchestrator(state=state)
        gw = StubGateway(content=VALID_LLM_JSON)
        service = CommunityOpinionService(orchestrator=orch, gateway=gw)

        await service.get_or_synthesize_overall(uuid4(), session=session_stub)

        # Aggregate call is the last one
        overall_call = gw.calls[-1]
        # It must contain the per-community summaries (from the canned JSON)
        assert "polarising" in overall_call["prompt_user"]


# ===========================================================================
# Response normalisation (pure functions on the service class)
# ===========================================================================


class TestResponseNormalisation:
    """SPEC: 25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis

    Covers the ``_parse_response``, ``_normalise_sentiment_trend``, and
    ``_clip_str`` helpers that guard against small-LLM edge cases (echoed
    schema literals, over-long strings, American spellings, etc.).
    """

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("rising", "rising"),
            ("Stable", "stable"),
            ("POLARISING", "polarising"),
            ("polarizing", "polarising"),  # American → British
            ("collapse", "collapsing"),
            ("growing", "rising"),
            # The classic small-LLM failure: echo the schema literal
            ("rising|stable|polarising|collapsing", "stable"),
            # Unknown / garbage values fall back to the safe default
            ("overwhelming", "stable"),
            ("", "stable"),
            (None, "stable"),
            (42, "stable"),
        ],
    )
    def test_normalise_sentiment_trend(self, raw, expected):
        assert (
            CommunityOpinionService._normalise_sentiment_trend(raw) == expected
        )

    @pytest.mark.parametrize(
        "raw,max_len,expected",
        [
            ("short", 100, "short"),
            ("x" * 50, 10, "xxxxxxxxxx"),
            ("", 10, ""),
            (None, 10, ""),
            (123, 10, "123"),
        ],
    )
    def test_clip_str(self, raw, max_len, expected):
        assert CommunityOpinionService._clip_str(raw, max_len=max_len) == expected

    def test_parse_response_normalises_all_fields(self):
        """A small LLM returns a hostile payload with a schema literal
        in ``sentiment_trend`` and a missing ``themes`` field. The
        parser must coerce it into a shape safe for DB persistence."""
        raw = {
            "summary": "x" * 5000,  # Over the 2000 clip limit
            "sentiment_trend": "rising|stable|polarising|collapsing",
            "dominant_emotions": ["excitement", None, 42],  # mixed garbage
            "divisions": [{"faction": "a", "share": 0.5, "concerns": []}],
        }
        normalised = CommunityOpinionService._parse_response(raw, "")
        assert len(normalised["summary"]) == 2000
        assert normalised["sentiment_trend"] == "stable"
        # Non-string emotions are dropped entirely
        assert normalised["dominant_emotions"] == ["excitement"]
        assert normalised["themes"] == []
        # Divisions round-trip through the normaliser — same shape as input
        assert normalised["divisions"] == [{
            "faction": "a", "share": 0.5, "concerns": [],
        }]
        assert normalised["key_quotes"] == []

    def test_normalise_themes_drops_garbage_elements(self):
        raw = [
            {"theme": "Valid", "weight": 0.5, "evidence_step": 3},
            "a bare string, not a dict",
            {"theme": "", "weight": 0.5},  # empty theme
            {"weight": 0.5},  # missing theme
            {"theme": "NoWeight"},  # missing weight → defaults to 0
            None,
            {"theme": "Clamped", "weight": 99.0, "evidence_step": "not-int"},
        ]
        out = CommunityOpinionService._normalise_themes(raw)
        assert len(out) == 3
        assert out[0] == {"theme": "Valid", "weight": 0.5, "evidence_step": 3}
        # Missing weight coerces to 0.0, missing evidence_step to 0
        assert out[1] == {
            "theme": "NoWeight", "weight": 0.0, "evidence_step": 0,
        }
        # Out-of-range weight is clamped, non-int step coerces to 0
        assert out[2] == {
            "theme": "Clamped", "weight": 1.0, "evidence_step": 0,
        }

    def test_normalise_themes_handles_non_list(self):
        # Small LLM sometimes returns a string or a dict instead of a list
        assert CommunityOpinionService._normalise_themes("themes go here") == []
        assert CommunityOpinionService._normalise_themes({"theme": "x"}) == []
        assert CommunityOpinionService._normalise_themes(None) == []

    def test_normalise_divisions_drops_garbage_elements(self):
        raw = [
            {"faction": "A", "share": 0.4, "concerns": ["cost", "trust"]},
            {"faction": "", "share": 0.3},  # empty faction
            "not a dict",
            {"share": 0.5},  # missing faction
            # Concerns must be a list of non-empty strings; mixed junk filtered
            {
                "faction": "B",
                "share": 0.3,
                "concerns": ["ok", "", None, 42, "also-ok"],
            },
        ]
        out = CommunityOpinionService._normalise_divisions(raw)
        assert len(out) == 2
        assert out[0]["faction"] == "A"
        assert out[0]["concerns"] == ["cost", "trust"]
        assert out[1]["concerns"] == ["ok", "also-ok"]

    def test_normalise_divisions_drops_non_list_concerns(self):
        raw = [{"faction": "A", "share": 0.5, "concerns": "a single string"}]
        out = CommunityOpinionService._normalise_divisions(raw)
        # Non-list concerns → empty list, but faction is still valid
        assert out == [{"faction": "A", "share": 0.5, "concerns": []}]

    def test_normalise_key_quotes_requires_agent_id_and_content(self):
        raw = [
            {"agent_id": "abc", "content": "hello", "step": 3},
            {"agent_id": "", "content": "missing id"},
            {"agent_id": "xyz", "content": ""},
            {"agent_id": "xyz", "content": "ok", "step": "nan"},
            "bare string",
            None,
        ]
        out = CommunityOpinionService._normalise_key_quotes(raw)
        assert len(out) == 2
        assert out[0] == {"agent_id": "abc", "content": "hello", "step": 3}
        # Non-int step coerces to 0
        assert out[1] == {"agent_id": "xyz", "content": "ok", "step": 0}


# ===========================================================================
# Deadlock retry path
# ===========================================================================


class _FakeOrig:
    """Mimics asyncpg.exceptions.DeadlockDetectedError enough for the
    ``sqlstate`` attribute lookup used by the retry helper."""

    def __init__(self, sqlstate: str) -> None:
        self.sqlstate = sqlstate


def _make_deadlock_error() -> Exception:
    """Construct a real ``sqlalchemy.exc.DBAPIError`` with ``orig.sqlstate``
    set to Postgres' deadlock code. Calling ``DBAPIError()`` directly is
    fussy — easier to use the two-argument form that sets ``orig``."""
    from sqlalchemy.exc import DBAPIError
    err = DBAPIError("fake", None, Exception("deadlock"))
    err.orig = _FakeOrig("40P01")
    return err


class _RetrySession:
    """Fake session that raises N deadlocks on commit before succeeding."""

    def __init__(self, deadlocks_before_success: int) -> None:
        self._remaining_deadlocks = deadlocks_before_success
        self.commit_attempts = 0
        self.rollbacks = 0
        self.added: list[Any] = []
        self.refreshed: list[Any] = []

    def add(self, row: Any) -> None:
        self.added.append(row)

    async def commit(self) -> None:
        self.commit_attempts += 1
        if self._remaining_deadlocks > 0:
            self._remaining_deadlocks -= 1
            raise _make_deadlock_error()

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, row: Any) -> None:
        self.refreshed.append(row)


def _make_row() -> Any:
    from app.models.community_opinion import CommunityOpinion
    return CommunityOpinion(
        opinion_id=uuid4(),
        simulation_id=uuid4(),
        community_id="c1",
        step=0,
        themes=[], divisions=[], sentiment_trend="stable",
        dominant_emotions=[], key_quotes=[], summary="",
        source_step_count=0, source_agent_count=0,
        llm_provider="x", llm_model="y",
        llm_cost_usd=0.0, is_fallback_stub=False,
    )


def _unused_service() -> CommunityOpinionService:
    """Build a service instance whose orchestrator/gateway are never
    touched — the retry tests only exercise the persist helper."""
    return CommunityOpinionService(
        orchestrator=StubOrchestrator(state=None),
        gateway=StubGateway(content="{}"),
    )


class TestPersistRetry:
    """SPEC: 25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis"""

    @pytest.mark.asyncio
    async def test_retries_on_deadlock_then_succeeds(self):
        service = _unused_service()
        session = _RetrySession(deadlocks_before_success=2)
        row = _make_row()
        result = await service._persist_row_with_retry(row, session)
        # 2 deadlocks + 1 success = 3 commit attempts
        assert session.commit_attempts == 3
        assert session.rollbacks == 2
        assert session.refreshed == [row]
        # Newly persisted row is returned unchanged
        assert result is row

    @pytest.mark.asyncio
    async def test_gives_up_after_max_attempts(self):
        from sqlalchemy.exc import DBAPIError
        service = _unused_service()
        session = _RetrySession(deadlocks_before_success=99)
        row = _make_row()
        with pytest.raises(DBAPIError):
            await service._persist_row_with_retry(
                row, session, max_attempts=3,
            )
        # All 3 attempts exhausted + final rollback before raise
        assert session.commit_attempts == 3
        assert session.rollbacks == 3


# ===========================================================================
# Unique-violation race path
# ===========================================================================


def _make_unique_violation_error() -> Exception:
    """Build a real ``IntegrityError`` with the Postgres unique_violation
    sqlstate (23505) — the error we want the retry helper to catch and
    convert into a "fetch the winner's row" path.
    """
    from sqlalchemy.exc import IntegrityError
    err = IntegrityError("fake", None, Exception("unique violation"))
    err.orig = _FakeOrig("23505")
    return err


class _UniqueViolationSession:
    """Session that raises a unique_violation on first commit, then
    returns a pre-seeded "winner" row when the retry helper asks for
    the cached one via ``execute(select(...))``.
    """

    def __init__(self, winner_row: Any) -> None:
        self._winner = winner_row
        self.commit_attempts = 0
        self.rollbacks = 0
        self.added: list[Any] = []
        self.refreshed: list[Any] = []

    class _Result:
        def __init__(self, row: Any) -> None:
            self._row = row

        def scalar_one_or_none(self) -> Any:
            return self._row

    def add(self, row: Any) -> None:
        self.added.append(row)

    async def commit(self) -> None:
        self.commit_attempts += 1
        raise _make_unique_violation_error()

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, row: Any) -> None:
        self.refreshed.append(row)

    async def execute(self, _stmt: Any) -> Any:
        return _UniqueViolationSession._Result(self._winner)


class TestPersistUniqueViolation:
    """SPEC: 25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis"""

    @pytest.mark.asyncio
    async def test_unique_violation_returns_winner_row(self):
        """When two writers race on (sim, community, step), the loser
        catches the 23505, re-reads the cache, and returns the winner's
        row instead of retrying."""
        service = _unused_service()
        winner_row = _make_row()  # Stand-in for the other writer's row
        session = _UniqueViolationSession(winner_row=winner_row)
        our_row = _make_row()

        result = await service._persist_row_with_retry(our_row, session)

        # Returned the WINNER's row, not ours
        assert result is winner_row
        assert result is not our_row
        # We attempted one commit, caught the violation, rolled back once
        assert session.commit_attempts == 1
        assert session.rollbacks == 1
        # We did not loop / retry — unique violations terminate immediately
        assert len(session.added) == 1

    @pytest.mark.asyncio
    async def test_unique_violation_no_winner_row_propagates(self):
        """If the constraint says a row exists but our own ``_find_cached``
        can't see it (transaction isolation quirk), re-raise rather than
        silently returning ``None``."""
        from sqlalchemy.exc import IntegrityError
        service = _unused_service()
        session = _UniqueViolationSession(winner_row=None)
        row = _make_row()

        with pytest.raises(IntegrityError):
            await service._persist_row_with_retry(row, session)
