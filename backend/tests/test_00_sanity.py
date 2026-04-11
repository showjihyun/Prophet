"""Phase 1 sanity tests — verify project structure and imports.
SPEC: docs/spec/00_ARCHITECTURE.md
"""
import pytest


@pytest.mark.phase1
class TestProjectStructure:
    """Verify basic project imports work."""

    def test_engine_types_import(self):
        """All shared types import correctly."""
        from app.engine.types import AgentAction, SimulationStatus, AgentPersonality, AgentEmotion
        assert len(AgentAction) == 12
        assert len(SimulationStatus) == 6

    def test_models_import(self):
        """All SQLAlchemy models import correctly."""
        from app.models import (
            Simulation, SimStep, SimulationEvent,
            Community, Agent, AgentState,
            Campaign, AgentMemory, NetworkEdge,
            PropagationEvent, ExpertOpinion, EmergentEvent, LLMCall,
        )
        assert Simulation.__tablename__ == "simulations"
        assert Agent.__tablename__ == "agents"

    def test_fastapi_app_import(self):
        """FastAPI app imports and has health endpoint."""
        from app.main import app
        assert app.title == "Prophet (MCASP)"

    def test_config_import(self):
        """Settings loads with defaults."""
        from app.config import Settings
        s = Settings()
        assert s.default_llm_provider == "ollama"
        assert s.llm_tier3_ratio == 0.1


@pytest.mark.phase1
class TestMocks:
    """Verify mock environment works."""

    @pytest.mark.asyncio
    async def test_mock_llm(self, mock_llm):
        """Mock LLM returns response."""
        from harness.mocks.mock_environment import LLMPrompt
        response = await mock_llm.complete(LLMPrompt(user="test"))
        assert response.provider == "mock"
        assert response.parsed["evaluation_score"] == 0.5

    @pytest.mark.asyncio
    async def test_mock_slm_batch(self, mock_slm):
        """Mock SLM batch returns correct count."""
        from harness.mocks.mock_environment import LLMPrompt
        prompts = [LLMPrompt(user=f"test_{i}") for i in range(5)]
        responses = await mock_slm.batch_complete(prompts)
        assert len(responses) == 5
        assert mock_slm.call_count == 5
        assert mock_slm.batch_log == [5]

    @pytest.mark.asyncio
    async def test_mock_llm_embed(self, mock_llm):
        """Mock embedding returns 768-dim vector."""
        vec = await mock_llm.embed("test text")
        assert len(vec) == 768

    @pytest.mark.asyncio
    async def test_mock_llm_embed_deterministic(self, mock_llm):
        """Same input produces same embedding."""
        vec1 = await mock_llm.embed("hello world")
        vec2 = await mock_llm.embed("hello world")
        assert vec1 == vec2
