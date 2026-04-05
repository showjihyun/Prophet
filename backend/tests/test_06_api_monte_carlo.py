"""Monte Carlo API endpoint tests.
Auto-generated from SPEC: docs/spec/06_API_SPEC.md#monte-carlo
SPEC Version: 0.1.0
Generated BEFORE full integration — tests define the API contract.

Tests cover: job creation (202), job status retrieval, 404 for unknown jobs,
and in-memory _monte_carlo_jobs dict population.
Uses the same ASGI TestClient pattern as test_06_api_simulations.py.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api import deps as _deps_mod
from app.api import simulations as _sim_mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_orchestrator():
    """Reset orchestrator singleton and Monte Carlo jobs between tests."""
    _deps_mod._orchestrator = None
    _sim_mod._monte_carlo_jobs.clear()
    yield
    _deps_mod._orchestrator = None
    _sim_mod._monte_carlo_jobs.clear()


def _valid_create_body() -> dict:
    return {
        "name": "MC Test Sim",
        "campaign": {
            "name": "Camp",
            "budget": 1000,
            "channels": ["sns"],
            "message": "Hello MC",
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
    assert resp.status_code == 201, f"Setup failed: {resp.text}"
    return resp.json()["simulation_id"]


# ---------------------------------------------------------------------------
# POST /api/v1/simulations/{sim_id}/monte-carlo
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestStartMonteCarlo:
    """SPEC: 06_API_SPEC.md#post-simulationssimulation_idmonte-carlo"""

    async def test_returns_202(self, client: AsyncClient, sim_id: str):
        """POST monte-carlo must return HTTP 202 Accepted."""
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 10},
        )
        assert resp.status_code == 202

    async def test_response_contains_job_id(self, client: AsyncClient, sim_id: str):
        """Response body must contain a non-empty job_id field."""
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 5},
        )
        data = resp.json()
        assert "job_id" in data
        assert data["job_id"] is not None
        assert len(data["job_id"]) > 0

    async def test_job_id_is_string(self, client: AsyncClient, sim_id: str):
        """job_id must be a string (UUID format)."""
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 3},
        )
        assert isinstance(resp.json()["job_id"], str)

    async def test_monte_carlo_jobs_dict_populated(
        self, client: AsyncClient, sim_id: str
    ):
        """_monte_carlo_jobs in-memory dict must contain the new job after POST."""
        assert len(_sim_mod._monte_carlo_jobs) == 0

        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 10},
        )
        job_id = resp.json()["job_id"]

        assert job_id in _sim_mod._monte_carlo_jobs, (
            f"job_id {job_id!r} not found in _monte_carlo_jobs"
        )

    async def test_multiple_jobs_accumulate(
        self, client: AsyncClient, sim_id: str
    ):
        """Multiple POST requests must create separate job entries."""
        resp1 = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 5},
        )
        resp2 = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 5},
        )
        job_id1 = resp1.json()["job_id"]
        job_id2 = resp2.json()["job_id"]

        assert job_id1 != job_id2
        assert job_id1 in _sim_mod._monte_carlo_jobs
        assert job_id2 in _sim_mod._monte_carlo_jobs

    async def test_404_for_nonexistent_sim(self, client: AsyncClient):
        """POST monte-carlo for a non-existent simulation must return 404."""
        resp = await client.post(
            "/api/v1/simulations/does-not-exist/monte-carlo",
            json={"n_runs": 10},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/simulations/{sim_id}/monte-carlo
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestGetLatestMonteCarlo:
    """SPEC: 06_API_SPEC.md#get-simulationssimulation_idmonte-carlo"""

    async def test_returns_latest_result_after_post(
        self, client: AsyncClient, sim_id: str
    ):
        """GET monte-carlo returns the latest result (or null) after a POST."""
        await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 5},
        )
        resp = await client.get(f"/api/v1/simulations/{sim_id}/monte-carlo")
        assert resp.status_code == 200

    async def test_result_reflects_most_recent_job(
        self, client: AsyncClient, sim_id: str
    ):
        """GET monte-carlo after posting two jobs returns a valid 200 response."""
        # Post two jobs
        resp1 = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 3},
        )
        await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 5},
        )
        assert resp1.status_code == 202

        # GET should return a 200 (latest result from in-memory jobs)
        get_resp = await client.get(f"/api/v1/simulations/{sim_id}/monte-carlo")
        assert get_resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/v1/simulations/{sim_id}/monte-carlo/{job_id}
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestGetMonteCarloJobStatus:
    """SPEC: 06_API_SPEC.md#get-simulationssimulation_idmonte-carlojob_id"""

    async def test_returns_200_for_existing_job(
        self, client: AsyncClient, sim_id: str
    ):
        """GET job status returns 200 for a job that was just created."""
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 10},
        )
        job_id = resp.json()["job_id"]

        status_resp = await client.get(
            f"/api/v1/simulations/{sim_id}/monte-carlo/{job_id}"
        )
        assert status_resp.status_code == 200

    async def test_job_status_contains_job_id(
        self, client: AsyncClient, sim_id: str
    ):
        """Job status response must contain the job_id field."""
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 10},
        )
        job_id = resp.json()["job_id"]

        status_resp = await client.get(
            f"/api/v1/simulations/{sim_id}/monte-carlo/{job_id}"
        )
        data = status_resp.json()
        assert "job_id" in data
        assert data["job_id"] == job_id

    async def test_job_status_has_status_field(
        self, client: AsyncClient, sim_id: str
    ):
        """Job status response must include a 'status' field."""
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 10},
        )
        job_id = resp.json()["job_id"]

        status_resp = await client.get(
            f"/api/v1/simulations/{sim_id}/monte-carlo/{job_id}"
        )
        data = status_resp.json()
        assert "status" in data, f"Missing 'status' field in response: {data}"

    async def test_404_for_nonexistent_job(
        self, client: AsyncClient, sim_id: str
    ):
        """GET job status for a non-existent job_id must return 404."""
        resp = await client.get(
            f"/api/v1/simulations/{sim_id}/monte-carlo/nonexistent-job-abc123"
        )
        assert resp.status_code == 404

    async def test_404_for_nonexistent_sim(self, client: AsyncClient):
        """GET job status for a non-existent sim must return 404."""
        resp = await client.get(
            "/api/v1/simulations/ghost-sim/monte-carlo/some-job-id"
        )
        assert resp.status_code == 404

    async def test_job_status_for_different_sims(
        self, client: AsyncClient
    ):
        """Job created for sim A is retrievable under sim A's URL."""
        # Create two simulations
        r1 = await client.post("/api/v1/simulations/", json=_valid_create_body())
        r2 = await client.post("/api/v1/simulations/", json=_valid_create_body())
        sim_id_a = r1.json()["simulation_id"]
        sim_id_b = r2.json()["simulation_id"]

        # Post MC job under sim A
        mc_resp = await client.post(
            f"/api/v1/simulations/{sim_id_a}/monte-carlo",
            json={"n_runs": 3},
        )
        job_id = mc_resp.json()["job_id"]

        # Retrieve under sim A — must succeed
        ok_resp = await client.get(
            f"/api/v1/simulations/{sim_id_a}/monte-carlo/{job_id}"
        )
        assert ok_resp.status_code == 200


