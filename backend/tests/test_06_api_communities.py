"""Communities API endpoint tests.
Auto-generated from SPEC: docs/spec/06_API_SPEC.md#5-community-endpoints
SPEC Version: 0.1.0
Generated BEFORE full integration — tests define the API contract.

Tests use the ASGI TestClient pattern (AsyncClient + ASGITransport) matching
the style established in test_06_api_simulations.py.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api import deps as _deps_mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_orchestrator():
    """Reset orchestrator singleton between tests."""
    _deps_mod._orchestrator = None
    yield
    _deps_mod._orchestrator = None


def _valid_create_body() -> dict:
    return {
        "name": "Community Test Sim",
        "campaign": {
            "name": "Camp",
            "budget": 1000,
            "channels": ["sns"],
            "message": "Hello communities",
        },
    }


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def sim_id(client: AsyncClient) -> str:
    """Create a simulation and return its ID."""
    resp = await client.post("/api/v1/simulations/", json=_valid_create_body())
    assert resp.status_code == 201, f"Failed to create simulation: {resp.text}"
    return resp.json()["simulation_id"]


# ---------------------------------------------------------------------------
# GET /api/v1/simulations/{sim_id}/communities
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestListCommunities:
    """SPEC: 06_API_SPEC.md#get-simulationssimulation_idcommunities"""

    async def test_returns_200_for_existing_sim(
        self, client: AsyncClient, sim_id: str
    ):
        """GET communities returns 200 for an existing simulation."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/communities/")
        assert resp.status_code == 200

    async def test_response_is_list_structure(
        self, client: AsyncClient, sim_id: str
    ):
        """Response body must contain a 'communities' list field."""
        resp = await client.get(f"/api/v1/simulations/{sim_id}/communities/")
        data = resp.json()
        assert "communities" in data
        assert isinstance(data["communities"], list)

    async def test_404_for_nonexistent_sim(self, client: AsyncClient):
        """GET communities for a non-existent simulation must return 404."""
        resp = await client.get(
            "/api/v1/simulations/nonexistent-uuid-1234/communities/"
        )
        assert resp.status_code == 404

    async def test_404_message_contains_sim_id(self, client: AsyncClient):
        """404 error detail must reference the missing simulation ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await client.get(f"/api/v1/simulations/{fake_id}/communities/")
        assert resp.status_code == 404
        detail = resp.json().get("detail", "")
        # detail may be a string or a list/dict — normalise to string
        detail_str = detail if isinstance(detail, str) else str(detail)
        assert fake_id in detail_str or "not found" in detail_str.lower()


