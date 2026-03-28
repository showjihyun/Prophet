"""Network generation module.
SPEC: docs/spec/02_NETWORK_SPEC.md
"""
from app.engine.network.community_graph import CommunityGraphBuilder
from app.engine.network.evolution import NetworkEvolver
from app.engine.network.generator import InfluenceScorer, NetworkGenerator
from app.engine.network.influencer_layer import InfluencerLayerBuilder
from app.engine.network.schema import (
    CommunityConfig,
    EvolutionConfig,
    NetworkConfig,
    NetworkMetrics,
    SocialNetwork,
)

__all__ = [
    "CommunityConfig",
    "CommunityGraphBuilder",
    "EvolutionConfig",
    "InfluenceScorer",
    "InfluencerLayerBuilder",
    "NetworkConfig",
    "NetworkEvolver",
    "NetworkGenerator",
    "NetworkMetrics",
    "SocialNetwork",
]