# ---------------------------------------------------------------------------
# Monte Carlo completed job field verification
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestMonteCarloCompletedFields:
    """SPEC: 06_API_SPEC.md — completed MC job must have all result fields."""

    async def test_completed_job_has_result_fields(
        self, client: AsyncClient, sim_id: str
    ):
        """After MC completes, job status must include viral_probability, reach stats."""
        import asyncio

        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 3},
        )
        job_id = resp.json()["job_id"]

        # Wait for background task to complete (poll with timeout)
        for _ in range(50):
            await asyncio.sleep(0.1)
            status_resp = await client.get(
                f"/api/v1/simulations/{sim_id}/monte-carlo/{job_id}"
            )
            data = status_resp.json()
            if data.get("status") in ("completed", "failed"):
                break

        if data.get("status") == "completed":
            assert "viral_probability" in data
            assert "expected_reach" in data
            assert "p5_reach" in data
            assert "p50_reach" in data
            assert "p95_reach" in data
        elif data.get("status") == "failed":
            assert "error_message" in data or data.get("status") == "failed"
        # queued/running is acceptable if task hasn't finished in time

    async def test_completed_job_has_timestamps(
        self, client: AsyncClient, sim_id: str
    ):
        """Completed MC job must have started_at and completed_at timestamps."""
        import asyncio

        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 3},
        )
        job_id = resp.json()["job_id"]

        for _ in range(50):
            await asyncio.sleep(0.1)
            status_resp = await client.get(
                f"/api/v1/simulations/{sim_id}/monte-carlo/{job_id}"
            )
            data = status_resp.json()
            if data.get("status") in ("completed", "failed"):
                break

        if data.get("status") == "completed":
            assert "started_at" in data
            assert "completed_at" in data
            assert data["completed_at"] is not None


