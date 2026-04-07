"""Dependency injection for Prophet API routes.
SPEC: docs/spec/06_API_SPEC.md
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.engine.simulation.persistence import SimulationPersistence

logger = logging.getLogger(__name__)

# Singleton orchestrator instance
_orchestrator: SimulationOrchestrator | None = None

# Shared persistence instance
_persistence = SimulationPersistence()


def _build_llm_stack():
    """Build the LLM adapter registry + gateway.

    SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry
    SPEC: docs/spec/platform/14_LLM_GATEWAY_SPEC.md

    Registers the default Ollama adapter (always available locally).
    Other providers (Claude, OpenAI, Gemini) are registered if API keys are set.
    Returns (gateway, llm_adapter) where llm_adapter is the registry itself.
    """
    from app.llm.registry import LLMAdapterRegistry
    from app.llm.gateway import LLMGateway
    from app.llm.ollama_client import OllamaAdapter

    registry = LLMAdapterRegistry()

    # Always register Ollama (local, no API key required)
    try:
        ollama = OllamaAdapter()
        registry.register_adapter("ollama", ollama)
        logger.info("LLM: Ollama adapter registered (%s)", settings.ollama_base_url)
    except Exception as exc:
        logger.warning("LLM: Ollama adapter failed to register: %s", exc)

    # Register cloud providers if API keys are configured
    if settings.anthropic_api_key:
        try:
            from app.llm.claude_client import ClaudeAdapter
            registry.register_adapter("claude", ClaudeAdapter(api_key=settings.anthropic_api_key))
            logger.info("LLM: Claude adapter registered")
        except Exception as exc:
            logger.warning("LLM: Claude adapter failed: %s", exc)

    if settings.openai_api_key:
        try:
            from app.llm.openai_client import OpenAIAdapter
            registry.register_adapter("openai", OpenAIAdapter(api_key=settings.openai_api_key))
            logger.info("LLM: OpenAI adapter registered")
        except Exception as exc:
            logger.warning("LLM: OpenAI adapter failed: %s", exc)

    if settings.gemini_api_key:
        try:
            from app.llm.gemini_client import GeminiAdapter
            registry.register_adapter("gemini", GeminiAdapter(api_key=settings.gemini_api_key))
            logger.info("LLM: Gemini adapter registered")
        except Exception as exc:
            logger.warning("LLM: Gemini adapter failed: %s", exc)

    # Build gateway with registry
    gateway = LLMGateway(registry=registry)
    logger.info("LLMGateway initialized with %d providers", len(registry._adapters))

    return gateway, registry


def get_orchestrator() -> SimulationOrchestrator:
    """Return the SimulationOrchestrator singleton.

    Automatically wires LLMGateway + Registry so the 3-tier cache chain
    and LLM cognition are active from the start.
    """
    global _orchestrator
    if _orchestrator is None:
        try:
            gateway, registry = _build_llm_stack()
            _orchestrator = SimulationOrchestrator(llm_adapter=registry, gateway=gateway)
            logger.info("SimulationOrchestrator initialized with LLMGateway")
        except Exception as exc:
            logger.warning("LLM stack init failed, running without LLM: %s", exc)
            _orchestrator = SimulationOrchestrator()
            logger.info("SimulationOrchestrator initialized (no LLM)")
    return _orchestrator


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session for request-scoped use."""
    async with async_session() as session:
        yield session


def get_persistence() -> SimulationPersistence:
    """Return the shared persistence instance."""
    return _persistence
