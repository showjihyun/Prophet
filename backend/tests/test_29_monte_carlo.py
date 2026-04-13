"""Monte Carlo endpoint tests.

Auto-generated from SPEC: docs/spec/29_MONTE_CARLO_SPEC.md
SPEC Version: 0.1.0

Covers MC-AC-01 ~ MC-AC-05 (engine + API). FE acceptance criteria
(MC-AC-06 ~ 08) are covered by `frontend/src/__tests__/DecidePanel.test.tsx`.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api import deps as _deps_mod


@pytest.fixture(autouse=True)
def _reset_orchestrator():
    _deps_mod._orchestrator = None
    yield
    _deps_mod._orchestrator = None


def _valid_create_body() -> dict:
    return {
        "name": "MC Test Sim",
        "campaign": {
            "name": "Camp",
            "budget": 1000,
            "channels": ["sns"],
            "message": "Hello MC",
        },
        # Keep tiny so MC sweep finishes inside the test budget.
        "max_steps": 2,
        "communities": [
            {"name": "Alpha", "size": 20},
            {"name": "Beta", "size": 20},
        ],
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


# --------------------------------------------------------------------------- #
# Engine-level (MC-AC-01)                                                      #
# --------------------------------------------------------------------------- #


def test_schema_imports():
    """SPEC §1.1 — RunSummary / MonteCarloResult are importable from diffusion.schema."""
    from app.engine.diffusion.schema import MonteCarloResult, RunSummary  # noqa: F401
    from app.engine.simulation.monte_carlo import MonteCarloRunner  # noqa: F401


# --------------------------------------------------------------------------- #
# API contract (MC-AC-02 ~ 05)                                                 #
# --------------------------------------------------------------------------- #


class TestMonteCarloEndpoint:
    """SPEC: 29_MONTE_CARLO_SPEC.md#21-endpoint-mc-api-01"""

    async def test_rejects_n_runs_lt_2(self, client: AsyncClient, sim_id: str):
        """MC-AC-02 — single-seed isn't Monte Carlo."""
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 1},
        )
        assert resp.status_code == 422

    async def test_rejects_n_runs_gt_50(self, client: AsyncClient, sim_id: str):
        """MC-AC-03 — guardrail against runaway sweeps."""
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 51},
        )
        assert resp.status_code == 422

    async def test_404_on_unknown_simulation(self, client: AsyncClient):
        """SPEC §2.4 — unknown simulation_id → 404."""
        resp = await client.post(
            "/api/v1/simulations/00000000-0000-0000-0000-000000000000/monte-carlo",
            json={"n_runs": 2},
        )
        assert resp.status_code == 404

    @pytest.mark.slow
    async def test_response_shape(self, client: AsyncClient, sim_id: str):
        """MC-AC-04 — response includes all aggregate fields."""
        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 2, "max_concurrency": 2},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        for key in (
            "simulation_id",
            "n_runs",
            "viral_probability",
            "expected_reach",
            "p5_reach",
            "p50_reach",
            "p95_reach",
            "community_adoption",
            "run_summaries",
        ):
            assert key in data, f"missing key: {key}"
        assert data["n_runs"] == 2
        assert 0.0 <= data["viral_probability"] <= 1.0
        assert isinstance(data["run_summaries"], list)

    @pytest.mark.slow
    async def test_does_not_mutate_source(self, client: AsyncClient, sim_id: str):
        """MC-AC-05 — original simulation's step_history must be untouched."""
        before = await client.get(f"/api/v1/simulations/{sim_id}")
        before_step = before.json().get("current_step", 0)

        resp = await client.post(
            f"/api/v1/simulations/{sim_id}/monte-carlo",
            json={"n_runs": 2, "max_concurrency": 2},
        )
        assert resp.status_code == 200

        after = await client.get(f"/api/v1/simulations/{sim_id}")
        after_step = after.json().get("current_step", 0)
        assert before_step == after_step, "MC sweep mutated source simulation"
