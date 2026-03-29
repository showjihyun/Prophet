# 12 — Platform & RecSys Plugin SPEC
Version: 0.1.0 | Status: DRAFT

---

## 1. Overview

Prophet supports pluggable SNS platform simulation and recommendation system algorithms.
Users can select which platform behavior to simulate (Twitter, Reddit, Instagram, Custom)
and which RecSys algorithm to use, from the Settings page or simulation config.

This enables:
- Platform-specific content exposure patterns (Twitter timeline vs Reddit hot score)
- Pluggable RecSys algorithms (swap without changing core engine)
- Custom platform definitions (user-defined action weights and feed rules)

---

## 2. Platform Plugin Architecture

```python
class PlatformPlugin(ABC):
    """Abstract base for SNS platform simulation plugins.
    SPEC: docs/spec/platform/12_PLATFORM_PLUGIN_SPEC.md
    """
    name: str                    # "twitter", "reddit", "instagram", "custom"
    display_name: str            # "Twitter/X", "Reddit", "Instagram"
    supported_actions: list[str] # subset of 12 AgentActions relevant to this platform

    @abstractmethod
    def get_feed_config(self) -> RecSysConfig:
        """Returns platform-specific RecSys weights."""

    @abstractmethod
    def get_action_weights(self) -> dict[str, float]:
        """Returns platform-specific action weight overrides."""

    @abstractmethod
    def get_propagation_rules(self) -> PropagationRules:
        """Returns platform-specific propagation behavior."""


@dataclass
class PropagationRules:
    """Platform-specific propagation parameters."""
    share_scope: Literal["all_followers", "top_k", "algorithmic"] = "all_followers"
    repost_amplification: float = 1.0     # repost reach multiplier
    comment_visibility: Literal["threaded", "flat", "ranked"] = "threaded"
    viral_threshold: float = 0.15         # cascade detection threshold
    echo_chamber_factor: float = 1.0      # intra-community boost (>1 = stronger bubbles)
```

---

## 3. Built-in Platform Plugins

### Twitter/X Plugin

```python
class TwitterPlugin(PlatformPlugin):
    name = "twitter"
    display_name = "Twitter/X"
    supported_actions = [
        "ignore", "view", "like", "comment", "share", "repost",
        "follow", "unfollow", "mute", "search"
    ]

    def get_feed_config(self) -> RecSysConfig:
        return RecSysConfig(
            feed_capacity=30,
            w_recency=0.15,
            w_social_affinity=0.35,    # in-network bias (TwHIN-style)
            w_interest_match=0.25,
            w_engagement_signal=0.20,
            w_ad_boost=0.05,
            enable_filter_bubble=True,
            diversity_penalty=0.03,
        )

    def get_action_weights(self) -> dict[str, float]:
        return {
            "repost": 0.85,     # retweet is dominant on Twitter
            "like": 0.4,
            "comment": 0.5,     # reply
            "share": 0.7,       # quote tweet
        }

    def get_propagation_rules(self) -> PropagationRules:
        return PropagationRules(
            share_scope="all_followers",
            repost_amplification=1.5,   # retweets amplify strongly
            comment_visibility="threaded",
            viral_threshold=0.10,       # Twitter virals fast
            echo_chamber_factor=1.2,
        )
```

### Reddit Plugin

```python
class RedditPlugin(PlatformPlugin):
    name = "reddit"
    display_name = "Reddit"
    supported_actions = [
        "ignore", "view", "like", "comment", "share",
        "save", "search"
    ]
    # No follow/unfollow (subreddit-based, not user-based)

    def get_feed_config(self) -> RecSysConfig:
        # Reddit Hot Score: h = log10(max(|u-d|, 1)) + sign(u-d) * (t-t0) / 45000
        return RecSysConfig(
            feed_capacity=25,
            w_recency=0.30,            # Reddit is very time-sensitive
            w_social_affinity=0.10,    # weak user-to-user (community-based)
            w_interest_match=0.15,
            w_engagement_signal=0.40,  # upvotes dominate ranking
            w_ad_boost=0.05,
            enable_filter_bubble=False, # subreddits are open
            diversity_penalty=0.10,
        )

    def get_propagation_rules(self) -> PropagationRules:
        return PropagationRules(
            share_scope="algorithmic",  # Reddit shows by algorithm, not followers
            repost_amplification=0.5,   # cross-posting is weak on Reddit
            comment_visibility="ranked", # top comments rise
            viral_threshold=0.20,
            echo_chamber_factor=1.5,    # subreddits are strong echo chambers
        )
```

