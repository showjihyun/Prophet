"""Bounded Confidence Opinion Dynamics (Deffuant model).

SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§2
"""


class OpinionDynamicsModel:
    """Deffuant bounded confidence opinion dynamics.

    SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§2

    Agents only update their beliefs when a neighbor's opinion falls within
    the confidence threshold epsilon. This prevents unrealistic uniform consensus
    and produces realistic opinion polarisation/clustering.

    Formula:
        delta = |agent_belief - neighbor_belief|
        if delta >= epsilon: no update
        else: new_belief = agent_belief + mu * edge_weight * (neighbor_belief - agent_belief)

    Constants:
        epsilon (float): confidence bound — max tolerable opinion gap [0.0, 2.0]
        mu (float): convergence rate [0.0, 1.0]
    """

    def __init__(self, epsilon: float = 0.3, mu: float = 0.5) -> None:
        """SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§2 BC-02"""
        self._epsilon = epsilon
        self._mu = mu

    def update_belief(
        self,
        agent_belief: float,
        neighbor_belief: float,
        edge_weight: float = 1.0,
        stubbornness: float = 0.0,
    ) -> float:
        """Apply Deffuant bounded confidence update with stubbornness.

        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§2 BC-01/BC-02
        SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#2.1 — Friedkin extension

        Args:
            stubbornness: Agent resistance to opinion change [0.0, 1.0].
                          0.0 = fully open, 1.0 = immovable.
                          Derived from personality.skepticism in practice.

        Returns the new agent belief, unchanged if |delta| >= epsilon.
        Result is clamped to [-1.0, 1.0].

        Determinism: Pure function. No RNG. BC-05.
        Side Effects: None.
        """
        delta = abs(agent_belief - neighbor_belief)
        if delta >= self._epsilon:
            return agent_belief
        effective_mu = self._mu * (1.0 - stubbornness)
        shift = effective_mu * edge_weight * (neighbor_belief - agent_belief)
        new_belief = agent_belief + shift
        return max(-1.0, min(1.0, new_belief))

    def batch_update(
        self,
        agent_belief: float,
        neighbor_beliefs: list[tuple[float, float]],
        stubbornness: float = 0.0,
    ) -> float:
        """Apply Deffuant update from multiple neighbors sequentially.

        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#§2 BC-03
        SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#2.1 — Friedkin extension

        Processes neighbors in belief-proximity order (closest first).
        Returns final belief after all within-bound neighbors are applied.

        Args:
            neighbor_beliefs: list of (belief, edge_weight) tuples.
            stubbornness: Agent resistance to opinion change [0.0, 1.0].
        """
        # Sort by proximity: closest beliefs first (BC-AC-05)
        sorted_neighbors = sorted(
            neighbor_beliefs,
            key=lambda nb: abs(agent_belief - nb[0]),
        )
        current = agent_belief
        for neighbor_belief, edge_weight in sorted_neighbors:
            current = self.update_belief(current, neighbor_belief, edge_weight, stubbornness)
        return current


__all__ = ["OpinionDynamicsModel"]
