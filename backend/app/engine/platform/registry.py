"""Platform plugin registry.
SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#5-plugin-registry
"""
from __future__ import annotations

from app.engine.platform.base import PlatformPlugin
from app.engine.platform.recsys import RecSysAlgorithm


class PlatformRegistry:
    """Central registry for platform plugins and RecSys algorithms.

    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#5-plugin-registry
    """

    def __init__(self) -> None:
        self._platforms: dict[str, PlatformPlugin] = {}
        self._recsys: dict[str, RecSysAlgorithm] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Auto-register all built-in plugins."""
        from app.engine.platform.custom import CustomPlatform
        from app.engine.platform.default import DefaultPlugin
        from app.engine.platform.instagram import InstagramPlugin
        from app.engine.platform.reddit import RedditPlugin
        from app.engine.platform.twitter import TwitterPlugin
        from app.engine.platform.recsys import (
            EmbeddingRecSys,
            HotScoreRecSys,
            WeightedRecSys,
        )

        for p in [
            DefaultPlugin(),
            TwitterPlugin(),
            RedditPlugin(),
            InstagramPlugin(),
            CustomPlatform(),
        ]:
            self._platforms[p.name] = p
        for r in [WeightedRecSys(), HotScoreRecSys(), EmbeddingRecSys()]:
            self._recsys[r.name] = r

    def register_platform(self, plugin: PlatformPlugin) -> None:
        """Register a custom platform plugin."""
        self._platforms[plugin.name] = plugin

    def get_platform(self, name: str) -> PlatformPlugin:
        """Retrieve a platform plugin by name.

        Raises:
            ValueError: If the platform name is not registered.
        """
        if name not in self._platforms:
            raise ValueError(
                f"Unknown platform '{name}'. "
                f"Available: {list(self._platforms.keys())}"
            )
        return self._platforms[name]

    def list_platforms(self) -> list[str]:
        """Return list of registered platform names."""
        return list(self._platforms.keys())

    def register_recsys(self, algo: RecSysAlgorithm) -> None:
        """Register a custom RecSys algorithm."""
        self._recsys[algo.name] = algo

    def get_recsys(self, name: str) -> RecSysAlgorithm:
        """Retrieve a RecSys algorithm by name.

        Raises:
            ValueError: If the algorithm name is not registered.
        """
        if name not in self._recsys:
            raise ValueError(
                f"Unknown RecSys algorithm '{name}'. "
                f"Available: {list(self._recsys.keys())}"
            )
        return self._recsys[name]

    def list_recsys(self) -> list[str]:
        """Return list of registered RecSys algorithm names."""
        return list(self._recsys.keys())
