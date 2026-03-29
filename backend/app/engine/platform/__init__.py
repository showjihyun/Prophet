"""Platform Plugin system for SNS simulation.
SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md
"""
from app.engine.platform.base import PlatformPlugin, PropagationRules
from app.engine.platform.recsys import RecSysAlgorithm, WeightedRecSys, HotScoreRecSys, EmbeddingRecSys
from app.engine.platform.registry import PlatformRegistry

__all__ = [
    "PlatformPlugin",
    "PropagationRules",
    "RecSysAlgorithm",
    "WeightedRecSys",
    "HotScoreRecSys",
    "EmbeddingRecSys",
    "PlatformRegistry",
]
