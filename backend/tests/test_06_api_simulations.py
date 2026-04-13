"""Simulation endpoint tests.
Auto-generated from SPEC: docs/spec/06_API_SPEC.md#2-simulation-endpoints
SPEC Version: 0.1.0
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api import deps as _deps_mod


@pytest.fixture(autouse=True)
def _reset_orchestrator():
    """Reset the orchestrator singleton between tests."""
    _deps_mod._orchestrator = None
    yield
    _deps_mod._orchestrator = None


def _valid_create_body() -> dict:
    return {
        "name": "Test Sim",
        "campaign": {
            "name": "Camp",
            "budget": 1000,
            "channels": ["sns"],
            "message": "Hello",
        },
    }


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def sim_id(client: AsyncClient) -> str:
    resp = await client.post("/api/v1/simulations/", json=_valid_create_body())
    return resp.json()["simulation_id"]


@pytest.mark.phase6
class TestCreateSimulation:
    """SPEC: 06_API_SPEC.md#post-simulations"""

    async def test_201_on_valid_body(self, client: AsyncClient):
        resp = await client.post("/api/v1/simulations/", json=_valid_create_body())
        assert resp.status_code == 201

    async def test_422_on_missing_campaign(self, client: AsyncClient):
        resp = await client.post("/api/v1/simulations/", json={"name": "No campaign"})
        assert resp.status_code == 422

    async def test_response_fields(self, client: AsyncClient):
        resp = await client.post("/api/v1/simulations/", json=_valid_create_body())
        data = resp.json()
        assert "simulation_id" in data
        assert data["status"] == "configured"
        assert "total_agents" in data
        assert data["total_agents"] == 1000  # default communities sum to 1000
        assert "network_metrics" in data
        assert "created_at" in data


