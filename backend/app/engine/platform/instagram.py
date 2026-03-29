"""Instagram platform plugin.
SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#3-built-in-platform-plugins
"""
from app.engine.diffusion.schema import RecSysConfig
from app.engine.platform.base import PlatformPlugin, PropagationRules


class InstagramPlugin(PlatformPlugin):
    """Instagram simulation plugin.

    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#instagram-plugin
    """
    name = "instagram"
    display_name = "Instagram"
    supported_actions = [
        "ignore", "view", "like", "comment", "share",
        "save", "follow", "unfollow", "mute",
    ]

    def get_feed_config(self) -> RecSysConfig:
        return RecSysConfig(
            feed_capacity=20,
            w_recency=0.20,
            w_social_affinity=0.40,
            w_interest_match=0.20,
            w_engagement_signal=0.15,
            w_ad_boost=0.05,
            enable_filter_bubble=True,
            diversity_penalty=0.05,
        )

    def get_action_weights(self) -> dict[str, float]:
        return {
            "like": 0.6,
            "comment": 0.4,
            "share": 0.5,
            "save": 0.3,
        }

    def get_propagation_rules(self) -> PropagationRules:
        return PropagationRules(
            share_scope="top_k",
            repost_amplification=0.3,
            comment_visibility="flat",
            viral_threshold=0.12,
            echo_chamber_factor=1.3,
        )
