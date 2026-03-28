"""Layer 3: Emotion — re-exports from emotion.py for backward compatibility.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-3-emotionlayer
"""
from app.engine.agent.emotion import EmotionLayer

__all__ = ["EmotionLayer"]
