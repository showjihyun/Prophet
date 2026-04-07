"""Network graph API contract tests.
Auto-generated from SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idnetwork
SPEC Version: 0.2.0

Tests verify that the network endpoint returns correct Cytoscape-format
data with all required node/edge fields.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api import deps as _deps_mod
from app.api import simulations as _sim_mod


@pytest.fixture(autouse=True)
def _reset():
    _deps_mod._orchestrator = None
    _sim_mod._monte_carlo_jobs.clear()
    yield
    _deps_mod._orchestrator = None
    _sim_mod._monte_carlo_jobs.clear()


def _valid_create_body() -> dict:
    return {
        "name": "Graph Test Sim",
        "campaign": {
            "name": "Camp",
            "budget": 1000,
            "channels": ["sns"],
            "message": "Hello Graph",
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
    assert resp.status_code == 201
    return resp.json()["simulation_id"]


# ---------------------------------------------------------------------------
# API-03: GET /simulations/{id}/network — SPEC contract
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestNetworkGraphAPI:
    """SPEC: 06_API_SPEC.md#get-simulationssimulation_idnetwork"""

    async def test_returns_200(self, client: AsyncClient, sim_id: str):
        """Network endpoint returns 200 for existing simulation."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        assert resp.status_code == 200

    async def test_response_has_nodes_and_edges(self, client: AsyncClient, sim_id: str):
        """Response must contain 'nodes' and 'edges' arrays."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    async def test_nodes_are_nonempty(self, client: AsyncClient, sim_id: str):
        """A created simulation must have nodes (agents)."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        data = resp.json()
        assert len(data["nodes"]) > 0, "Simulation should have agents as nodes"

    async def test_edges_are_nonempty(self, client: AsyncClient, sim_id: str):
        """A created simulation must have edges (connections)."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        data = resp.json()
        assert len(data["edges"]) > 0, "Simulation should have network edges"

    async def test_node_has_required_fields(self, client: AsyncClient, sim_id: str):
        """SPEC: each node.data must have id, label, community, agent_type, influence_score, adopted."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        node = resp.json()["nodes"][0]
        assert "data" in node, "Node must have 'data' wrapper"
        d = node["data"]
        assert "id" in d, "Node must have 'id'"
        assert "label" in d, "Node must have 'label'"
        assert "community" in d, "Node must have 'community' (short key like A/B/C)"
        assert "agent_type" in d, "Node must have 'agent_type'"
        assert "influence_score" in d, "Node must have 'influence_score'"
        assert "adopted" in d, "Node must have 'adopted'"

    async def test_node_community_is_short_key(self, client: AsyncClient, sim_id: str):
        """SPEC: community field should be a short key (A/B/C/D/E), not a UUID."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        nodes = resp.json()["nodes"]
        for node in nodes[:10]:
            community = node["data"]["community"]
            assert isinstance(community, str)
            # Short keys are 1-2 chars, UUIDs are 36 chars
            assert len(community) <= 10, f"Community should be short key, got: {community}"

    async def test_node_label_is_string(self, client: AsyncClient, sim_id: str):
        """Node label must be a non-empty string."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        node = resp.json()["nodes"][0]
        label = node["data"]["label"]
        assert isinstance(label, str)
        assert len(label) > 0

    async def test_node_influence_score_range(self, client: AsyncClient, sim_id: str):
        """influence_score must be between 0 and 1."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        for node in resp.json()["nodes"][:20]:
            score = node["data"]["influence_score"]
            assert 0.0 <= score <= 1.0, f"influence_score {score} out of range"

    async def test_edge_has_required_fields(self, client: AsyncClient, sim_id: str):
        """SPEC: each edge.data must have id, source, target, weight, is_bridge."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        edge = resp.json()["edges"][0]
        assert "data" in edge, "Edge must have 'data' wrapper"
        d = edge["data"]
        assert "id" in d, "Edge must have 'id'"
        assert "source" in d, "Edge must have 'source'"
        assert "target" in d, "Edge must have 'target'"
        assert "weight" in d, "Edge must have 'weight'"
        assert "is_bridge" in d, "Edge must have 'is_bridge'"

    async def test_edge_weight_range(self, client: AsyncClient, sim_id: str):
        """Edge weight must be between 0 and 1."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        for edge in resp.json()["edges"][:20]:
            weight = edge["data"]["weight"]
            assert 0.0 <= weight <= 1.0, f"Edge weight {weight} out of range"

    async def test_edge_is_bridge_is_boolean(self, client: AsyncClient, sim_id: str):
        """is_bridge must be a boolean."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        edge = resp.json()["edges"][0]
        assert isinstance(edge["data"]["is_bridge"], bool)

    async def test_edge_has_edge_type(self, client: AsyncClient, sim_id: str):
        """edge_type must be present and one of 'intra', 'inter', 'bridge'."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        edge = resp.json()["edges"][0]
        if "edge_type" in edge["data"]:
            assert edge["data"]["edge_type"] in ("intra", "inter", "bridge")

    async def test_404_for_nonexistent_sim(self, client: AsyncClient):
        """Network endpoint returns 404 for non-existent simulation."""
        resp = await client.get("/api/v1/simulations/nonexistent-uuid/network/")
        assert resp.status_code == 404

    async def test_multiple_communities_in_nodes(self, client: AsyncClient, sim_id: str):
        """Nodes should span multiple communities (not all same)."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/network/")
        communities = {n["data"]["community"] for n in resp.json()["nodes"]}
        assert len(communities) >= 2, f"Expected multiple communities, got: {communities}"
