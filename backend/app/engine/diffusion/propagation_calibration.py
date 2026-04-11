"""Shared propagation-probability formula.

SPEC: docs/spec/26_DIFFUSION_CALIBRATION_SPEC.md (Round 7-d / 8-3)

The same probability calculation was previously duplicated between
:mod:`app.engine.agent.influence` (the layer the agent tick uses) and
:mod:`app.engine.diffusion.propagation_model` (the newer model). The first
time the calibration was updated, only one copy was touched, and the other
silently regressed — agents with low centrality stopped propagating entirely
because the forgotten copy lacked the ``max(0.1, influence_score)`` floor.

Every Round-X calibration tweak belongs in this single module so both
callers stay in lock-step.
"""
from __future__ import annotations

import math

__all__ = ["propagation_probability", "INFLUENCE_FLOOR"]

#: Minimum effective influence for probability computation.
#:
#: Typical Prophet agents derive influence from (blended) centrality on
#: small graphs: values cluster around 0.04–0.1. Without a floor, the
#: ``influence * trust * emotion * ms_score`` product collapses to ~0 and
#: no propagation events fire across a whole step. The floor guarantees
#: low-centrality agents still occasionally share.
INFLUENCE_FLOOR: float = 0.1


def propagation_probability(
    *,
    influence_score: float,
    trust: float,
    emotion_factor: float,
    message_strength: float,
) -> float:
    """Compute P(i → j) for a single target neighbour.

    SPEC: docs/spec/26_DIFFUSION_CALIBRATION_SPEC.md

    The formula is::

        influence = max(INFLUENCE_FLOOR, influence_score)
        smoothed  = 0.01 + 0.99 / (1 + exp(-4 · emotion_factor))
        p         = influence · trust · smoothed · message_strength

    Design notes:

    * **Sigmoid-smoothed emotion** replaces the earlier ``max(emotion_factor, 0)``
      gate. With the gate, any agent whose excitement barely equalled their
      skepticism produced probability zero; with the sigmoid, ``emotion_factor == 0``
      yields ~0.5 and slightly-negative emotion still contributes a small weight.
    * **Influence floor** compensates for the fact that
      :func:`networkx.degree_centrality` on small (80-1000 node) graphs returns
      values in the 0.03–0.15 range. Without the floor, the probability product
      collapses to ~0 and no propagation events fire.
    * The result is **not** clamped here — that remains the caller's job
      (SHARE vs ADOPT has different post-processing, e.g. ``p *= 0.5`` for ADOPT).

    All arguments are keyword-only to prevent positional call sites from
    drifting when we add a new calibration knob.
    """
    influence = max(INFLUENCE_FLOOR, influence_score)
    smoothed = 0.01 + 0.99 / (1.0 + math.exp(-4.0 * emotion_factor))
    return influence * trust * smoothed * message_strength
