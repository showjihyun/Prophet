"""Pytest configuration and shared fixtures.
SPEC: docs/spec/09_HARNESS_SPEC.md#pytest-configuration
"""
import pytest

from harness.mocks.mock_environment import MockLLMAdapter, MockSLMAdapter, MockDatabase


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
