"""Pytest configuration and shared fixtures.
SPEC: docs/spec/09_HARNESS_SPEC.md#pytest-configuration
"""
import pytest

from harness.mocks.mock_environment import MockLLMAdapter, MockSLMAdapter, MockDatabase
from harness.runners.agent_harness import AgentHarness
from harness.runners.network_harness import NetworkHarness
from harness.runners.diffusion_harness import DiffusionHarness


@pytest.fixture(scope="session", autouse=True)
async def _bootstrap_schema():
    """Create extensions + all tables once per pytest session.

    API tests use ``httpx.AsyncClient(transport=ASGITransport(app))``
    which runs requests against the ASGI app without firing FastAPI's
    startup/shutdown lifecycle. That means ``app.main.lifespan`` never
    runs during tests — so ``CREATE EXTENSION vector`` and
    ``metadata.create_all`` never execute, and every query that hits
    the DB trips over ``relation "simulations" does not exist``.

    Locally this went unnoticed because dev databases were schema'd
    by a prior live run or by ``alembic upgrade head``. On a fresh
    CI Postgres container, nothing has created the schema yet, so
    this fixture does the bootstrap that the lifespan would have.

    Session-scoped so the cost is paid once. Pure-unit tests that
    never touch a DB still pay the ``CREATE EXTENSION`` round-trip
    but the cost is negligible and it keeps the fixture unconditional.

    Swallows exceptions so tests that run without a DB (pure harness
    unit tests, CI-less laptop runs) aren't blocked.
    """
    import sqlalchemy
    try:
        from app.database import engine, Base
        import app.models  # noqa: F401 — register every model on Base.metadata
        async with engine.begin() as conn:
            await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        # Pure-unit tests may not have a reachable DB — skip silently.
        pass
    yield


@pytest.fixture
def mock_llm():
    """Mock LLM adapter (Tier 3)."""
    return MockLLMAdapter()


@pytest.fixture
def mock_slm():
    """Mock SLM adapter (Tier 1)."""
    return MockSLMAdapter()


@pytest.fixture
async def mock_db():
    """In-memory SQLite database for testing."""
    db = MockDatabase()
    await db.setup()
    yield db.session
    await db.teardown()


@pytest.fixture
def agent_harness():
    """Agent harness for per-layer unit tests.
    SPEC: docs/spec/09_HARNESS_SPEC.md#pytest-configuration
    """
    return AgentHarness()


@pytest.fixture
def network_harness():
    """Network harness for network generation unit tests.
    SPEC: docs/spec/09_HARNESS_SPEC.md#pytest-configuration
    """
    return NetworkHarness()


@pytest.fixture
def diffusion_harness():
    """Diffusion harness for single-step diffusion unit tests.
    SPEC: docs/spec/09_HARNESS_SPEC.md#pytest-configuration
    """
    return DiffusionHarness()


@pytest.fixture(autouse=True)
async def _clean_simulation_db():
    """Truncate simulation-related DB tables before each test.

    Historical context: the tests were authored while ``persist_creation``
    silently swallowed failures, which kept the DB incidentally clean.
    Round 4 made persistence strict, so we now need explicit cleanup to
    preserve test isolation (e.g. ``TestListSimulations::test_empty_list``
    must actually see an empty list).

    The fixture is a no-op on a working empty DB and harmless for unit
    tests that don't touch persistence. DB failures are swallowed so pure
    unit tests without a reachable DB are unaffected.
    """
    from sqlalchemy import text
    try:
        from app.database import async_session
        async with async_session() as session:
            await session.execute(text("TRUNCATE TABLE simulations CASCADE"))
            await session.execute(text("TRUNCATE TABLE projects CASCADE"))
            await session.commit()
    except Exception:
        # Pure-unit tests may not have a reachable DB — skip cleanup silently.
        pass
    yield
