"""Shared data types across engine modules — re-export convenience module.
SPEC: docs/spec/01_AGENT_SPEC.md, 02_NETWORK_SPEC.md, 03_DIFFUSION_SPEC.md

All types are defined in their canonical modules and re-exported here.
Prefer importing from the canonical location in production code.
"""

# Canonical: app.engine.agent.schema
from app.engine.agent.schema import AgentAction, AgentPersonality, AgentEmotion  # noqa: F401

# Canonical: app.engine.simulation.schema
from app.engine.simulation.schema import SimulationStatus  # noqa: F401

# Canonical: app.engine.agent.influence
from app.engine.agent.influence import MessageStrength, ContextualPacket  # noqa: F401
