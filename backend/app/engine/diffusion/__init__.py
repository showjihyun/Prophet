"""Social Diffusion Engine.
SPEC: docs/spec/03_DIFFUSION_SPEC.md
"""
from app.engine.diffusion.schema import (
    CampaignEvent,
    CascadeConfig,
    CommunitySentiment,
    EmergentEvent,
    ExpertOpinion,
    ExposureResult,
    FeedItem,
    MonteCarloResult,
    NegativeEvent,
    PropagationEvent,
    RecSysConfig,
    RunSummary,
)
from app.engine.diffusion.exposure_model import ExposureModel
from app.engine.diffusion.propagation_model import PropagationModel
from app.engine.diffusion.sentiment_model import SentimentModel
from app.engine.diffusion.cascade_detector import CascadeDetector, StepResult
from app.engine.diffusion.cognition_model import CognitionLayer, CognitionResult

__all__ = [
    # Schema
    "CampaignEvent",
    "CascadeConfig",
    "CommunitySentiment",
    "EmergentEvent",
    "ExpertOpinion",
    "ExposureResult",
    "FeedItem",
    "MonteCarloResult",
    "NegativeEvent",
    "PropagationEvent",
    "RecSysConfig",
    "RunSummary",
    # Models
    "ExposureModel",
    "PropagationModel",
    "SentimentModel",
    "CascadeDetector",
    "StepResult",
    "CognitionLayer",
    "CognitionResult",
]
