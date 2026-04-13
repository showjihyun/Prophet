"""Dependency injection for Prophet API routes.

SPEC: docs/spec/06_API_SPEC.md
SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#composition-root

**Composition Root**

This module is the *composition root* of the Prophet backend — the one
and only place where concrete infrastructure types
(:class:`SimulationPersistence`, :class:`SqlSimulationRepository`,
:class:`SqlProjectRepository`, :class:`ConnectionManager`) are
instantiated and wired together.

Every other module in ``app/`` depends on **Protocols** or abstract
interfaces, never on the concrete types. This rule is enforced by
``TestCompositionRoot`` in ``tests/test_25_simulation_service.py`` —
adding a new ``from app.engine.simulation.persistence import
SimulationPersistence`` anywhere outside this module (or
``app/repositories/``) will fail CI.

If you need a new infrastructure dependency:

1. Define a Protocol in ``app/repositories/protocols.py`` or
   ``app/services/ports.py``.
2. Implement the concrete type in ``app/repositories/`` or the relevant
   infrastructure module.
3. Instantiate the concrete type **here** and expose a ``get_*``
   FastAPI dependency that returns the Protocol type.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.engine.simulation.orchestrator import SimulationOrchestrator
from app.llm.gateway import LLMGateway
from app.repositories.simulation_persistence import SimulationPersistence
from app.repositories.simulation_repo import SqlSimulationRepository
from app.repositories.project_repo import SqlProjectRepository
from app.services.community_opinion_service import CommunityOpinionService
from app.services.simulation_service import SimulationService

logger = logging.getLogger(__name__)

# Singleton orchestrator + gateway instances (wired together in
# :func:`get_orchestrator`). Exposing the gateway separately lets the
# CommunityOpinionService share the same L1/L2/L3 cache chain that
# agent cognition uses, rather than building a second isolated stack.
_orchestrator: SimulationOrchestrator | None = None
_gateway: LLMGateway | None = None
# Guard against concurrent construction under multi-request cold start.
import threading as _threading
_init_lock = _threading.Lock()

# Shared persistence + repository instances
_persistence = SimulationPersistence()
_sim_repo = SqlSimulationRepository(persistence=_persistence)
_project_repo = SqlProjectRepository()


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

    # Chinese Top 3 (OpenAI-compatible, all tier-3 capable)
    if settings.deepseek_api_key:
        try:
            from app.llm.openai_compat import DeepSeekAdapter
            registry.register_adapter(
                "deepseek",
                DeepSeekAdapter(
                    api_key=settings.deepseek_api_key,
                    base_url=settings.deepseek_base_url,
                    default_model=settings.deepseek_default_model,
                ),
            )
            logger.info("LLM: DeepSeek adapter registered")
        except Exception as exc:
            logger.warning("LLM: DeepSeek adapter failed: %s", exc)

    if settings.qwen_api_key:
        try:
            from app.llm.openai_compat import QwenAdapter
            registry.register_adapter(
                "qwen",
                QwenAdapter(
                    api_key=settings.qwen_api_key,
                    base_url=settings.qwen_base_url,
                    default_model=settings.qwen_default_model,
                ),
            )
            logger.info("LLM: Qwen adapter registered")
        except Exception as exc:
            logger.warning("LLM: Qwen adapter failed: %s", exc)

    if settings.moonshot_api_key:
        try:
            from app.llm.openai_compat import MoonshotAdapter
            registry.register_adapter(
                "moonshot",
                MoonshotAdapter(
                    api_key=settings.moonshot_api_key,
                    base_url=settings.moonshot_base_url,
                    default_model=settings.moonshot_default_model,
                ),
            )
            logger.info("LLM: Moonshot adapter registered")
        except Exception as exc:
            logger.warning("LLM: Moonshot adapter failed: %s", exc)

    if settings.glm_api_key:
        try:
            from app.llm.openai_compat import ZhipuGLMAdapter
            registry.register_adapter(
                "glm",
                ZhipuGLMAdapter(
                    api_key=settings.glm_api_key,
                    base_url=settings.glm_base_url,
                    default_model=settings.glm_default_model,
                ),
            )
            logger.info("LLM: Zhipu GLM adapter registered")
        except Exception as exc:
            logger.warning("LLM: Zhipu GLM adapter failed: %s", exc)

    # Build gateway with registry
    gateway = LLMGateway(registry=registry)
    logger.info("LLMGateway initialized with %d providers", len(registry._adapters))

    return gateway, registry


def get_orchestrator() -> SimulationOrchestrator:
    """Return the SimulationOrchestrator singleton.

    Automatically wires LLMGateway + Registry so the 3-tier cache chain
    and LLM cognition are active from the start. Thread-safe via
    ``_init_lock`` so concurrent requests during cold start don't race.
    """
    global _orchestrator, _gateway
    if _orchestrator is not None:
        return _orchestrator
    with _init_lock:
        # Double-check after acquiring the lock.
        if _orchestrator is not None:
            return _orchestrator
        try:
            gateway, registry = _build_llm_stack()
            _gateway = gateway
            _orchestrator = SimulationOrchestrator(
                llm_adapter=registry, gateway=gateway,
                session_factory=async_session,
            )
            logger.info("SimulationOrchestrator initialized with LLMGateway + pgvector memory")
        except Exception as exc:
            logger.warning("LLM stack init failed, running without LLM: %s", exc)
            _orchestrator = SimulationOrchestrator(session_factory=async_session)
            logger.info("SimulationOrchestrator initialized (no LLM, pgvector memory only)")
    return _orchestrator


def get_llm_gateway() -> LLMGateway:
    """Return the shared LLMGateway singleton.

    Builds the orchestrator lazily on first call so the gateway and
    orchestrator always share one adapter registry + cache chain.
    Thread-safe — delegates to ``get_orchestrator()`` which holds the lock.
    """
    global _gateway
    if _gateway is not None:
        return _gateway
    # Force orchestrator construction — also populates _gateway.
    get_orchestrator()
    if _gateway is None:
        with _init_lock:
            if _gateway is None:
                gateway, _ = _build_llm_stack()
                _gateway = gateway
    return _gateway


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session for request-scoped use."""
    async with async_session() as session:
        yield session


def get_simulation_repo() -> SqlSimulationRepository:
    """Return the shared SimulationRepository instance.
    SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#2.1
    """
    return _sim_repo


def get_project_repo() -> SqlProjectRepository:
    """Return the shared ProjectRepository instance.
    SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#2.2
    """
    return _project_repo


def get_simulation_service() -> SimulationService:
    """Return a SimulationService wired with orchestrator + repo + notifier.
    SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#3.1

    The ConnectionManager (WebSocket) structurally satisfies the
    NotificationPort Protocol — no explicit adapter needed.
    """
    from app.api.ws import manager as ws_manager
    return SimulationService(
        orchestrator=get_orchestrator(),
        repo=_sim_repo,
        notifier=ws_manager,
    )


def get_community_opinion_service() -> CommunityOpinionService:
    """Return a CommunityOpinionService wired to the shared orchestrator + gateway.
    SPEC: docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis
    """
    return CommunityOpinionService(
        orchestrator=get_orchestrator(),
        gateway=get_llm_gateway(),
    )
