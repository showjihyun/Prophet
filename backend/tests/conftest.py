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