# ---------------------------------------------------------------------------
# GET /api/v1/simulations/{sim_id}/communities/{community_id}/threads
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestListCommunityThreads:
    """SPEC: 06_API_SPEC.md#5-community-endpoints — threads list"""

    async def test_returns_200_for_existing_sim(
        self, client: AsyncClient, sim_id: str
    ):
        """GET threads returns 200 for an existing sim + community combination."""
        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads"
        )
        assert resp.status_code == 200

    async def test_response_contains_threads_list(
        self, client: AsyncClient, sim_id: str
    ):
        """Response body must contain a 'threads' list."""
        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads"
        )
        data = resp.json()
        assert "threads" in data
        assert isinstance(data["threads"], list)

    async def test_threads_have_required_fields(
        self, client: AsyncClient, sim_id: str
    ):
        """Each thread summary must have: thread_id, topic, message_count."""
        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads"
        )
        data = resp.json()
        for thread in data["threads"]:
            assert "thread_id" in thread, f"Missing thread_id in {thread}"
            assert "topic" in thread, f"Missing topic in {thread}"
            assert "message_count" in thread, f"Missing message_count in {thread}"

    async def test_threads_generated_for_any_community_id(
        self, client: AsyncClient, sim_id: str
    ):
        """Synthetic threads are generated even for communities with no step history."""
        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/B/threads"
        )
        assert resp.status_code == 200
        data = resp.json()
        # SPEC says 3 synthetic threads per community
        assert len(data["threads"]) == 3

    async def test_404_for_nonexistent_sim(self, client: AsyncClient):
        """GET threads for a non-existent sim must return 404."""
        resp = await client.get(
            "/api/v1/simulations/nonexistent-sim/communities/A/threads"
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/simulations/{sim_id}/communities/{community_id}/threads/{thread_id}
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestGetCommunityThread:
    """SPEC: 06_API_SPEC.md#5-community-endpoints — thread detail"""

    async def test_returns_200_for_existing_thread(
        self, client: AsyncClient, sim_id: str
    ):
        """GET thread detail returns 200 for an existing thread ID."""
        # First discover a valid thread_id from the list
        list_resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads"
        )
        threads = list_resp.json()["threads"]
        assert len(threads) > 0
        thread_id = threads[0]["thread_id"]

        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads/{thread_id}"
        )
        assert resp.status_code == 200

    async def test_thread_detail_contains_messages(
        self, client: AsyncClient, sim_id: str
    ):
        """Thread detail response must contain a 'messages' list."""
        list_resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads"
        )
        thread_id = list_resp.json()["threads"][0]["thread_id"]

        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads/{thread_id}"
        )
        data = resp.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)
        assert len(data["messages"]) > 0

    async def test_thread_detail_message_fields(
        self, client: AsyncClient, sim_id: str
    ):
        """Each message in thread detail must have: message_id, agent_id, content."""
        list_resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads"
        )
        thread_id = list_resp.json()["threads"][0]["thread_id"]

        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads/{thread_id}"
        )
        for msg in resp.json()["messages"]:
            assert "message_id" in msg, f"Missing message_id: {msg}"
            assert "agent_id" in msg, f"Missing agent_id: {msg}"
            assert "content" in msg, f"Missing content: {msg}"

    async def test_404_for_nonexistent_thread(
        self, client: AsyncClient, sim_id: str
    ):
        """GET thread detail for a non-existent thread_id must return 404."""
        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads/totally-fake-thread"
        )
        assert resp.status_code == 404

    async def test_404_for_nonexistent_sim(self, client: AsyncClient):
        """GET thread detail for a non-existent sim must return 404."""
        resp = await client.get(
            "/api/v1/simulations/ghost-sim/communities/A/threads/some-thread"
        )
        assert resp.status_code == 404

    async def test_thread_detail_summary_fields(
        self, client: AsyncClient, sim_id: str
    ):
        """Thread detail must include thread_id, topic, participant_count, avg_sentiment."""
        list_resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads"
        )
        thread_id = list_resp.json()["threads"][0]["thread_id"]

        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads/{thread_id}"
        )
        data = resp.json()
        assert "thread_id" in data
        assert "topic" in data
        assert "participant_count" in data
        assert "avg_sentiment" in data
        assert data["thread_id"] == thread_id

    async def test_thread_message_has_reactions(
        self, client: AsyncClient, sim_id: str
    ):
        """SPEC: Each ChatMessage must have reactions: {agree, disagree, nuanced}."""
        list_resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads"
        )
        thread_id = list_resp.json()["threads"][0]["thread_id"]

        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads/{thread_id}"
        )
        for msg in resp.json()["messages"]:
            assert "reactions" in msg, f"Missing reactions in message: {msg}"
            reactions = msg["reactions"]
            assert "agree" in reactions, f"Missing 'agree' in reactions: {reactions}"
            assert "disagree" in reactions, f"Missing 'disagree' in reactions: {reactions}"
            assert "nuanced" in reactions, f"Missing 'nuanced' in reactions: {reactions}"

    async def test_thread_message_has_reply_fields(
        self, client: AsyncClient, sim_id: str
    ):
        """SPEC: Each ChatMessage must have is_reply and reply_to_id fields."""
        list_resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads"
        )
        thread_id = list_resp.json()["threads"][0]["thread_id"]

        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads/{thread_id}"
        )
        for msg in resp.json()["messages"]:
            assert "is_reply" in msg, f"Missing is_reply in message: {msg}"
            assert "reply_to_id" in msg, f"Missing reply_to_id in message: {msg}"

    async def test_thread_message_stance_field(
        self, client: AsyncClient, sim_id: str
    ):
        """SPEC: Each ChatMessage must have a stance field."""
        list_resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads"
        )
        thread_id = list_resp.json()["threads"][0]["thread_id"]

        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/communities/A/threads/{thread_id}"
        )
        for msg in resp.json()["messages"]:
            assert "stance" in msg, f"Missing stance in message: {msg}"
            assert msg["stance"] in ("Progressive", "Conservative", "Neutral")


