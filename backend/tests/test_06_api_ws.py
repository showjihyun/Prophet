"""WebSocket endpoint tests.
Auto-generated from SPEC: docs/spec/06_API_SPEC.md#7-websocket---wssimulation_id
SPEC Version: 0.1.0
"""
import pytest
from starlette.testclient import TestClient

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


@pytest.mark.phase6
class TestWebSocket:
    """SPEC: 06_API_SPEC.md#7-websocket---wssimulation_id"""

    def test_ws_pause_message(self, sync_client: TestClient):
        """Client sends pause -> server replies status_change."""
        with sync_client.websocket_connect("/ws/test-sim") as ws:
            ws.send_json({"type": "pause"})
            msg = ws.receive_json()
            assert msg["type"] == "status_change"
            assert msg["data"]["status"] == "paused"

    def test_ws_resume_message(self, sync_client: TestClient):
        """Client sends resume -> server replies status_change."""
        with sync_client.websocket_connect("/ws/test-sim") as ws:
            ws.send_json({"type": "resume"})
            msg = ws.receive_json()
            assert msg["type"] == "status_change"
            assert msg["data"]["status"] == "running"

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

    def test_ws_inject_event(self, sync_client: TestClient):
        """Client sends inject_event -> server acknowledges."""
        with sync_client.websocket_connect("/ws/test-sim") as ws:
            ws.send_json({
                "type": "inject_event",
                "data": {"event_type": "controversy", "content": "Test"},
            })
            msg = ws.receive_json()
            assert msg["type"] == "status_change"
            assert msg["data"]["status"] == "event_injected"
