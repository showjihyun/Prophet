"""Settings endpoints — LLM provider configuration & simulation defaults.
SPEC: docs/spec/06_API_SPEC.md#7-settings-endpoints
SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#6-settings-integration
"""
from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import APIRouter

from app.config import settings
from app.engine.platform.registry import PlatformRegistry

router = APIRouter(
    prefix="/api/v1/settings",
    tags=["settings"],
)


@router.get("/")
async def get_settings() -> dict[str, Any]:
    """Get current system settings.
    SPEC: docs/spec/06_API_SPEC.md#get-apiv1settings
    """
    return {
        "llm": {
            "default_provider": settings.default_llm_provider,
            "ollama_base_url": settings.ollama_base_url,
            "ollama_default_model": settings.ollama_default_model,
            "slm_model": settings.slm_model,
            "ollama_embed_model": settings.ollama_embed_model,
            "anthropic_model": settings.anthropic_default_model,
            "anthropic_api_key_set": bool(settings.anthropic_api_key),
            "openai_model": settings.openai_default_model,
            "openai_api_key_set": bool(settings.openai_api_key),
        },
        "simulation": {
            "slm_llm_ratio": settings.slm_llm_ratio,
            "llm_tier3_ratio": settings.llm_tier3_ratio,
            "llm_cache_ttl": settings.llm_cache_ttl,
        },
    }


@router.put("/")
async def update_settings(body: dict[str, Any]) -> dict[str, str]:
    """Update system settings (runtime, in-memory).
    SPEC: docs/spec/06_API_SPEC.md#put-apiv1settings
    """
    llm = body.get("llm", {})
    if "default_provider" in llm:
        settings.default_llm_provider = llm["default_provider"]
    if "ollama_base_url" in llm:
        settings.ollama_base_url = llm["ollama_base_url"]
    if "ollama_default_model" in llm:
        settings.ollama_default_model = llm["ollama_default_model"]
    if "slm_model" in llm:
        settings.slm_model = llm["slm_model"]
    if "ollama_embed_model" in llm:
        settings.ollama_embed_model = llm["ollama_embed_model"]  # type: ignore[attr-defined]
    if "anthropic_api_key" in llm:
        settings.anthropic_api_key = llm["anthropic_api_key"]
    if "anthropic_model" in llm:
        settings.anthropic_default_model = llm["anthropic_model"]
    if "openai_api_key" in llm:
        settings.openai_api_key = llm["openai_api_key"]
    if "openai_model" in llm:
        settings.openai_default_model = llm["openai_model"]

    sim = body.get("simulation", {})
    if "slm_llm_ratio" in sim:
        settings.slm_llm_ratio = sim["slm_llm_ratio"]  # type: ignore[attr-defined]
    if "llm_tier3_ratio" in sim:
        settings.llm_tier3_ratio = sim["llm_tier3_ratio"]
    if "llm_cache_ttl" in sim:
        settings.llm_cache_ttl = sim["llm_cache_ttl"]

    return {"status": "ok"}


@router.get("/ollama-models")
async def list_ollama_models() -> dict[str, list[str]]:
    """List available Ollama models (calls Ollama /api/tags).
    SPEC: docs/spec/06_API_SPEC.md#get-apiv1settingsollama-models
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.ollama_base_url}/api/tags",
                timeout=5.0,
            )
            data = resp.json()
            return {"models": [m["name"] for m in data.get("models", [])]}
    except Exception:
        return {"models": []}


@router.get("/platforms")
async def list_platforms() -> dict[str, Any]:
    """List available platform plugins.
    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#6-settings-integration
    """
    registry = PlatformRegistry()
    return {
        "platforms": [
            {
                "name": p.name,
                "display_name": p.display_name,
                "actions": p.supported_actions,
            }
            for p in registry._platforms.values()
        ]
    }


@router.get("/recsys")
async def list_recsys() -> dict[str, Any]:
    """List available RecSys algorithms.
    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#6-settings-integration
    """
    registry = PlatformRegistry()
    return {
        "algorithms": [{"name": r.name} for r in registry._recsys.values()]
    }


@router.post("/test-ollama")
async def test_ollama() -> dict[str, Any]:
    """Test Ollama connection.
    SPEC: docs/spec/06_API_SPEC.md#post-apiv1settingstest-ollama
    """
    start = time.time()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.ollama_base_url}/api/tags",
                timeout=5.0,
            )
            resp.raise_for_status()
            latency = (time.time() - start) * 1000
            return {
                "status": "ok",
                "model": settings.ollama_default_model,
                "latency_ms": round(latency),
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}
