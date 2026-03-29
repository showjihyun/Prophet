"""Platform Plugin base classes.
SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from app.engine.diffusion.schema import RecSysConfig


@dataclass
class PropagationRules:
    """Platform-specific propagation parameters.

    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#2-platform-plugin-architecture
    """
    share_scope: Literal["all_followers", "top_k", "algorithmic"] = "all_followers"
    repost_amplification: float = 1.0
    comment_visibility: Literal["threaded", "flat", "ranked"] = "threaded"
    viral_threshold: float = 0.15
    echo_chamber_factor: float = 1.0


class PlatformPlugin(ABC):
    """Abstract base for SNS platform simulation plugins.

    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md#2-platform-plugin-architecture
    """
    name: str
    display_name: str
    supported_actions: list[str]

    @abstractmethod
    def get_feed_config(self) -> RecSysConfig:
        """Returns platform-specific RecSys weights."""
        ...

    @abstractmethod
    def get_action_weights(self) -> dict[str, float]:
        """Returns platform-specific action weight overrides."""
        ...

    @abstractmethod
    def get_propagation_rules(self) -> PropagationRules:
        """Returns platform-specific propagation behavior."""
        ...
