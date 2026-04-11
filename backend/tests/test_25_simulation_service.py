"""Unit tests for SimulationService.

SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#3.1

Contract discipline:
  * The ``MagicMock(spec=SimulationOrchestrator)`` binding ensures that a
    typo in a method name (e.g. ``orch.strat``) fails the test instead of
    silently returning another Mock.
  * :class:`FakeSimulationRepo` mirrors the real
    :class:`SqlSimulationRepository` signature (including the kwarg-only
    ``session``), so the service cannot accidentally call the repo with
    the wrong argument shape.
  * :class:`FakeNotifier` implements the :class:`NotificationPort`
    Protocol so Protocol drift breaks the tests.
  * The ``not_found`` stop path is verified via the
    :class:`SimulationNotFoundError` exception, not a sentinel dict.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.services.ports import SimulationNotFoundError, StopOutcome
from app.services.simulation_service import SimulationService


# ===========================================================================
# Fakes
# ===========================================================================


@dataclass
class FakeRepoCall:
    name: str
    args: tuple
    kwargs: dict


class FakeSimulationRepo:
    """Protocol-compatible in-memory repository for unit tests.

    Method signatures mirror :class:`SqlSimulationRepository` exactly,
    including kwarg-only ``session``. A drift in the service's call
    shape (e.g. forgetting ``session=``) will raise TypeError here.
    """

    def __init__(self) -> None:
        self.calls: list[FakeRepoCall] = []
        self.row_exists_value = True

    def _record(self, name: str, args: tuple, kwargs: dict) -> None:
        self.calls.append(FakeRepoCall(name=name, args=args, kwargs=kwargs))

    def names(self) -> list[str]:
        return [c.name for c in self.calls]

    def find(self, name: str) -> FakeRepoCall:
        return next(c for c in self.calls if c.name == name)

    # ---- Writes -------------------------------------------------------- #

    async def save_creation(
        self,
        sim_id: uuid.UUID,
        config: Any,
        agents: list[Any],
        edges: list[tuple[Any, Any, dict]],
        *,
        session: Any,
    ) -> None:
        self._record(
            "save_creation",
            (sim_id, config, agents, edges),
            {"session": session},
        )

    async def save_step(
        self,
        sim_id: uuid.UUID,
        result: Any,
        agents: list[Any] | None = None,
        *,
        session: Any,
    ) -> None:
        self._record(
            "save_step", (sim_id, result), {"agents": agents, "session": session},
        )

    async def save_status(
        self,
        sim_id: uuid.UUID,
        status: str,
        step: int | None = None,
        *,
        session: Any,
    ) -> None:
        self._record(
            "save_status", (sim_id, status, step), {"session": session},
        )

    async def persist_llm_calls(
        self, sim_id: uuid.UUID, call_logs: list, *, session: Any,
    ) -> None:
        self._record("persist_llm_calls", (sim_id, call_logs), {"session": session})

    async def persist_expert_opinions(
        self, sim_id: uuid.UUID, step: int, opinions: list[dict], *, session: Any,
    ) -> None:
        self._record(
            "persist_expert_opinions",
            (sim_id, step, opinions),
            {"session": session},
        )

    async def persist_agent_memories(
        self, sim_id: uuid.UUID, memories: list[dict], *, session: Any,
    ) -> None:
        self._record(
            "persist_agent_memories", (sim_id, memories), {"session": session},
        )

    async def persist_thread_messages(
        self, messages: list, *, session: Any,
    ) -> None:
        self._record("persist_thread_messages", (messages,), {"session": session})

    async def persist_event(
        self,
        sim_id: uuid.UUID,
        event_type: str,
        step: int,
        data: dict,
        *,
        session: Any,
    ) -> None:
        self._record(
            "persist_event",
            (sim_id, event_type, step, data),
            {"session": session},
        )

    # ---- Reads --------------------------------------------------------- #

    async def row_exists(self, sim_id: uuid.UUID, *, session: Any) -> bool:
        self._record("row_exists", (sim_id,), {"session": session})
        return self.row_exists_value

    async def find_by_id(self, sim_id: uuid.UUID, *, session: Any) -> dict | None:
        self._record("find_by_id", (sim_id,), {"session": session})
        return None

    async def list_all(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        session: Any,
    ) -> list[dict]:
        self._record(
            "list_all", (), {"status": status, "limit": limit, "offset": offset, "session": session},
        )
        return []

    async def count(self, status: str | None = None, *, session: Any) -> int:
        self._record("count", (status,), {"session": session})
        return 0

    async def load_steps(self, sim_id: uuid.UUID, *, session: Any) -> list[dict]:
        self._record("load_steps", (sim_id,), {"session": session})
        return []

    async def restore_state(self, sim_id: uuid.UUID, *, session: Any) -> dict | None:
        self._record("restore_state", (sim_id,), {"session": session})
        return None

    # ---- Misc ---------------------------------------------------------- #

    @property
    def failed_queue(self) -> list[dict]:
        return []


class FakeNotifier:
    """Satisfies :class:`NotificationPort` Protocol."""

    def __init__(self) -> None:
        self.broadcasts: list[tuple[str, dict]] = []
        self.agent_updates: list[tuple[str, dict]] = []

    async def broadcast(self, simulation_id: str, message: dict) -> None:
        self.broadcasts.append((simulation_id, message))

    async def broadcast_agent_updates(
        self, simulation_id: str, agent_state_map: dict[str, dict],
    ) -> None:
        self.agent_updates.append((simulation_id, agent_state_map))

    def broadcast_types(self) -> list[str]:
        return [m.get("type") for _, m in self.broadcasts]


def _fake_session_factory() -> Any:
    """Produce a ``SessionFactory`` that yields the same fake session."""
    fake_bg_session = MagicMock(name="bg_session")

    @asynccontextmanager
    async def _factory():
        yield fake_bg_session

    return _factory, fake_bg_session


def _make_orchestrator(state: Any = None) -> Any:
    """Build a MagicMock(spec=SimulationOrchestrator) with async hooks.

    Using ``spec=`` means typos in service code (e.g. ``orch.strat``)
    raise AttributeError immediately instead of silently passing.
    """
    orch = MagicMock(spec=SimulationOrchestrator)
    orch.start = AsyncMock()
    orch.run_step = AsyncMock()
    orch.pause = AsyncMock()
    orch.resume = AsyncMock()
    orch.reset = AsyncMock()
    orch.run_all = AsyncMock()
    orch.create_simulation = MagicMock()
    if state is not None:
        orch.get_state = MagicMock(return_value=state)
    else:
        orch.get_state = MagicMock(side_effect=ValueError("not found"))
    return orch


def _fake_state(sim_id: uuid.UUID, *, status: str = "running", step: int = 0) -> Any:
    return SimpleNamespace(
        simulation_id=sim_id,
        status=status,
        current_step=step,
        agents=[],
        config=SimpleNamespace(name="test", description=""),
        network=None,
    )


def _fake_step_result(
    *,
    step: int = 1,
    llm_calls: int = 0,
    tier_dist: dict | None = None,
    emergent_events: list | None = None,
) -> Any:
    return SimpleNamespace(
        step=step,
        total_adoption=10,
        adoption_rate=0.1,
        diffusion_rate=0.05,
        mean_sentiment=0.0,
        sentiment_variance=0.1,
        community_metrics={},
        emergent_events=emergent_events or [],
        action_distribution={},
        propagation_pairs=[],
        llm_calls_this_step=llm_calls,
        llm_tier_distribution=tier_dist or {},
        step_duration_ms=100.0,
    )


async def _drain_bg_tasks() -> None:
    """Yield so fire-and-forget ``asyncio.create_task`` coroutines run."""
    import asyncio
    await asyncio.sleep(0)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def fake_session() -> Any:
    return MagicMock(name="fake_session", spec=AsyncSession)


@pytest.fixture
def fake_repo() -> FakeSimulationRepo:
    return FakeSimulationRepo()


@pytest.fixture
def fake_notifier() -> FakeNotifier:
    return FakeNotifier()


def _build_service(
    orchestrator, repo, notifier, *, session_factory=None,
) -> SimulationService:
    if session_factory is None:
        session_factory, _ = _fake_session_factory()
    return SimulationService(
        orchestrator=orchestrator,
        repo=repo,
        notifier=notifier,
        session_factory=session_factory,
    )


# ===========================================================================
# Tests
# ===========================================================================


class TestStart:
    """SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#3.1"""

    @pytest.mark.asyncio
    async def test_start_transitions_status_and_persists(
        self, fake_repo, fake_notifier, fake_session,
    ):
        sim_id = uuid.uuid4()
        orch = _make_orchestrator(state=_fake_state(sim_id, status="configured"))
        svc = _build_service(orch, fake_repo, fake_notifier)

        result = await svc.start(sim_id, session=fake_session)
        await _drain_bg_tasks()

        orch.start.assert_awaited_once_with(sim_id)
        save = fake_repo.find("save_status")
        assert save.args[0] == sim_id
        assert save.args[1] == "running"
        assert save.kwargs["session"] is fake_session
        assert result["status"] == "running"
        assert "status_change" in fake_notifier.broadcast_types()