@pytest.mark.phase6
class TestListSimulations:
    """SPEC: 06_API_SPEC.md#get-simulations"""

    async def test_empty_list(self, client: AsyncClient):
        resp = await client.get("/api/v1/simulations/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_after_create(self, client: AsyncClient, sim_id: str):
        resp = await client.get("/api/v1/simulations/")
        data = resp.json()
        assert data["total"] == 1

    async def test_pagination(self, client: AsyncClient):
        for _ in range(5):
            await client.post("/api/v1/simulations/", json=_valid_create_body())
        resp = await client.get("/api/v1/simulations/", params={"limit": 2, "offset": 0})
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5


@pytest.mark.phase6
class TestGetSimulation:
    """SPEC: 06_API_SPEC.md#get-simulationssimulation_id"""

    async def test_get_existing(self, client: AsyncClient, sim_id: str):
        resp = await client.get(f"/api/v1/simulations/{sim_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["simulation_id"] == sim_id

    async def test_404_nonexistent(self, client: AsyncClient):
        resp = await client.get("/api/v1/simulations/nonexistent-uuid")
        assert resp.status_code == 404


@pytest.mark.phase6
class TestStartSimulation:
    """SPEC: 06_API_SPEC.md#post-simulationssimulation_idstart"""

    async def test_start_configured(self, client: AsyncClient, sim_id: str):
        resp = await client.post(f"/api/v1/simulations/{sim_id}/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    async def test_start_already_running(self, client: AsyncClient, sim_id: str):
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        resp = await client.post(f"/api/v1/simulations/{sim_id}/start")
        assert resp.status_code == 409


@pytest.mark.phase6
class TestStepSimulation:
    """SPEC: 06_API_SPEC.md#post-simulationssimulation_idstep"""

    async def test_step_after_start(self, client: AsyncClient, sim_id: str):
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        resp = await client.post(f"/api/v1/simulations/{sim_id}/step")
        assert resp.status_code == 200
        data = resp.json()
        assert "step" in data
        assert "adoption_rate" in data

    async def test_step_when_configured_409(self, client: AsyncClient, sim_id: str):
        resp = await client.post(f"/api/v1/simulations/{sim_id}/step")
        assert resp.status_code == 409


@pytest.mark.phase6
class TestPauseResumeStop:
    """SPEC: 06_API_SPEC.md#pause-resume-stop"""

    async def test_pause_running(self, client: AsyncClient, sim_id: str):
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        resp = await client.post(f"/api/v1/simulations/{sim_id}/pause")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    async def test_pause_configured_409(self, client: AsyncClient, sim_id: str):
        resp = await client.post(f"/api/v1/simulations/{sim_id}/pause")
        assert resp.status_code == 409

    async def test_resume_paused(self, client: AsyncClient, sim_id: str):
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        await client.post(f"/api/v1/simulations/{sim_id}/pause")
        resp = await client.post(f"/api/v1/simulations/{sim_id}/resume")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    async def test_stop(self, client: AsyncClient, sim_id: str):
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        resp = await client.post(f"/api/v1/simulations/{sim_id}/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"


@pytest.mark.phase6
class TestStepHistory:
    """SPEC: 06_API_SPEC.md#get-simulationssimulation_idsteps"""

    async def test_empty_steps(self, client: AsyncClient, sim_id: str):
        resp = await client.get(f"/api/v1/simulations/{sim_id}/steps")
        assert resp.status_code == 200
        assert resp.json()["steps"] == []

    async def test_steps_after_execution(self, client: AsyncClient, sim_id: str):
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        await client.post(f"/api/v1/simulations/{sim_id}/step")
        await client.post(f"/api/v1/simulations/{sim_id}/step")
        resp = await client.get(f"/api/v1/simulations/{sim_id}/steps")
        data = resp.json()
        assert len(data["steps"]) == 2

    async def test_emergent_events_serialization_contract(
        self, client: AsyncClient, sim_id: str,
    ):
        """Regression — REST and WS payloads MUST agree on the EmergentEvent
        field shape. The FE EmergentEvent type uses `event_type`, not `type`,
        and includes `severity` + `description`. A 2026-04 audit found this
        endpoint emitting `{type, step, community_id}` only — every event
        on the FE became `event_type: undefined → "unknown"` and React keys
        collided whenever a single step had >1 event.
        """
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        # Run a few steps to coax detectors into firing.
        for _ in range(8):
            await client.post(f"/api/v1/simulations/{sim_id}/step")
        resp = await client.get(f"/api/v1/simulations/{sim_id}/steps")
        steps = resp.json()["steps"]
        for s in steps:
            for e in s["emergent_events"]:
                # Required keys must exist (typo regression check).
                assert "event_type" in e, (
                    f"missing 'event_type' (was bug: emitted as 'type'): {e}"
                )
                assert "severity" in e
                assert "description" in e
                # 'type' is the buggy old name; must NOT appear.
                assert "type" not in e, (
                    f"forbidden legacy 'type' key still present: {e}"
                )
                assert e["event_type"] in {
                    "viral_cascade", "slow_adoption",
                    "polarization", "collapse", "echo_chamber",
                }


@pytest.mark.phase6
class TestInjectEvent:
    """SPEC: 06_API_SPEC.md#post-simulationssimulation_idinject-event"""

    async def test_inject_running(self, client: AsyncClient, sim_id: str):
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/inject-event",
            json={
                "event_type": "campaign_ad",
                "content": "Test event",
                "controversy": 0.9,
                "target_communities": ["A"],
            },
        )
        assert resp.status_code == 200
        assert "event_id" in resp.json()

    async def test_inject_configured_409(self, client: AsyncClient, sim_id: str):
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/inject-event",
            json={"event_type": "campaign_ad", "content": "Nope"},
        )
        assert resp.status_code == 409

    async def test_inject_with_target_communities(self, client: AsyncClient, sim_id: str):
        """target_communities should be accepted and forwarded to orchestrator."""
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/inject-event",
            json={
                "event_type": "controversy",
                "content": "scandal in community A",
                "controversy": 0.9,
                "target_communities": ["A", "C"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "event_id" in data
        assert "effective_step" in data

    async def test_inject_unknown_type_400(self, client: AsyncClient, sim_id: str):
        """Unknown event type should return 400."""
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/inject-event",
            json={"event_type": "UNKNOWN_TYPE", "content": "test"},
        )
        assert resp.status_code == 400

    async def test_inject_roundtrip_content_reaches_agents(
        self, client: AsyncClient, sim_id: str
    ):
        """End-to-end: verify the documented Inject Event flow.

        This is the round-trip test behind the docstring claim:
          1. POST /inject-event → 200 with event_id + effective_step
          2. Event queued on state.injected_events with the typed content
             visible in its `message` field
          3. Next step consumes the queue (len → 0) and routes it through
             perception so agents' exposure_count bumps
          4. effective_step matches the step that actually processes it
        """
        from app.api import deps as deps_mod

        await client.post(f"/api/v1/simulations/{sim_id}/start")
        orch = deps_mod.get_orchestrator()
        from uuid import UUID
        state = orch.get_state(UUID(sim_id))

        step_before = state.current_step
        exposure_before = sum(a.exposure_count for a in state.agents)

        unique_content = "Battery explosion reported in 47 units — E2E marker"
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/inject-event",
            json={
                "event_type": "controversy",
                "content": unique_content,
                "controversy": 0.9,
            },
        )
        # 1. API contract
        assert resp.status_code == 200
        data = resp.json()
        assert "event_id" in data
        assert data["effective_step"] == step_before + 1

        # 2. Queued + content survives into the message
        assert len(state.injected_events) == 1
        queued = state.injected_events[0]
        assert queued.event_type == "community_discussion"  # controversy → mapped
        assert unique_content in queued.message

        # 3. Next step consumes the queue + agents perceive it
        step_resp = await client.post(f"/api/v1/simulations/{sim_id}/step")
        assert step_resp.status_code == 200
        assert len(state.injected_events) == 0
        exposure_after = sum(a.exposure_count for a in state.agents)
        assert exposure_after > exposure_before, (
            f"No agent saw the injected event "
            f"(exposure {exposure_before} → {exposure_after})"
        )

        # 4. The consuming step matches effective_step
        assert state.current_step == data["effective_step"]


@pytest.mark.phase6
class TestReplayAndCompare:
    """SPEC: 06_API_SPEC.md#replay-compare"""

    async def test_replay(self, client: AsyncClient, sim_id: str):
        resp = await client.post(f"/api/v1/simulations/{sim_id}/replay/5")
        # 200 if step exists in history, 400 if not found — both are valid
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            data = resp.json()
            assert data["from_step"] == 5
            assert "replay_id" in data

    async def test_compare_404(self, client: AsyncClient, sim_id: str):
        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/compare/nonexistent"
        )
        assert resp.status_code == 404

    async def test_compare_both_exist(self, client: AsyncClient):
        r1 = await client.post("/api/v1/simulations/", json=_valid_create_body())
        r2 = await client.post("/api/v1/simulations/", json=_valid_create_body())
        id1 = r1.json()["simulation_id"]
        id2 = r2.json()["simulation_id"]
        resp = await client.get(f"/api/v1/simulations/{id1}/compare/{id2}")
        assert resp.status_code == 200


@pytest.mark.phase6
class TestEngineControl:
    """SPEC: 06_API_SPEC.md#engine-control"""

    async def test_engine_control_requires_paused(self, client: AsyncClient, sim_id: str):
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/engine-control",
            json={"slm_llm_ratio": 0.5, "slm_model": "phi4", "budget_usd": 50.0},
        )
        assert resp.status_code == 409  # configured, not paused

    async def test_engine_control_paused(self, client: AsyncClient, sim_id: str):
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        await client.post(f"/api/v1/simulations/{sim_id}/pause")
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/engine-control",
            json={"slm_llm_ratio": 0.7, "slm_model": "phi4", "budget_usd": 50.0},
        )
        assert resp.status_code == 200


@pytest.mark.phase6
class TestRecommendEngine:
    """SPEC: 06_API_SPEC.md#recommend-engine"""

    async def test_recommend(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/simulations/recommend-engine",
            json={"agent_count": 1000, "budget_usd": 10.0, "max_steps": 50},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recommended_ratio" in data
        assert "tier_distribution" in data