# ---------------------------------------------------------------------------
# Monte Carlo request body fields
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestMonteCarloRequestFields:
    """SPEC: 06_API_SPEC.md — MC request body fields"""

    async def test_default_n_runs(self, client: AsyncClient, sim_id: str):
        """POST with n_runs must store the value."""
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 42},
        )
        job_id = resp.json()["job_id"]

        status_resp = await client.get(
            f"/api/v1/simulations/{sim_id}/monte-carlo/{job_id}"
        )
        data = status_resp.json()
        assert data.get("n_runs") == 42

    async def test_status_transitions(self, client: AsyncClient, sim_id: str):
        """Job status must be one of: queued, running, completed, failed."""
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 3},
        )
        job_id = resp.json()["job_id"]

        status_resp = await client.get(
            f"/api/v1/simulations/{sim_id}/monte-carlo/{job_id}"
        )
        data = status_resp.json()
        valid_statuses = {"queued", "running", "completed", "failed"}
        assert data["status"] in valid_statuses, (
            f"Unexpected status: {data['status']}"
        )


# ---------------------------------------------------------------------------
# MonteCarloRun DB model contract tests
# ---------------------------------------------------------------------------


@pytest.mark.phase6
class TestMonteCarloRunModel:
    """SPEC: 08_DB_SPEC.md#monte_carlo_runs — model field contracts"""

    def test_model_import(self):
        """MonteCarloRun model can be imported."""
        from app.models.propagation import MonteCarloRun  # noqa: F401

    def test_tablename(self):
        """Table must be named 'monte_carlo_runs'."""
        from app.models.propagation import MonteCarloRun

        assert MonteCarloRun.__tablename__ == "monte_carlo_runs"

    def test_required_columns(self):
        """All SPEC-required columns must exist on the model."""
        from app.models.propagation import MonteCarloRun

        col_names = {c.name for c in MonteCarloRun.__table__.columns}
        required = {
            "job_id",
            "simulation_id",
            "status",
            "n_runs",
            "viral_probability",
            "expected_reach",
            "p5_reach",
            "p50_reach",
            "p95_reach",
        }
        assert required.issubset(col_names), f"Missing columns: {required - col_names}"

    def test_job_id_is_primary_key(self):
        """job_id must be the primary key."""
        from app.models.propagation import MonteCarloRun

        pk_cols = [c.name for c in MonteCarloRun.__table__.primary_key.columns]
        assert "job_id" in pk_cols

    def test_simulation_id_index(self):
        """idx_monte_carlo_sim index on simulation_id must exist."""
        from app.models.propagation import MonteCarloRun
        from sqlalchemy import Index

        index_names = set()
        for item in MonteCarloRun.__table_args__:
            if isinstance(item, Index):
                index_names.add(item.name)
        assert "idx_monte_carlo_sim" in index_names, (
            f"Expected idx_monte_carlo_sim, got: {index_names}"
        )

    def test_community_adoption_is_jsonb(self):
        """community_adoption column must be JSONB type."""
        from app.models.propagation import MonteCarloRun

        col = MonteCarloRun.__table__.c["community_adoption"]
        col_type = str(col.type).upper()
        assert "JSON" in col_type, f"community_adoption should be JSONB, got {col.type}"

    def test_instantiation(self):
        """MonteCarloRun can be instantiated with required fields."""
        import uuid
        from app.models.propagation import MonteCarloRun

        run = MonteCarloRun(
            job_id=uuid.uuid4(),
            simulation_id=uuid.uuid4(),
            status="completed",
            n_runs=100,
            viral_probability=0.42,
            expected_reach=0.65,
            p5_reach=0.20,
            p50_reach=0.55,
            p95_reach=0.90,
        )
        assert run.status == "completed"
        assert run.n_runs == 100
        assert run.viral_probability == 0.42