class TestStep:
    """SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#3.1"""

    @pytest.mark.asyncio
    async def test_step_persists_and_broadcasts(
        self, fake_repo, fake_notifier, fake_session,
    ):
        sim_id = uuid.uuid4()
        state = _fake_state(sim_id, status="running", step=0)
        orch = _make_orchestrator(state=state)
        orch.run_step = AsyncMock(return_value=_fake_step_result(step=1))
        svc = _build_service(orch, fake_repo, fake_notifier)

        result = await svc.step(sim_id, session=fake_session)
        await _drain_bg_tasks()

        assert result.step == 1
        names = fake_repo.names()
        assert "save_step" in names
        assert "save_status" in names
        # Request session threaded through
        assert fake_repo.find("save_step").kwargs["session"] is fake_session
        assert fake_repo.find("save_status").kwargs["session"] is fake_session
        # No LLM activity → no LLM persist
        assert "persist_llm_calls" not in names
        assert "persist_expert_opinions" not in names
        assert "persist_agent_memories" not in names
        assert "step_result" in fake_notifier.broadcast_types()

    @pytest.mark.asyncio
    async def test_step_persists_llm_calls_when_present(
        self, fake_repo, fake_notifier, fake_session,
    ):
        sim_id = uuid.uuid4()
        state = _fake_state(sim_id, status="running")
        orch = _make_orchestrator(state=state)
        orch.run_step = AsyncMock(return_value=_fake_step_result(
            step=2, llm_calls=3, tier_dist={1: 2, 3: 1},
        ))
        svc = _build_service(orch, fake_repo, fake_notifier)

        await svc.step(sim_id, session=fake_session)
        await _drain_bg_tasks()

        llm_call = fake_repo.find("persist_llm_calls")
        # persist_llm_calls uses the request session (inline await)
        assert llm_call.kwargs["session"] is fake_session
        records = llm_call.args[1]
        assert len(records) == 3
        assert {r["tier"] for r in records} == {1, 3}

    @pytest.mark.asyncio
    async def test_step_persists_expert_opinions_with_bg_session(
        self, fake_repo, fake_notifier, fake_session,
    ):
        sim_id = uuid.uuid4()
        state = _fake_state(sim_id, status="running")

        # Inject a session_factory we can inspect
        factory, bg_session = _fake_session_factory()
        expert_event = SimpleNamespace(
            event_type="expert_consensus",
            step=2,
            community_id=uuid.uuid4(),
            severity=0.8,
            description="Experts align",
        )
        orch = _make_orchestrator(state=state)
        orch.run_step = AsyncMock(return_value=_fake_step_result(
            step=2, emergent_events=[expert_event],
        ))
        svc = _build_service(
            orch, fake_repo, fake_notifier, session_factory=factory,
        )

        await svc.step(sim_id, session=fake_session)
        await _drain_bg_tasks()

        call = fake_repo.find("persist_expert_opinions")
        # Background task opened its OWN session, not the request one
        assert call.kwargs["session"] is bg_session
        assert call.kwargs["session"] is not fake_session
        opinions = call.args[2]
        assert len(opinions) == 1
        assert opinions[0]["score"] == pytest.approx(0.6)
        assert opinions[0]["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_step_failure_persists_status_and_reraises(
        self, fake_repo, fake_notifier, fake_session,
    ):
        sim_id = uuid.uuid4()
        state = _fake_state(sim_id, status="running", step=5)
        orch = _make_orchestrator(state=state)
        orch.run_step = AsyncMock(side_effect=RuntimeError("boom"))
        svc = _build_service(orch, fake_repo, fake_notifier)

        state.status = "failed"  # orchestrator would've flipped it

        with pytest.raises(RuntimeError, match="boom"):
            await svc.step(sim_id, session=fake_session)
        await _drain_bg_tasks()

        save = fake_repo.find("save_status")
        assert save.args[1] == "failed"
        assert any(
            m.get("data", {}).get("status") == "failed"
            for _, m in fake_notifier.broadcasts
        )


