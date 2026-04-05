"""WebSocket endpoint tests.
Auto-generated from SPEC: docs/spec/06_API_SPEC.md#7-websocket---wssimulation_id
SPEC Version: 0.1.0

Tests cover both WS protocol and orchestrator-integrated commands.
"""
import pytest
from starlette.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api import deps as _deps_mod
from app.api import simulations as _sim_mod


@pytest.fixture(autouse=True)
def _reset_store():
    _deps_mod._orchestrator = None
    _sim_mod._monte_carlo_jobs.clear()
    yield
    _deps_mod._orchestrator = None
    _sim_mod._monte_carlo_jobs.clear()


@pytest.fixture
def sync_client():
    return TestClient(app)


def _valid_create_body() -> dict:
    return {
        "name": "WS Test Sim",
        "campaign": {
            "name": "Camp",
            "budget": 1000,
            "channels": ["sns"],
            "message": "Hello WS",
        },
    }


# ---------------------------------------------------------------------------
# Protocol tests (no real simulation needed)
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestWebSocketProtocol:
    """SPEC: 06_API_SPEC.md#7-websocket — protocol-level tests"""

    def test_ws_subscribe_agent(self, sync_client: TestClient):
        """Client subscribes to agent updates."""
        with sync_client.websocket_connect("/ws/test-sim") as ws:
            ws.send_json({
                "type": "subscribe_agent",
                "data": {"agent_id": "agent-123"},
            })
            msg = ws.receive_json()
            assert msg["type"] == "agent_update"
            assert msg["data"]["agent_id"] == "agent-123"
            assert msg["data"]["subscribed"] is True

    def test_ws_unsubscribe_agent(self, sync_client: TestClient):
        """Client unsubscribes from agent updates."""
        with sync_client.websocket_connect("/ws/test-sim") as ws:
            ws.send_json({
                "type": "unsubscribe_agent",
                "data": {"agent_id": "agent-123"},
            })
            msg = ws.receive_json()
            assert msg["type"] == "agent_update"
            assert msg["data"]["agent_id"] == "agent-123"
            assert msg["data"]["subscribed"] is False

    def test_ws_unknown_type(self, sync_client: TestClient):
        """Unknown message type -> error response."""
        with sync_client.websocket_connect("/ws/test-sim") as ws:
            ws.send_json({"type": "unknown_type"})
            msg = ws.receive_json()
            assert msg["type"] == "error"

    def test_ws_invalid_json(self, sync_client: TestClient):
        """Invalid JSON -> error response."""
        with sync_client.websocket_connect("/ws/test-sim") as ws:
            ws.send_text("not json at all")
            msg = ws.receive_json()
            assert msg["type"] == "error"


# ---------------------------------------------------------------------------
# Orchestrator-integrated command tests (require real simulation)
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestWebSocketCommands:
    """SPEC: 06_API_SPEC.md#7-websocket — commands control the orchestrator"""

    async def test_ws_pause_with_real_simulation(self, sync_client: TestClient):
        """Client sends pause -> orchestrator processes -> response sent."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post("/api/v1/simulations/", json=_valid_create_body())
            sim_id = resp.json()["simulation_id"]
            # Start may fail in test env (no DB), manually set status
            from app.api.deps import get_orchestrator
            from uuid import UUID
            orch = get_orchestrator()
            state = orch.get_state(UUID(sim_id))
            state.status = "running"

        with sync_client.websocket_connect(f"/ws/{sim_id}") as ws:
            ws.send_json({"type": "pause"})
            msg = ws.receive_json()
            assert msg["type"] == "status_change"
            assert msg["data"]["status"] == "paused"
            assert "step" in msg["data"]

    async def test_ws_resume_after_pause(self, sync_client: TestClient):
        """Client sends resume -> orchestrator resumes -> status_change broadcast."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post("/api/v1/simulations/", json=_valid_create_body())
            sim_id = resp.json()["simulation_id"]
            from app.api.deps import get_orchestrator
            from uuid import UUID
            orch = get_orchestrator()
            state = orch.get_state(UUID(sim_id))
            state.status = "paused"

        with sync_client.websocket_connect(f"/ws/{sim_id}") as ws:
            ws.send_json({"type": "resume"})
            msg = ws.receive_json()
            assert msg["type"] == "status_change"
            assert msg["data"]["status"] == "running"

    async def test_ws_inject_event_with_real_simulation(self, sync_client: TestClient):
        """Client sends inject_event -> orchestrator injects -> status_change broadcast."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post("/api/v1/simulations/", json=_valid_create_body())
            sim_id = resp.json()["simulation_id"]

        with sync_client.websocket_connect(f"/ws/{sim_id}") as ws:
            ws.send_json({
                "type": "inject_event",
                "data": {"event_type": "controversy", "content": "Test"},
            })
            msg = ws.receive_json()
            assert msg["type"] == "status_change"
            assert msg["data"]["status"] == "event_injected"

    def test_ws_pause_nonexistent_sim_returns_error(self, sync_client: TestClient):
        """Pause for non-existent sim returns error, not crash."""
        with sync_client.websocket_connect("/ws/nonexistent-sim") as ws:
            ws.send_json({"type": "pause"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "detail" in msg["data"]

    def test_ws_resume_nonexistent_sim_returns_error(self, sync_client: TestClient):
        """Resume for non-existent sim returns error."""
        with sync_client.websocket_connect("/ws/nonexistent-sim") as ws:
            ws.send_json({"type": "resume"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
