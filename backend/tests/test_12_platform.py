"""Platform Plugin system tests.

Auto-generated from SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md
SPEC Version: 0.1.0
Acceptance criteria: PLT-01 through PLT-06.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.engine.diffusion.schema import RecSysConfig
from app.engine.platform.base import PlatformPlugin, PropagationRules
from app.engine.platform.default import DefaultPlugin
from app.engine.platform.instagram import InstagramPlugin
from app.engine.platform.recsys import (
    EmbeddingRecSys,
    HotScoreRecSys,
    RecSysAlgorithm,
    WeightedRecSys,
)
from app.engine.platform.reddit import RedditPlugin
from app.engine.platform.registry import PlatformRegistry
from app.engine.platform.twitter import TwitterPlugin


pytestmark = pytest.mark.phase8


# ---------------------------------------------------------------------------
# PLT-01: Register and retrieve Twitter plugin
# ---------------------------------------------------------------------------


class TestPLT01TwitterPlugin:
    """PLT-01: Register and retrieve Twitter plugin with correct feed config."""

    def test_twitter_plugin_name(self) -> None:
        plugin = TwitterPlugin()
        assert plugin.name == "twitter"
        assert plugin.display_name == "Twitter/X"

    def test_twitter_supported_actions(self) -> None:
        plugin = TwitterPlugin()
        assert "repost" in plugin.supported_actions
        assert "like" in plugin.supported_actions
        assert "comment" in plugin.supported_actions

    def test_twitter_feed_config(self) -> None:
        plugin = TwitterPlugin()
        config = plugin.get_feed_config()
        assert isinstance(config, RecSysConfig)
        assert config.feed_capacity == 30
        assert config.w_social_affinity == 0.35
        assert config.enable_filter_bubble is True

    def test_twitter_action_weights(self) -> None:
        plugin = TwitterPlugin()
        weights = plugin.get_action_weights()
        assert weights["repost"] == 0.85
        assert "like" in weights

    def test_twitter_propagation_rules(self) -> None:
        plugin = TwitterPlugin()
        rules = plugin.get_propagation_rules()
        assert isinstance(rules, PropagationRules)
        assert rules.repost_amplification == 1.5
        assert rules.viral_threshold == 0.10

    def test_registry_get_twitter(self) -> None:
        registry = PlatformRegistry()
        plugin = registry.get_platform("twitter")
        assert plugin.name == "twitter"
        config = plugin.get_feed_config()
        assert config.feed_capacity == 30


# ---------------------------------------------------------------------------
# PLT-02: Register and retrieve Reddit plugin (different weights)
# ---------------------------------------------------------------------------


class TestPLT02RedditPlugin:
    """PLT-02: Reddit plugin has different RecSys weights than Twitter."""

    def test_reddit_plugin_name(self) -> None:
        plugin = RedditPlugin()
        assert plugin.name == "reddit"
        assert plugin.display_name == "Reddit"

    def test_reddit_different_weights_from_twitter(self) -> None:
        twitter = TwitterPlugin().get_feed_config()
        reddit = RedditPlugin().get_feed_config()
        assert twitter.w_engagement_signal != reddit.w_engagement_signal
        assert twitter.w_social_affinity != reddit.w_social_affinity
        assert reddit.w_engagement_signal == 0.40
        assert reddit.enable_filter_bubble is False

    def test_reddit_no_follow_unfollow(self) -> None:
        plugin = RedditPlugin()
        assert "follow" not in plugin.supported_actions
        assert "unfollow" not in plugin.supported_actions

    def test_reddit_propagation_algorithmic(self) -> None:
        plugin = RedditPlugin()
        rules = plugin.get_propagation_rules()
        assert rules.share_scope == "algorithmic"
        assert rules.comment_visibility == "ranked"


# ---------------------------------------------------------------------------
# PLT-03: Platform changes feed ranking behavior
# ---------------------------------------------------------------------------


class TestPLT03PlatformChangesFeedRanking:
    """PLT-03: SimulationConfig.platform changes feed ranking."""

    def test_twitter_vs_reddit_feed_capacity(self) -> None:
        registry = PlatformRegistry()
        tw = registry.get_platform("twitter").get_feed_config()
        rd = registry.get_platform("reddit").get_feed_config()
        assert tw.feed_capacity != rd.feed_capacity

    def test_twitter_vs_reddit_weights_differ(self) -> None:
        registry = PlatformRegistry()
        tw = registry.get_platform("twitter").get_feed_config()
        rd = registry.get_platform("reddit").get_feed_config()
        # Twitter favors social affinity; Reddit favors engagement signal
        assert tw.w_social_affinity > rd.w_social_affinity
        assert rd.w_engagement_signal > tw.w_engagement_signal

    def test_instagram_relationship_driven(self) -> None:
        plugin = InstagramPlugin()
        config = plugin.get_feed_config()
        assert config.w_social_affinity == 0.40
        assert config.w_social_affinity > config.w_engagement_signal


# ---------------------------------------------------------------------------
# PLT-04: RecSys algorithm swap at runtime
# ---------------------------------------------------------------------------


class TestPLT04RecSysSwap:
    """PLT-04: Hot score vs weighted produce different rankings."""

    def test_weighted_recsys_sorts_by_exposure(self) -> None:
        @dataclass
        class FakeItem:
            exposure_score: float

        items = [FakeItem(0.1), FakeItem(0.9), FakeItem(0.5)]
        algo = WeightedRecSys()
        ranked = algo.rank_feed(agent=None, candidates=items)
        scores = [i.exposure_score for i in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_hot_score_recsys_uses_likes_and_age(self) -> None:
        @dataclass
        class FakeItem:
            likes: int
            dislikes: int
            age_seconds: int

        # High-likes old item vs low-likes new item
        old_popular = FakeItem(likes=1000, dislikes=10, age_seconds=100)
        new_unpopular = FakeItem(likes=2, dislikes=0, age_seconds=90000)

        algo = HotScoreRecSys()
        ranked = algo.rank_feed(agent=None, candidates=[new_unpopular, old_popular])
        # new_unpopular has huge age bonus (90000/45000=2.0) plus small vote score
        # old_popular has log10(990)~2.996 + 100/45000~0.002 = ~2.998
        # new_unpopular has log10(2)~0.301 + 90000/45000=2.0 = ~2.301
        # So old_popular should rank higher
        assert ranked[0].likes == 1000

    def test_hot_score_vs_weighted_different_order(self) -> None:
        @dataclass
        class FakeItem:
            exposure_score: float
            likes: int
            dislikes: int
            age_seconds: int

        items = [
            FakeItem(exposure_score=0.9, likes=1, dislikes=0, age_seconds=1),
            FakeItem(exposure_score=0.1, likes=100, dislikes=0, age_seconds=1),
        ]
        weighted_ranked = WeightedRecSys().rank_feed(agent=None, candidates=items)
        hot_ranked = HotScoreRecSys().rank_feed(agent=None, candidates=items)

        assert weighted_ranked[0].exposure_score == 0.9
        assert hot_ranked[0].likes == 100

    def test_embedding_recsys_passthrough(self) -> None:
        items = [1, 2, 3]
        algo = EmbeddingRecSys()
        assert algo.rank_feed(agent=None, candidates=items) == items

    def test_registry_swap_recsys(self) -> None:
        registry = PlatformRegistry()
        w = registry.get_recsys("weighted")
        h = registry.get_recsys("hot_score")
        assert w.name == "weighted"
        assert h.name == "hot_score"
        assert w.name != h.name


# ---------------------------------------------------------------------------
# PLT-05: Settings API lists all platforms
# ---------------------------------------------------------------------------


class TestPLT05SettingsAPI:
    """PLT-05: Registry returns all four built-in platforms."""

    def test_list_platforms_contains_all_builtins(self) -> None:
        registry = PlatformRegistry()
        names = registry.list_platforms()
        assert "default" in names
        assert "twitter" in names
        assert "reddit" in names
        assert "instagram" in names
        assert len(names) == 4

    def test_list_recsys_contains_all_builtins(self) -> None:
        registry = PlatformRegistry()
        names = registry.list_recsys()
        assert "weighted" in names
        assert "hot_score" in names
        assert "embedding" in names
        assert len(names) == 3

    def test_platform_plugin_has_required_attrs(self) -> None:
        registry = PlatformRegistry()
        for name in registry.list_platforms():
            p = registry.get_platform(name)
            assert hasattr(p, "name")
            assert hasattr(p, "display_name")
            assert hasattr(p, "supported_actions")
            assert isinstance(p.get_feed_config(), RecSysConfig)
            assert isinstance(p.get_action_weights(), dict)
            assert isinstance(p.get_propagation_rules(), PropagationRules)


# ---------------------------------------------------------------------------
# PLT-06: Unknown platform name raises error
# ---------------------------------------------------------------------------


class TestPLT06UnknownPlatformError:
    """PLT-06: ValueError for unknown platform/recsys names."""

    def test_unknown_platform_raises_value_error(self) -> None:
        registry = PlatformRegistry()
        with pytest.raises(ValueError, match="Unknown platform 'tiktok'"):
            registry.get_platform("tiktok")

    def test_unknown_recsys_raises_value_error(self) -> None:
        registry = PlatformRegistry()
        with pytest.raises(ValueError, match="Unknown RecSys algorithm"):
            registry.get_recsys("nonexistent")

    def test_custom_plugin_registration(self) -> None:
        """Verify custom plugins can be registered and retrieved."""
        registry = PlatformRegistry()

        class CustomPlugin(PlatformPlugin):
            name = "custom"
            display_name = "Custom Test"
            supported_actions = ["view", "like"]

            def get_feed_config(self) -> RecSysConfig:
                return RecSysConfig()

            def get_action_weights(self) -> dict[str, float]:
                return {"like": 0.5}

            def get_propagation_rules(self) -> PropagationRules:
                return PropagationRules()

        registry.register_platform(CustomPlugin())
        assert "custom" in registry.list_platforms()
        assert registry.get_platform("custom").display_name == "Custom Test"