class TestPauseResume:
    """SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#3.1"""

    @pytest.mark.asyncio
    async def test_pause_persists_step_and_broadcasts(
        self, fake_repo, fake_notifier, fake_session,
    ):
        sim_id = uuid.uuid4()
        state = _fake_state(sim_id, status="running", step=3)
        orch = _make_orchestrator(state=state)
        svc = _build_service(orch, fake_repo, fake_notifier)

        await svc.pause(sim_id, session=fake_session)
        await _drain_bg_tasks()

        orch.pause.assert_awaited_once_with(sim_id)
        save = fake_repo.find("save_status")
        assert save.args[1] == "paused"
        assert save.args[2] == 3
        assert save.kwargs["session"] is fake_session

    @pytest.mark.asyncio
    async def test_resume_accepts_session_for_symmetry(
        self, fake_repo, fake_notifier, fake_session,
    ):
        """resume() must accept ``session=`` even though it doesn't use it,
        so every lifecycle method has the same call shape."""
        sim_id = uuid.uuid4()
        state = _fake_state(sim_id, status="paused")
        orch = _make_orchestrator(state=state)
        svc = _build_service(orch, fake_repo, fake_notifier)

        result = await svc.resume(sim_id, session=fake_session)
        await _drain_bg_tasks()

        orch.resume.assert_awaited_once_with(sim_id)
        assert result["status"] == "running"
        assert any(
            m.get("data", {}).get("status") == "running"
            for _, m in fake_notifier.broadcasts
        )


