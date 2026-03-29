"""RecSys algorithm plugins.
SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#4-recsys-algorithm-plugin
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any


class RecSysAlgorithm(ABC):
    """Pluggable recommendation algorithm.

    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#4-recsys-algorithm-plugin
    """
    name: str

    @abstractmethod
    def rank_feed(
        self,
        agent: Any,
        candidates: list[Any],
        social_graph: Any | None = None,
    ) -> list[Any]:
        """Rank and filter candidates for this agent's feed."""
        ...


class WeightedRecSys(RecSysAlgorithm):
    """Current Prophet default: weighted 5-factor formula.

    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#4-recsys-algorithm-plugin
    """
    name = "weighted"

    def rank_feed(
        self,
        agent: Any,
        candidates: list[Any],
        social_graph: Any | None = None,
    ) -> list[Any]:
        """Rank candidates by feed_rank_score (weighted sum of 5 factors)."""
        return sorted(
            candidates,
            key=lambda c: getattr(c, "exposure_score", 0),
            reverse=True,
        )


class HotScoreRecSys(RecSysAlgorithm):
    """Reddit-style hot score ranking.

    h = sign(u-d) * log10(max(|u-d|, 1)) + age_seconds / 45000

    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#4-recsys-algorithm-plugin
    """
    name = "hot_score"

    def rank_feed(
        self,
        agent: Any,
        candidates: list[Any],
        social_graph: Any | None = None,
    ) -> list[Any]:
        """Rank candidates using Reddit hot-score algorithm."""
        def hot_score(item: Any) -> float:
            ups = getattr(item, "likes", 1)
            downs = getattr(item, "dislikes", 0)
            s = ups - downs
            order = math.log10(max(abs(s), 1))
            sign = 1 if s > 0 else (-1 if s < 0 else 0)
            age = max(getattr(item, "age_seconds", 1), 1)
            return round(sign * order + age / 45000, 7)

        return sorted(candidates, key=hot_score, reverse=True)


class EmbeddingRecSys(RecSysAlgorithm):
    """Embedding similarity-based ranking (sentence-transformers or TwHIN-BERT style).

    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#4-recsys-algorithm-plugin

    Note: full implementation requires sentence-transformers integration.
    Currently acts as passthrough; will be extended in a future phase.
    """
    name = "embedding"

    def rank_feed(
        self,
        agent: Any,
        candidates: list[Any],
        social_graph: Any | None = None,
    ) -> list[Any]:
        """Passthrough — future: rank by embedding cosine similarity."""
        return candidates
