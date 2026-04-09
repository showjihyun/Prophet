"""Agent endpoint tests.
Auto-generated from SPEC: docs/spec/06_API_SPEC.md#3-agent-endpoints
SPEC Version: 0.1.0
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api import deps as _deps_mod


@pytest.fixture(autouse=True)
def _reset_store():
    _deps_mod._orchestrator = None
    yield
    _deps_mod._orchestrator = None


def _valid_create_body() -> dict:
    return {
        "name": "Agent Test Sim",
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
class TestListAgents:
    """SPEC: 06_API_SPEC.md#get-simulationssimulation_idagents"""

    async def test_list_agents_200(self, client: AsyncClient, sim_id: str):
        resp = await client.get(f"/api/v1/simulations/{sim_id}/agents/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_list_agents_404_bad_sim(self, client: AsyncClient):
        resp = await client.get("/api/v1/simulations/nonexistent/agents/")
        assert resp.status_code == 404


@pytest.mark.phase6
class TestGetAgent:
    """SPEC: 06_API_SPEC.md#get-simulationssimulation_idagentsagent_id"""

    async def test_get_agent_404(self, client: AsyncClient, sim_id: str):
        """No agents in stub orchestrator -> 404."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/agents/fake-id")
        assert resp.status_code == 404


@pytest.mark.phase6
class TestPatchAgent:
    """SPEC: 06_API_SPEC.md#patch-simulationssimulation_idagentsagent_id"""

    async def test_patch_requires_paused(self, client: AsyncClient, sim_id: str):
        """CONFIGURED is not PAUSED -> 409."""
        resp = await client.patch(
            f"/api/v1/simulations/{sim_id}/agents/fake-id",
            json={"belief": 0.5},
        )
        assert resp.status_code == 409

    async def test_patch_running_409(self, client: AsyncClient, sim_id: str):
        """RUNNING -> 409."""
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        resp = await client.patch(
            f"/api/v1/simulations/{sim_id}/agents/fake-id",
            json={"belief": 0.5},
        )
        assert resp.status_code == 409

    async def test_patch_paused_but_no_agent(self, client: AsyncClient, sim_id: str):
        """PAUSED but agent not found -> 404 (stub orchestrator)."""
        await client.post(f"/api/v1/simulations/{sim_id}/start")
        await client.post(f"/api/v1/simulations/{sim_id}/pause")
        resp = await client.patch(
            f"/api/v1/simulations/{sim_id}/agents/fake-id",
            json={"belief": 0.5},
        )
        assert resp.status_code == 404


@pytest.mark.phase6
class TestAgentMemory:
    """SPEC: 06_API_SPEC.md#get-simulationssimulation_idagentsagent_idmemory"""

    async def test_memory_404_for_unknown_agent(self, client: AsyncClient, sim_id: str):
        # A nonexistent agent id must return 404 — the old behaviour of
        # returning `200 {memories: []}` was a silent failure that hid
        # real bugs behind an empty list.
        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/agents/fake-id/memory"
        )
        assert resp.status_code == 404