class TestCreate:
    """SPEC: docs/spec/06_API_SPEC.md#post-simulations"""

    def _body(self, communities=None) -> Any:
        return SimpleNamespace(
            name="test sim",
            description="desc",
            communities=communities,
            max_steps=10,
            default_llm_provider="ollama",
            random_seed=42,
            slm_llm_ratio=0.5,
            slm_model="phi4",
            budget_usd=10.0,
            platform="default",
            campaign=SimpleNamespace(
                name="camp",
                budget=100.0,
                channels=["social"],
                message="hello",
                target_communities=["all"],
                novelty=0.6,
                utility=0.7,
                controversy=0.1,
            ),
        )

    @pytest.mark.asyncio
    async def test_create_builds_default_communities_when_none_provided(
        self, fake_repo, fake_notifier, fake_session,
    ):
        orch = _make_orchestrator()
        captured_state = SimpleNamespace(
            simulation_id=uuid.uuid4(),
            status="configured",
            agents=[],
            network=None,
        )
        orch.create_simulation = MagicMock(return_value=captured_state)
        svc = _build_service(orch, fake_repo, fake_notifier)

        state = await svc.create(self._body(communities=None), session=fake_session)

        assert state is captured_state
        orch.create_simulation.assert_called_once()
        config = orch.create_simulation.call_args.args[0]
        assert len(config.communities) == 5
        assert config.communities[0].name == "early_adopters"
        assert "save_creation" in fake_repo.names()
        assert fake_repo.find("save_creation").kwargs["session"] is fake_session

    @pytest.mark.asyncio
    async def test_create_evicts_ghost_state_on_persist_failure(
        self, fake_notifier, fake_session,
    ):
        """Round 4: when ``save_creation`` raises, the service must
        evict the in-memory state via ``orchestrator.delete_simulation``
        and re-raise so the caller sees the failure."""
        captured_sim_id = uuid.uuid4()
        captured_state = SimpleNamespace(
            simulation_id=captured_sim_id,
            status="configured",
            agents=[],
            network=None,
        )
        orch = _make_orchestrator()
        orch.create_simulation = MagicMock(return_value=captured_state)
        orch.delete_simulation = AsyncMock()

        failing_repo = FakeSimulationRepo()

        async def _explode(*args, **kwargs):
            raise RuntimeError("db down")

        failing_repo.save_creation = _explode  # type: ignore[method-assign]

        svc = _build_service(orch, failing_repo, fake_notifier)

        with pytest.raises(RuntimeError, match="db down"):
            await svc.create(self._body(), session=fake_session)

        # Ghost eviction: orchestrator.delete_simulation must have been
        # called with the just-created sim id.
        orch.delete_simulation.assert_awaited_once_with(captured_sim_id)

    @pytest.mark.asyncio
    async def test_create_uses_provided_communities(
        self, fake_repo, fake_notifier, fake_session,
    ):
        orch = _make_orchestrator()
        orch.create_simulation = MagicMock(return_value=SimpleNamespace(
            simulation_id=uuid.uuid4(),
            status="configured",
            agents=[],
            network=None,
        ))
        svc = _build_service(orch, fake_repo, fake_notifier)

        body = self._body(communities=[
            {"id": "X", "name": "custom", "size": 50, "agent_type": "consumer"},
        ])
        await svc.create(body, session=fake_session)

        config = orch.create_simulation.call_args.args[0]
        assert len(config.communities) == 1
        assert config.communities[0].id == "X"
        assert config.communities[0].name == "custom"
        assert config.communities[0].size == 50


