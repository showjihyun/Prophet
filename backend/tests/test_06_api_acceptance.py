"""Acceptance tests for API endpoints (API-01 through API-08).
Auto-generated from SPEC: docs/spec/06_API_SPEC.md#9-acceptance-criteria
SPEC Version: 0.1.0
Generated BEFORE full orchestrator integration — tests define the contract.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# Reset in-memory store between tests
from app.api import simulations as _sim_mod


@pytest.fixture(autouse=True)
def _reset_store():
    _sim_mod._simulations.clear()
    _sim_mod._monte_carlo_jobs.clear()
    yield
    _sim_mod._simulations.clear()
    _sim_mod._monte_carlo_jobs.clear()


def _valid_campaign() -> dict:
    return {
        "name": "Test Campaign",
        "budget": 5000000,
        "channels": ["sns", "influencer"],
        "message": "Test message",
        "target_communities": ["all"],
        "controversy": 0.1,
        "novelty": 0.8,
        "utility": 0.7,
    }


def _valid_create_body() -> dict:
    return {
        "name": "Q2 Smartphone Launch",
        "description": "Test campaign for Model X",
        "campaign": _valid_campaign(),
        "max_steps": 50,
    }


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def created_sim(client: AsyncClient) -> dict:
    resp = await client.post("/api/v1/simulations/", json=_valid_create_body())
    assert resp.status_code == 201
    return resp.json()


# ---- API-01: POST /simulations with valid config -> 201 + simulation_id ----


@pytest.mark.phase6
@pytest.mark.acceptance
class TestAPI01CreateSimulation:
    """SPEC: 06_API_SPEC.md §9 API-01"""

    async def test_create_simulation_returns_201(self, client: AsyncClient):
        resp = await client.post("/api/v1/simulations/", json=_valid_create_body())
        assert resp.status_code == 201

    async def test_create_simulation_has_simulation_id(self, client: AsyncClient):
        resp = await client.post("/api/v1/simulations/", json=_valid_create_body())
        data = resp.json()
        assert "simulation_id" in data
        assert len(data["simulation_id"]) > 0

    async def test_create_simulation_status_configured(self, client: AsyncClient):
        resp = await client.post("/api/v1/simulations/", json=_valid_create_body())
        data = resp.json()
        assert data["status"] == "configured"

    async def test_create_simulation_has_created_at(self, client: AsyncClient):
        resp = await client.post("/api/v1/simulations/", json=_valid_create_body())
        data = resp.json()
        assert "created_at" in data


# ---- API-02: POST /simulations/{id}/step when CONFIGURED -> 409 ----


@pytest.mark.phase6
@pytest.mark.acceptance
class TestAPI02StepRequiresStart:
    """SPEC: 06_API_SPEC.md §9 API-02"""

    async def test_step_configured_returns_409(
        self, client: AsyncClient, created_sim: dict
    ):
        sim_id = created_sim["simulation_id"]
        resp = await client.post(f"/api/v1/simulations/{sim_id}/step")
        assert resp.status_code == 409


# ---- API-03: GET /simulations/{id}/network in cytoscape format ----


@pytest.mark.phase6
@pytest.mark.acceptance
class TestAPI03NetworkCytoscape:
    """SPEC: 06_API_SPEC.md §9 API-03"""

    async def test_network_returns_200(
        self, client: AsyncClient, created_sim: dict
    ):
        sim_id = created_sim["simulation_id"]
        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/network/", params={"format": "cytoscape"}
        )
        assert resp.status_code == 200

    async def test_network_has_nodes_and_edges(
        self, client: AsyncClient, created_sim: dict
    ):
        sim_id = created_sim["simulation_id"]
        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/network/", params={"format": "cytoscape"}
        )
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data


# ---- API-04: PATCH agent while simulation RUNNING -> 409 ----


@pytest.mark.phase6
@pytest.mark.acceptance
class TestAPI04PatchAgentRequiresPause:
    """SPEC: 06_API_SPEC.md §9 API-04"""

    async def test_patch_agent_running_returns_409(
        self, client: AsyncClient, created_sim: dict
    ):
        sim_id = created_sim["simulation_id"]
        # Start the simulation (move to RUNNING)
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        # Attempt to patch an agent
        resp = await client.patch(
            f"/api/v1/simulations/{sim_id}/agents/fake-agent",
            json={"belief": 0.5},
        )
        assert resp.status_code == 409


# ---- API-05: WebSocket step_result (basic connectivity test) ----


@pytest.mark.phase6
@pytest.mark.acceptance
class TestAPI05WebSocket:
    """SPEC: 06_API_SPEC.md §9 API-05"""

    def test_ws_connects(self):
        """WebSocket can connect and exchange messages."""
        from starlette.testclient import TestClient

        test_client = TestClient(app)
        with test_client.websocket_connect("/ws/test-sim") as ws:
            ws.send_json({"type": "pause"})
            msg = ws.receive_json()
            assert msg["type"] == "status_change"
            assert msg["data"]["status"] == "paused"


# ---- API-06: GET /simulations with status filter ----


@pytest.mark.phase6
@pytest.mark.acceptance
class TestAPI06StatusFilter:
    """SPEC: 06_API_SPEC.md §9 API-06"""

    async def test_filter_by_status(self, client: AsyncClient):
        # Create two simulations
        await client.post("/api/v1/simulations/", json=_valid_create_body())
        resp2 = await client.post("/api/v1/simulations/", json=_valid_create_body())
        sim2_id = resp2.json()["simulation_id"]

        # Start the second one
        await client.post(f"/api/v1/simulations/{sim2_id}/start")

        # Filter by configured
        resp = await client.get(
            "/api/v1/simulations/", params={"status": "configured"}
        )
        data = resp.json()
        assert resp.status_code == 200
        for item in data["items"]:
            assert item["status"] == "configured"

    async def test_filter_returns_only_matching(self, client: AsyncClient):
        await client.post("/api/v1/simulations/", json=_valid_create_body())

        resp = await client.get(
            "/api/v1/simulations/", params={"status": "running"}
        )
        data = resp.json()
        assert data["total"] == 0


# ---- API-07: POST monte-carlo returns 202 immediately ----


@pytest.mark.phase6
@pytest.mark.acceptance
class TestAPI07MonteCarlo202:
    """SPEC: 06_API_SPEC.md §9 API-07"""

    async def test_monte_carlo_returns_202(
        self, client: AsyncClient, created_sim: dict
    ):
        sim_id = created_sim["simulation_id"]
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 10, "llm_enabled": False},
        )
        assert resp.status_code == 202

    async def test_monte_carlo_has_job_id(
        self, client: AsyncClient, created_sim: dict
    ):
        sim_id = created_sim["simulation_id"]
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 10},
        )
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "queued"


# ---- API-08: Inject event -> reflected (basic injection test) ----


@pytest.mark.phase6
@pytest.mark.acceptance
class TestAPI08InjectEvent:
    """SPEC: 06_API_SPEC.md §9 API-08"""

    async def test_inject_event_returns_200(
        self, client: AsyncClient, created_sim: dict
    ):
        sim_id = created_sim["simulation_id"]
        # Must be running or paused
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/inject-event",
            json={
                "event_type": "controversy",
                "content": "Battery explosion report",
                "controversy": 0.9,
                "target_communities": ["C"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "event_id" in data
        assert "effective_step" in data
