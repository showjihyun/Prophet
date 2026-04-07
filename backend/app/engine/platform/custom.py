"""Custom (user-defined) platform plugin.
SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#4-custom-platform-plugin
"""
from __future__ import annotations

from app.engine.diffusion.schema import RecSysConfig
from app.engine.platform.base import PlatformPlugin, PropagationRules

_DEFAULT_ACTIONS = [
    "ignore", "view", "search",
    "like", "save", "comment", "share", "repost",
    "follow", "unfollow",
    "adopt",
    "mute",
]

_DEFAULT_ACTION_WEIGHTS: dict[str, float] = {
    "like": 0.5,
    "comment": 0.5,
    "share": 0.5,
    "repost": 0.5,
    "save": 0.3,
}


class CustomPlatform(PlatformPlugin):
    """User-defined platform with configurable action weights and feed rules.

    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#4-custom-platform-plugin

    Config dict keys (all optional):
    - ``display_name`` (str): Human-readable platform name shown in the UI.
    - ``supported_actions`` (list[str]): Which action types are available.
    - ``action_weights`` (dict[str, float]): Per-action weight overrides
      (values used directly by the diffusion engine).
    - ``feed_config`` (dict): RecSysConfig field overrides.  The dict may
      contain any subset of the RecSysConfig fields:
      ``feed_capacity``, ``w_recency``, ``w_social_affinity``,
      ``w_interest_match``, ``w_engagement_signal``, ``w_ad_boost``,
      ``enable_filter_bubble``, ``diversity_penalty``.
    - ``propagation`` (dict): PropagationRules field overrides.
    """

    name = "custom"
    display_name = "Custom Platform"

    def __init__(self, config: dict | None = None) -> None:
        cfg = config or {}

        # display_name override
        if "display_name" in cfg:
            self.display_name = str(cfg["display_name"])

        # supported_actions override
        if "supported_actions" in cfg:
            self.supported_actions = list(cfg["supported_actions"])
        else:
            self.supported_actions = list(_DEFAULT_ACTIONS)

        # action_weights override
        self._action_weights: dict[str, float] = dict(_DEFAULT_ACTION_WEIGHTS)
        if "action_weights" in cfg:
            self._action_weights.update(cfg["action_weights"])

        # feed_config override — build RecSysConfig from default, then patch
        feed_overrides: dict = cfg.get("feed_config", {})
        default_feed = RecSysConfig()
        self._feed_config = RecSysConfig(
            feed_capacity=int(
                feed_overrides.get("feed_capacity", default_feed.feed_capacity)
            ),
            w_recency=float(
                feed_overrides.get("w_recency", default_feed.w_recency)
            ),
            w_social_affinity=float(
                feed_overrides.get("w_social_affinity", default_feed.w_social_affinity)
            ),
            w_interest_match=float(
                feed_overrides.get("w_interest_match", default_feed.w_interest_match)
            ),
            w_engagement_signal=float(
                feed_overrides.get("w_engagement_signal", default_feed.w_engagement_signal)
            ),
            w_ad_boost=float(
                feed_overrides.get("w_ad_boost", default_feed.w_ad_boost)
            ),
            enable_filter_bubble=bool(
                feed_overrides.get("enable_filter_bubble", default_feed.enable_filter_bubble)
            ),
            diversity_penalty=float(
                feed_overrides.get("diversity_penalty", default_feed.diversity_penalty)
            ),
        )

        # propagation rules override
        prop_overrides: dict = cfg.get("propagation", {})
        default_prop = PropagationRules()
        self._propagation_rules = PropagationRules(
            share_scope=prop_overrides.get("share_scope", default_prop.share_scope),
            repost_amplification=float(
                prop_overrides.get("repost_amplification", default_prop.repost_amplification)
            ),
            comment_visibility=prop_overrides.get(
                "comment_visibility", default_prop.comment_visibility
            ),
            viral_threshold=float(
                prop_overrides.get("viral_threshold", default_prop.viral_threshold)
            ),
            echo_chamber_factor=float(
                prop_overrides.get("echo_chamber_factor", default_prop.echo_chamber_factor)
            ),
        )

    # ------------------------------------------------------------------
    # PlatformPlugin interface
    # ------------------------------------------------------------------

    def get_feed_config(self) -> RecSysConfig:
        """Returns the user-configured RecSys weights.
        SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#4-custom-platform-plugin
        """
        return self._feed_config

    def get_action_weights(self) -> dict[str, float]:
        """Returns the user-configured action weight overrides.
        SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#4-custom-platform-plugin
        """
        return dict(self._action_weights)

    def get_propagation_rules(self) -> PropagationRules:
        """Returns the user-configured propagation behavior.
        SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#4-custom-platform-plugin
        """
        return self._propagation_rules

    # ------------------------------------------------------------------
    # Convenience: recreate from a new config dict (returns new instance)
    # ------------------------------------------------------------------

    def reconfigure(self, config: dict) -> "CustomPlatform":
        """Return a new CustomPlatform instance with the given config applied."""
        return CustomPlatform(config)