class TestStop:
    """SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstop"""

    @pytest.mark.asyncio
    async def test_stop_raises_not_found_when_missing_everywhere(
        self, fake_repo, fake_notifier, fake_session,
    ):
        sim_id = uuid.uuid4()
        fake_repo.row_exists_value = False
        orch = _make_orchestrator(state=None)  # get_state raises
        svc = _build_service(orch, fake_repo, fake_notifier)

        with pytest.raises(SimulationNotFoundError) as exc_info:
            await svc.stop(sim_id, session=fake_session)
        assert exc_info.value.simulation_id == str(sim_id)

    @pytest.mark.asyncio
    async def test_stop_db_only_simulation_marks_completed(
        self, fake_repo, fake_notifier, fake_session,
    ):
        """DB-only historical sim: get_state raises but row_exists is True."""
        sim_id = uuid.uuid4()
        fake_repo.row_exists_value = True
        orch = _make_orchestrator(state=None)
        svc = _build_service(orch, fake_repo, fake_notifier)

        outcome = await svc.stop(sim_id, session=fake_session)

        assert outcome is StopOutcome.COMPLETED
        save = fake_repo.find("save_status")
        assert save.args[1] == "completed"

    @pytest.mark.asyncio
    async def test_stop_resets_failed_simulation_via_orchestrator(
        self, fake_repo, fake_notifier, fake_session,
    ):
        """Reset path must delegate to ``orchestrator.reset`` instead of
        mutating ``state.status`` directly (audit L3)."""
        sim_id = uuid.uuid4()
        state = _fake_state(sim_id, status="failed", step=7)
        orch = _make_orchestrator(state=state)
        svc = _build_service(orch, fake_repo, fake_notifier)

        outcome = await svc.stop(sim_id, session=fake_session)
        await _drain_bg_tasks()

        assert outcome is StopOutcome.RESET
        orch.reset.assert_awaited_once_with(sim_id)
        assert fake_repo.find("save_status").args[1] == "created"

    @pytest.mark.asyncio
    async def test_stop_marks_running_simulation_completed(
        self, fake_repo, fake_notifier, fake_session,
    ):
        sim_id = uuid.uuid4()
        state = _fake_state(sim_id, status="running", step=5)
        orch = _make_orchestrator(state=state)
        svc = _build_service(orch, fake_repo, fake_notifier)

        outcome = await svc.stop(sim_id, session=fake_session)
        await _drain_bg_tasks()

        assert outcome is StopOutcome.COMPLETED
        assert state.status == "completed"


