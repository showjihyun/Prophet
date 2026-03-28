"""Layer 6: Influence — re-exports from influence.py for backward compatibility.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer
"""
from app.engine.agent.influence import (
    InfluenceLayer, MessageStrength, PropagationEvent, ContextualPacket,
)

__all__ = ["InfluenceLayer", "MessageStrength", "PropagationEvent", "ContextualPacket"]
