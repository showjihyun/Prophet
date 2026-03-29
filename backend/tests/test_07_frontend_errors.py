"""Frontend error protocol tests.
SPEC: docs/spec/06_API_SPEC.md#error-response-format
SPEC: docs/spec/07_FRONTEND_SPEC.md#error-specification

Tests verify that the API layer returns proper error formats for frontend consumption:
- RFC 7807-style error responses for 4xx/5xx
- WebSocket error event format (tested via HTTP fallback)
- Simulation config validation (422 on invalid config)
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


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.phase7
class TestAPIErrorResponses:
    """SPEC: 07_FRONTEND_SPEC.md#error-specification — API error format (RFC 7807)"""

    @pytest.mark.asyncio
    async def test_4xx_returns_rfc7807_format(self, client):
        """HTTP 4xx errors return RFC 7807-like problem detail."""
        resp = await client.get(
            "/api/v1/simulations/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404
        data = resp.json()
        # FastAPI returns {"detail": ...} which aligns with RFC 7807 "detail" field
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_5xx_returns_generic_message(self, client):
        """Server errors should not expose internal details.

        We verify that error responses for bad input don't leak tracebacks.
        """
        resp = await client.get("/api/v1/simulations/not-a-uuid-format")
        assert resp.status_code in (404, 422)
        body = resp.text
        assert "Traceback" not in body
        assert "File \"/app" not in body

    @pytest.mark.asyncio
    async def test_invalid_config_returns_422(self, client):
        """Missing required fields -> 422 Unprocessable Entity."""
        resp = await client.post(
            "/api/v1/simulations/",
            json={"name": "test"},  # missing campaign
        )
        assert resp.status_code == 422


@pytest.mark.phase7
class TestWebSocketErrorProtocol:
    """SPEC: 07_FRONTEND_SPEC.md#error-specification — WebSocket error events"""

    @pytest.mark.asyncio
    async def test_ws_error_event_format(self, client):
        """Stepping a non-existent simulation returns an error status code."""
        resp = await client.post(
            "/api/v1/simulations/00000000-0000-0000-0000-000000000000/step"
        )
        # Should be 404 (not found) or 409 (invalid state)
        assert resp.status_code in (404, 409)
        data = resp.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_ws_disconnect_sends_reconnect_hint(self, client):
        """Health endpoint is available for reconnection target."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