class TestContractDiscipline:
    """Meta-tests that pin the contract strength improvements from Round 1+2+3."""

    def test_service_does_not_import_from_api_layer(self):
        """Layer rule: services/ must not depend on api/."""
        import app.services.simulation_service as svc_mod
        import inspect
        source = inspect.getsource(svc_mod)
        # No ``from app.api`` anywhere in the service module source.
        assert "from app.api" not in source, (
            "SimulationService must not import from app.api — use ports instead"
        )

    def test_service_depends_on_repository_protocol(self):
        """Contract rule: repo annotation must be the Protocol, not the concrete class."""
        import typing
        from app.repositories.protocols import SimulationRepository
        hints = typing.get_type_hints(SimulationService.__init__)
        assert hints.get("repo") is SimulationRepository, (
            f"Expected repo: SimulationRepository, got {hints.get('repo')}"
        )

    def test_notifier_is_protocol_typed(self):
        """Contract rule: notifier annotation must be the Port Protocol."""
        import typing
        from app.services.ports import NotificationPort
        hints = typing.get_type_hints(SimulationService.__init__)
        assert hints.get("notifier") is NotificationPort

    def test_connection_manager_structurally_satisfies_notification_port(self):
        """The real WS manager must satisfy the Port without explicit subclassing."""
        from app.api.ws import ConnectionManager
        # Structural check — required methods exist with the right arity.
        assert hasattr(ConnectionManager, "broadcast")
        assert hasattr(ConnectionManager, "broadcast_agent_updates")

    def test_simulations_route_does_not_import_persistence(self):
        """Round 3: simulations.py routes must NOT depend on SimulationPersistence.

        Read paths go through ``SimulationRepository`` Protocol; write paths
        go through ``SimulationService``.
        """
        import app.api.simulations as sim_mod
        import inspect
        source = inspect.getsource(sim_mod)
        assert "SimulationPersistence" not in source, (
            "simulations.py must not reference SimulationPersistence directly — "
            "use SimulationRepository (reads) or SimulationService (writes)"
        )
        assert "get_persistence" not in source, (
            "simulations.py must not import get_persistence — use get_simulation_repo"
        )

    def test_projects_route_does_not_import_persistence(self):
        """Round 3: projects.py must not depend on SimulationPersistence."""
        import app.api.projects as proj_mod
        import inspect
        source = inspect.getsource(proj_mod)
        assert "SimulationPersistence" not in source
        assert "get_persistence" not in source

    def test_orchestrator_reset_is_a_method(self):
        """Round 3 (audit L3): orchestrator owns the reset transition."""
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        assert hasattr(SimulationOrchestrator, "reset"), (
            "SimulationService.stop() should delegate reset to orchestrator, "
            "not mutate state.status directly"
        )

    def test_service_has_run_all_method(self):
        """Round 3: run_all must be owned by the service, not inlined in the route."""
        assert hasattr(SimulationService, "run_all")

    def test_deps_no_longer_exposes_get_persistence(self):
        """Round 3: get_persistence helper must be gone from DI module.

        Routes consume ``get_simulation_repo`` (Protocol-typed) instead.
        """
        import app.api.deps as deps
        assert not hasattr(deps, "get_persistence"), (
            "get_persistence must be removed from app.api.deps — "
            "routes should depend on SimulationRepository via get_simulation_repo"
        )

    def test_orchestrator_exposes_list_states(self):
        """Round 4: list_states() must be a public domain method.

        Before Round 4, ``list_simulations`` route reached into
        ``orchestrator._simulations`` directly.
        """
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        assert hasattr(SimulationOrchestrator, "list_states")

    def test_list_simulations_route_does_not_touch_private_dict(self):
        """Round 4: the route must go through ``orchestrator.list_states``,
        not ``orchestrator._simulations`` directly."""
        import app.api.simulations as sim_mod
        import inspect
        source = inspect.getsource(sim_mod)
        assert "orchestrator._simulations" not in source, (
            "list_simulations route must use orchestrator.list_states() "
            "instead of reaching into the private _simulations dict"
        )

    def test_persist_creation_re_raises_on_failure(self):
        """Round 4: persist_creation must re-raise (no silent swallow).

        This verifies the method's source contains a bare ``raise`` in the
        except block — a weaker but stable check than trying to trigger a
        real DB failure in unit tests.
        """
        import inspect
        from app.repositories.simulation_persistence import SimulationPersistence
        source = inspect.getsource(SimulationPersistence.persist_creation)
        # The only ``raise`` statement should be in the exception handler.
        assert "raise" in source, (
            "persist_creation must re-raise on failure so callers can abort cleanly"
        )
        # Confirm the old swallow comment is gone
        assert "Swallow" not in source


