"""Layer 4: Cognition — re-exports from cognition.py for backward compatibility.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-4-cognitionlayer
"""
from app.engine.agent.cognition import CognitionLayer, CognitionResult

__all__ = ["CognitionLayer", "CognitionResult"]