### Instagram Plugin

```python
class InstagramPlugin(PlatformPlugin):
    name = "instagram"
    display_name = "Instagram"
    supported_actions = [
        "ignore", "view", "like", "comment", "share",
        "save", "follow", "unfollow", "mute"
    ]

    def get_feed_config(self) -> RecSysConfig:
        return RecSysConfig(
            feed_capacity=20,
            w_recency=0.20,
            w_social_affinity=0.40,    # Instagram is very relationship-driven
            w_interest_match=0.20,
            w_engagement_signal=0.15,
            w_ad_boost=0.05,
            enable_filter_bubble=True,
            diversity_penalty=0.05,
        )

    def get_propagation_rules(self) -> PropagationRules:
        return PropagationRules(
            share_scope="top_k",        # DM sharing, not public repost
            repost_amplification=0.3,   # no native repost
            comment_visibility="flat",
            viral_threshold=0.12,
            echo_chamber_factor=1.3,
        )
```

### Default (Prophet Generic)

```python
class DefaultPlugin(PlatformPlugin):
    name = "default"
    display_name = "Prophet (Generic)"
    supported_actions = [...]  # all 12
    # Uses existing RecSysConfig defaults
```

---

## 4. RecSys Algorithm Plugin

```python
class RecSysAlgorithm(ABC):
    """Pluggable recommendation algorithm."""
    name: str

    @abstractmethod
    def rank_feed(
        self,
        agent: AgentState,
        candidates: list[FeedItem],
        social_graph: nx.Graph,
    ) -> list[FeedItem]:
        """Rank and filter candidates for this agent's feed."""


class WeightedRecSys(RecSysAlgorithm):
    """Current Prophet default: weighted 5-factor formula."""
    name = "weighted"

class HotScoreRecSys(RecSysAlgorithm):
    """Reddit-style hot score ranking."""
    name = "hot_score"
    # h = log10(max(|u-d|, 1)) + sign(u-d) * (t-t0) / 45000

class EmbeddingRecSys(RecSysAlgorithm):
    """Embedding similarity-based (sentence-transformers or TwHIN-BERT style)."""
    name = "embedding"
    # Uses sentence-transformers for content similarity
```

---

## 5. Plugin Registry

```python
class PlatformRegistry:
    _platforms: dict[str, PlatformPlugin] = {}
    _recsys: dict[str, RecSysAlgorithm] = {}

    def register_platform(self, plugin: PlatformPlugin) -> None: ...
    def get_platform(self, name: str) -> PlatformPlugin: ...
    def list_platforms(self) -> list[str]: ...

    def register_recsys(self, algo: RecSysAlgorithm) -> None: ...
    def get_recsys(self, name: str) -> RecSysAlgorithm: ...
    def list_recsys(self) -> list[str]: ...
```

---

## 6. Settings Integration

### API Endpoints

```
GET  /api/v1/settings/platforms     → list available platform plugins
GET  /api/v1/settings/recsys       → list available RecSys algorithms
PUT  /api/v1/settings              → { "platform": "twitter", "recsys": "hot_score" }
```

### SimulationConfig Extension

```python
@dataclass
class SimulationConfig:
    ...
    platform: str = "default"           # "twitter" | "reddit" | "instagram" | "default"
    recsys_algorithm: str = "weighted"  # "weighted" | "hot_score" | "embedding"
```

### Settings Page (UI)

```
┌─── Platform Configuration ─────────────────────┐
│ Platform: [Twitter/X ▼]                        │
│                                                 │
│ Feed capacity: 30    Filter bubble: ✓           │
│ Viral threshold: 0.10                           │
│ Echo chamber factor: 1.2                        │
│                                                 │
│ RecSys Algorithm: [Hot Score ▼]                 │
│ Available: Weighted | Hot Score | Embedding      │
└─────────────────────────────────────────────────┘
```

---

## 7. Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| PLT-01 | Register and retrieve Twitter plugin | Plugin returned with correct feed config |
| PLT-02 | Register and retrieve Reddit plugin | Different RecSys weights than Twitter |
| PLT-03 | SimulationConfig.platform changes feed ranking | Twitter vs Reddit produce different exposure patterns |
| PLT-04 | RecSys algorithm swap at runtime | Hot score vs weighted produce different rankings |
| PLT-05 | Settings API lists all platforms | Returns ["default", "twitter", "reddit", "instagram"] |
| PLT-06 | Unknown platform name raises error | ValueError for "tiktok" |