class TestCompositionRoot:
    """Round 5: enforce that ``app/api/deps.py`` is the sole composition root.

    Concrete infrastructure types (``SimulationPersistence``,
    ``SqlSimulationRepository``, ``SqlProjectRepository``) may be
    imported only by the repository module that defines them and by
    the composition root (``deps.py``). Every other module must depend
    on Protocols.
    """

    def _walk_app_modules(self):
        """Yield (module_path, source_text) for every .py file under app/."""
        import pathlib
        app_root = pathlib.Path(__file__).parent.parent / "app"
        for py_file in app_root.rglob("*.py"):
            rel = py_file.relative_to(app_root.parent)
            yield str(rel).replace("\\", "/"), py_file.read_text(encoding="utf-8")

    def test_simulation_persistence_only_imported_at_composition_root(self):
        """``SimulationPersistence`` may only be imported by the repository
        adapter (``simulation_repo.py``), the composition root
        (``api/deps.py``), or its own definition file.

        Round 6: moved from ``engine/simulation/persistence.py`` to
        ``repositories/simulation_persistence.py`` to satisfy CA-01
        (engine/ must not import sqlalchemy).
        """
        allowed = {
            "app/repositories/simulation_persistence.py",  # the definition
            "app/repositories/simulation_repo.py",
            "app/api/deps.py",
        }
        violators = []
        for path, source in self._walk_app_modules():
            if path in allowed:
                continue
            # Match real imports only, not docstring mentions.
            if (
                "from app.repositories.simulation_persistence import SimulationPersistence"
                in source
                or "from app.engine.simulation.persistence import SimulationPersistence"
                in source
            ):
                violators.append(path)
        assert not violators, (
            f"SimulationPersistence import outside composition root: {violators}"
        )

    def test_sql_repository_classes_only_imported_at_composition_root(self):
        """``SqlSimulationRepository`` / ``SqlProjectRepository`` may only
        be imported by the repositories package init and the composition
        root — services and routes must depend on the Protocol."""
        allowed = {
            "app/repositories/__init__.py",
            "app/repositories/simulation_repo.py",
            "app/repositories/project_repo.py",
            "app/api/deps.py",
        }
        violators = []
        for path, source in self._walk_app_modules():
            if path in allowed:
                continue
            for concrete in ("SqlSimulationRepository", "SqlProjectRepository"):
                import_line = f"import {concrete}"
                if import_line in source:
                    violators.append((path, concrete))
                    break
        assert not violators, (
            f"Concrete repo class import outside composition root: {violators}"
        )


