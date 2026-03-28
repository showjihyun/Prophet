"""Thin wrapper delegating to AgentEngine CognitionLayer for the diffusion pipeline.
SPEC: docs/spec/03_DIFFUSION_SPEC.md#diffusion-pipeline
"""
from app.engine.agent.cognition import CognitionLayer, CognitionResult

__all__ = ["CognitionLayer", "CognitionResult"]
