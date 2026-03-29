"""Twitter/X platform plugin.
SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#3-built-in-platform-plugins
"""
from app.engine.diffusion.schema import RecSysConfig
from app.engine.platform.base import PlatformPlugin, PropagationRules


class TwitterPlugin(PlatformPlugin):
    """Twitter/X simulation plugin.

    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#twitterx-plugin
    """
    name = "twitter"
    display_name = "Twitter/X"
    supported_actions = [
        "ignore", "view", "like", "comment", "share", "repost",
        "follow", "unfollow", "mute", "search",
    ]

    def get_feed_config(self) -> RecSysConfig:
        return RecSysConfig(
            feed_capacity=30,
            w_recency=0.15,
            w_social_affinity=0.35,
            w_interest_match=0.25,
            w_engagement_signal=0.20,
            w_ad_boost=0.05,
            enable_filter_bubble=True,
            diversity_penalty=0.03,
        )

    def get_action_weights(self) -> dict[str, float]:
        return {
            "repost": 0.85,
            "like": 0.4,
            "comment": 0.5,
            "share": 0.7,
        }

    def get_propagation_rules(self) -> PropagationRules:
        return PropagationRules(
            share_scope="all_followers",
            repost_amplification=1.5,
            comment_visibility="threaded",
            viral_threshold=0.10,
            echo_chamber_factor=1.2,
        )
