"""Default Prophet platform plugin.
SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#3-built-in-platform-plugins
"""
from app.engine.diffusion.schema import RecSysConfig
from app.engine.platform.base import PlatformPlugin, PropagationRules


class DefaultPlugin(PlatformPlugin):
    """Prophet generic platform — uses default RecSysConfig weights.

    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#default-prophet-generic
    """
    name = "default"
    display_name = "Prophet (Generic)"
    supported_actions = [
        "ignore", "view", "search",
        "like", "save", "comment", "share", "repost",
        "follow", "unfollow",
        "adopt",
        "mute",
    ]

    def get_feed_config(self) -> RecSysConfig:
        return RecSysConfig()

    def get_action_weights(self) -> dict[str, float]:
        return {
            "like": 0.5,
            "comment": 0.5,
            "share": 0.5,
            "repost": 0.5,
            "save": 0.3,
        }

    def get_propagation_rules(self) -> PropagationRules:
        return PropagationRules()
