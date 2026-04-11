"""Pytest configuration and shared fixtures.
SPEC: docs/spec/09_HARNESS_SPEC.md#pytest-configuration
"""
import pytest

from harness.mocks.mock_environment import MockLLMAdapter, MockSLMAdapter, MockDatabase
from harness.runners.agent_harness import AgentHarness
from harness.runners.network_harness import NetworkHarness
from harness.runners.diffusion_harness import DiffusionHarness


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
