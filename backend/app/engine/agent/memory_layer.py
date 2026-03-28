"""Layer 2: Memory — agent memory storage and retrieval.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-2-memorylayer

Re-exports from app.engine.agent.memory for backward compatibility.
"""
from app.engine.agent.memory import MemoryLayer, MemoryRecord, MemoryConfig

__all__ = ["MemoryLayer", "MemoryRecord", "MemoryConfig"]
