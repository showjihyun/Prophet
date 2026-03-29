"""Reddit platform plugin.
SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#3-built-in-platform-plugins
"""
from app.engine.diffusion.schema import RecSysConfig
from app.engine.platform.base import PlatformPlugin, PropagationRules


class RedditPlugin(PlatformPlugin):
    """Reddit simulation plugin.

    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#reddit-plugin
    """
    name = "reddit"
    display_name = "Reddit"
    supported_actions = [
        "ignore", "view", "like", "comment", "share",
        "save", "search",
    ]

    def get_feed_config(self) -> RecSysConfig:
        return RecSysConfig(
            feed_capacity=25,
            w_recency=0.30,
            w_social_affinity=0.10,
            w_interest_match=0.15,
            w_engagement_signal=0.40,
            w_ad_boost=0.05,
            enable_filter_bubble=False,
            diversity_penalty=0.10,
        )

    def get_action_weights(self) -> dict[str, float]:
        return {
            "like": 0.6,
            "comment": 0.7,
            "share": 0.3,
        }

    def get_propagation_rules(self) -> PropagationRules:
        return PropagationRules(
            share_scope="algorithmic",
            repost_amplification=0.5,
            comment_visibility="ranked",
            viral_threshold=0.20,
            echo_chamber_factor=1.5,
        )
