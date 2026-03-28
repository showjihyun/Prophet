"""
Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md#error-specification
SPEC Version: 0.1.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)

NOTE: These are backend-side tests for WebSocket/API error behavior that
the frontend depends on. Frontend component tests (React ErrorBoundary,
Zustand store reset, etc.) belong in frontend/src/__tests__/.
"""
import pytest
from uuid import uuid4


class TestWebSocketErrorProtocol:
    """SPEC: 07_FRONTEND_SPEC.md#error-specification — WebSocket error events"""

    def test_ws_disconnect_sends_reconnect_hint(self):
        """Server detects WS disconnect → buffers events for reconnect."""
        from app.api.ws import WebSocketManager
        manager = WebSocketManager()
        sim_id = uuid4()
        # Register then disconnect
        manager.register(sim_id, client_id="c1")
        manager.disconnect(sim_id, client_id="c1")
        # Buffer an event while disconnected
        manager.broadcast(sim_id, {"type": "step_result", "step": 5})
        # Reconnect should deliver buffered events
        buffered = manager.reconnect(sim_id, client_id="c1")
        assert len(buffered) == 1
        assert buffered[0]["step"] == 5

    def test_ws_error_event_format(self):
        """WebSocket error event follows standard format."""
        from app.api.ws import WebSocketManager
        manager = WebSocketManager()
        error_event = manager.make_error_event(
            sim_id=uuid4(), error_type="SimulationStepError",
            message="Step 5 crashed", step=5,
        )
        assert error_event["type"] == "error"
        assert "error_type" in error_event
        assert "message" in error_event


class TestAPIErrorResponses:
    """SPEC: 07_FRONTEND_SPEC.md#error-specification — API error format (RFC 7807)"""

    def test_4xx_returns_rfc7807_format(self):
        """HTTP 4xx errors return RFC 7807 problem detail."""
        from app.api.errors import make_problem_detail
        detail = make_problem_detail(
            status=404, title="Simulation not found",
            detail=f"No simulation with ID {uuid4()}",
        )
        assert detail["status"] == 404
        assert "title" in detail
        assert "detail" in detail
        assert detail["type"] == "about:blank" or detail["type"].startswith("http")

    def test_5xx_returns_generic_message(self):
        """HTTP 5xx returns generic error, no internal details leaked."""
        from app.api.errors import make_problem_detail
        detail = make_problem_detail(
            status=500, title="Internal Server Error",
            detail="An unexpected error occurred.",
        )
        assert detail["status"] == 500
        assert "traceback" not in str(detail)
        assert "stack" not in str(detail)


class TestSimulationConfigValidationAPI:
    """SPEC: 07_FRONTEND_SPEC.md#error-specification — form validation backend"""

    def test_invalid_config_returns_422(self):
        """Invalid simulation config body returns 422 with field errors."""
        from app.api.errors import make_validation_error
        errors = make_validation_error(fields={
            "communities": "At least 1 community required",
            "max_steps": "Must be positive integer",
        })
        assert errors["status"] == 422
        assert len(errors["errors"]) == 2