# ---------------------------------------------------------------------------
# Community Templates CRUD endpoints
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestCommunityTemplatesList:
    """SPEC: 06_API_SPEC.md#community-template-endpoints — GET /communities/templates"""

    async def test_list_templates_returns_200(self, client: AsyncClient):
        """GET /api/v1/communities/templates/ must return 200."""
        resp = await client.get("/api/v1/communities/templates/")
        assert resp.status_code == 200

    async def test_list_templates_contains_templates_list(self, client: AsyncClient):
        """Response must contain a 'templates' list."""
        resp = await client.get("/api/v1/communities/templates/")
        data = resp.json()
        assert "templates" in data
        assert isinstance(data["templates"], list)

    async def test_default_templates_exist(self, client: AsyncClient):
        """Default templates (early_adopters, etc.) must be present."""
        resp = await client.get("/api/v1/communities/templates/")
        templates = resp.json()["templates"]
        assert len(templates) >= 1, "At least one default template should exist"

    async def test_template_has_required_fields(self, client: AsyncClient):
        """Each template must have: template_id, name, agent_type, default_size."""
        resp = await client.get("/api/v1/communities/templates/")
        for tmpl in resp.json()["templates"]:
            assert "template_id" in tmpl
            assert "name" in tmpl
            assert "agent_type" in tmpl
            assert "default_size" in tmpl


@pytest.mark.phase6
class TestCommunityTemplatesCRUD:
    """SPEC: 06_API_SPEC.md#community-template-endpoints — POST/PUT/DELETE"""

    async def test_create_template_returns_template(self, client: AsyncClient):
        """POST /api/v1/communities/templates/ must create and return a template."""
        body = {
            "name": "Test Community",
            "agent_type": "test_type",
            "default_size": 50,
            "description": "Test description",
            "personality_profile": {"openness": 0.5},
        }
        resp = await client.post("/api/v1/communities/templates/", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "template_id" in data
        assert data["name"] == "Test Community"
        assert data["agent_type"] == "test_type"
        assert data["default_size"] == 50

    async def test_update_template(self, client: AsyncClient):
        """PUT /api/v1/communities/templates/{id} must update the template."""
        # Create first
        create_body = {
            "name": "To Update",
            "agent_type": "updatable",
            "default_size": 10,
        }
        create_resp = await client.post(
            "/api/v1/communities/templates/", json=create_body
        )
        template_id = create_resp.json()["template_id"]

        # Update
        update_body = {
            "name": "Updated Name",
            "agent_type": "updated_type",
            "default_size": 99,
        }
        resp = await client.put(
            f"/api/v1/communities/templates/{template_id}", json=update_body
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Name"
        assert data["default_size"] == 99

    async def test_update_nonexistent_template_returns_404(self, client: AsyncClient):
        """PUT on a non-existent template must return 404."""
        body = {"name": "X", "agent_type": "x", "default_size": 1}
        resp = await client.put(
            "/api/v1/communities/templates/nonexistent-id", json=body
        )
        assert resp.status_code == 404

    async def test_delete_template(self, client: AsyncClient):
        """DELETE /api/v1/communities/templates/{id} must return 204."""
        # Create first
        create_body = {
            "name": "To Delete",
            "agent_type": "deletable",
            "default_size": 5,
        }
        create_resp = await client.post(
            "/api/v1/communities/templates/", json=create_body
        )
        template_id = create_resp.json()["template_id"]

        # Delete
        resp = await client.delete(
            f"/api/v1/communities/templates/{template_id}"
        )
        assert resp.status_code == 204

    async def test_delete_nonexistent_template_returns_404(self, client: AsyncClient):
        """DELETE on a non-existent template must return 404."""
        resp = await client.delete(
            "/api/v1/communities/templates/nonexistent-id"
        )
        assert resp.status_code == 404