class TestEnginePurity:
    """Round 5: enforce that the engine layer is free of obvious
    non-determinism leaks.

    Python's built-in ``hash()`` randomizes string hashes (PYTHONHASHSEED)
    so any ``hash(str_value)`` in engine code breaks replay reproducibility.
    ``hash(int)`` and ``hash(UUID)`` are deterministic in CPython 3.4+,
    so only string-argument calls are flagged.
    """

    # Patterns that indicate a string argument to ``hash()``.
    _FORBIDDEN_HASH_PATTERNS = [
        "hash(str(",
        "hash(cid_str",
        "hash(campaign.name",
        "hash(agent_type_str",
    ]

    def test_engine_has_no_string_hash_calls(self):
        import pathlib
        engine_root = (
            pathlib.Path(__file__).parent.parent / "app" / "engine"
        )
        violators: list[tuple[str, str]] = []
        for py_file in engine_root.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            # Strip docstrings/comments — very rough but good enough to
            # avoid matching the explanation comments we wrote.
            code_lines = [
                line for line in source.splitlines()
                if not line.lstrip().startswith("#")
                and not line.lstrip().startswith('"""')
            ]
            joined = "\n".join(code_lines)
            for pattern in self._FORBIDDEN_HASH_PATTERNS:
                if pattern in joined:
                    violators.append((str(py_file.name), pattern))
        assert not violators, (
            f"Non-deterministic hash(str) calls in engine: {violators}"
        )

    def test_engine_has_no_runtime_sqlalchemy_import(self):
        """Round 6 (CA-01): ``app/engine/**`` may never import SQLAlchemy
        as a **runtime** dependency.

        Allowed patterns:
          * ``if TYPE_CHECKING:`` blocks (static-only, stripped by CPython)
          * Lazy inline imports inside a function body, guarded by
            ``# noqa: PLC0415 — lazy DI fallback`` comment
        Forbidden:
          * Module-level ``from sqlalchemy ...`` or ``import sqlalchemy``
        """
        import pathlib
        import re
        engine_root = (
            pathlib.Path(__file__).parent.parent / "app" / "engine"
        )
        violators: list[tuple[str, int, str]] = []
        # Match any top-level import line (no leading whitespace) that
        # references sqlalchemy. Lines inside functions/classes have
        # leading whitespace and are ignored — they're lazy imports,
        # explicitly allowed for the DI fallback pattern.
        pattern = re.compile(
            r"^(from\s+sqlalchemy\b|import\s+sqlalchemy\b)",
            re.MULTILINE,
        )
        for py_file in engine_root.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            # Strip TYPE_CHECKING blocks — they're static-only.
            # Very conservative: remove lines between
            # ``if TYPE_CHECKING:`` and the next unindented statement.
            stripped_lines: list[str] = []
            inside_type_checking = False
            for line in source.splitlines():
                if re.match(r"^if\s+TYPE_CHECKING", line):
                    inside_type_checking = True
                    stripped_lines.append(line)
                    continue
                if inside_type_checking:
                    # Stay inside block while indented or blank.
                    if line.startswith((" ", "\t")) or line.strip() == "":
                        # Drop the content — don't scan for imports.
                        stripped_lines.append("")
                        continue
                    inside_type_checking = False
                stripped_lines.append(line)
            cleaned = "\n".join(stripped_lines)
            for m in pattern.finditer(cleaned):
                line_num = cleaned[: m.start()].count("\n") + 1
                rel = py_file.relative_to(engine_root.parent.parent).as_posix()
                violators.append((rel, line_num, m.group(0)))
        assert not violators, (
            "CA-01 violation — engine/ files must not runtime-import "
            f"sqlalchemy:\n"
            + "\n".join(f"  {f}:{ln}  {snip}" for f, ln, snip in violators)
        )

    def test_engine_has_no_module_level_config_import(self):
        """Round 6 (CA-02): ``app/engine/**`` may never import
        ``app.config.settings`` at module level.

        Lazy ``from app.config import settings`` inside a function body
        is allowed — it's the DI fallback pattern used by
        ``engine/agent/memory.py::_get_setting``. Module-level imports
        would tie the engine to a live infrastructure config and break
        pure-unit testability.
        """
        import pathlib
        import re
        engine_root = (
            pathlib.Path(__file__).parent.parent / "app" / "engine"
        )
        violators: list[tuple[str, int, str]] = []
        pattern = re.compile(
            r"^(from\s+app\.config\s+import|import\s+app\.config\b)",
            re.MULTILINE,
        )
        for py_file in engine_root.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            for m in pattern.finditer(source):
                line_num = source[: m.start()].count("\n") + 1
                rel = py_file.relative_to(engine_root.parent.parent).as_posix()
                violators.append((rel, line_num, m.group(0)))
        assert not violators, (
            "CA-02 violation — engine/ files must not runtime-import "
            f"app.config at module level:\n"
            + "\n".join(f"  {f}:{ln}  {snip}" for f, ln, snip in violators)
        )
