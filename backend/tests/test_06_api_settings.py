"""Settings endpoint tests.
Auto-generated from SPEC: docs/spec/06_API_SPEC.md#7-settings-endpoints
SPEC Version: 0.1.0
Generated BEFORE implementation — tests define the contract.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.phase7
class TestGetSettings:
    """SPEC: 06_API_SPEC.md#get-apiv1settings"""

    async def test_200_returns_settings(self, client: AsyncClient):
        resp = await client.get("/api/v1/settings/")
        assert resp.status_code == 200

    async def test_response_has_llm_section(self, client: AsyncClient):
        resp = await client.get("/api/v1/settings/")
        data = resp.json()
        assert "llm" in data
        llm = data["llm"]
        assert "default_provider" in llm
        assert "ollama_base_url" in llm
        assert "ollama_default_model" in llm
        assert "slm_model" in llm
        assert "anthropic_model" in llm
        assert "anthropic_api_key_set" in llm
        assert "openai_model" in llm
        assert "openai_api_key_set" in llm

    async def test_response_has_simulation_section(self, client: AsyncClient):
        resp = await client.get("/api/v1/settings/")
        data = resp.json()
        assert "simulation" in data
        sim = data["simulation"]
        assert "slm_llm_ratio" in sim
        assert "llm_tier3_ratio" in sim
        assert "llm_cache_ttl" in sim

    async def test_api_keys_are_boolean_not_raw(self, client: AsyncClient):
        resp = await client.get("/api/v1/settings/")
        data = resp.json()
        assert isinstance(data["llm"]["anthropic_api_key_set"], bool)
        assert isinstance(data["llm"]["openai_api_key_set"], bool)


@pytest.mark.phase7
class TestUpdateSettings:
    """SPEC: 06_API_SPEC.md#put-apiv1settings"""

    async def test_200_on_valid_update(self, client: AsyncClient):
        resp = await client.put(
            "/api/v1/settings/",
            json={
                "llm": {"ollama_base_url": "http://localhost:11434"},
                "simulation": {"slm_llm_ratio": 0.7},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_updated_values_persist(self, client: AsyncClient):
        await client.put(
            "/api/v1/settings/",
            json={"llm": {"ollama_default_model": "llama3:latest"}},
        )
        resp = await client.get("/api/v1/settings/")
        assert resp.json()["llm"]["ollama_default_model"] == "llama3:latest"


@pytest.mark.phase7
class TestOllamaModels:
    """SPEC: 06_API_SPEC.md#get-apiv1settingsollama-models"""

    async def test_200_returns_models_list(self, client: AsyncClient):
        resp = await client.get("/api/v1/settings/ollama-models")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert isinstance(data["models"], list)


@pytest.mark.phase7
class TestOllamaConnection:
    """SPEC: 06_API_SPEC.md#post-apiv1settingstest-ollama"""

    async def test_200_returns_status(self, client: AsyncClient):
        resp = await client.post("/api/v1/settings/test-ollama")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] in ("ok", "error")

    async def test_ok_response_has_latency(self, client: AsyncClient):
        resp = await client.post("/api/v1/settings/test-ollama")
        data = resp.json()
        if data["status"] == "ok":
            assert "latency_ms" in data
            assert "model" in data

    async def test_error_response_has_message(self, client: AsyncClient):
        # Point to bad URL first
        await client.put(
            "/api/v1/settings/",
            json={"llm": {"ollama_base_url": "http://localhost:1"}},
        )
        resp = await client.post("/api/v1/settings/test-ollama")
        data = resp.json()
        assert data["status"] == "error"
        assert "message" in data
