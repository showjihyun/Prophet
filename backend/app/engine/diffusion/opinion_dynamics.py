"""Bounded Confidence Opinion Dynamics (Deffuant model).

SPEC: docs/spec/20_SIMULATION_QUALITY_P2_SPEC.md#§2
"""


class OpinionDynamicsModel:
    """Deffuant bounded confidence opinion dynamics.

    SPEC: docs/spec/20_SIMULATION_QUALITY_P2_SPEC.md#§2

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
        """SPEC: docs/spec/20_SIMULATION_QUALITY_P2_SPEC.md#§2 BC-02"""
        self._epsilon = epsilon
        self._mu = mu

    def update_belief(
        self,
        agent_belief: float,
        neighbor_belief: float,
        edge_weight: float = 1.0,
    ) -> float:
        """Apply Deffuant bounded confidence update.

        SPEC: docs/spec/20_SIMULATION_QUALITY_P2_SPEC.md#§2 BC-01/BC-02

        Returns the new agent belief, unchanged if |delta| >= epsilon.
        Result is clamped to [-1.0, 1.0].

        Determinism: Pure function. No RNG. BC-05.
        Side Effects: None.
        """
        delta = abs(agent_belief - neighbor_belief)
        if delta >= self._epsilon:
            return agent_belief
        shift = self._mu * edge_weight * (neighbor_belief - agent_belief)
        new_belief = agent_belief + shift
        return max(-1.0, min(1.0, new_belief))

    def batch_update(
        self,
        agent_belief: float,
        neighbor_beliefs: list[tuple[float, float]],
    ) -> float:
        """Apply Deffuant update from multiple neighbors sequentially.

        SPEC: docs/spec/20_SIMULATION_QUALITY_P2_SPEC.md#§2 BC-03

        Processes neighbors in belief-proximity order (closest first).
        Returns final belief after all within-bound neighbors are applied.

        Args:
            neighbor_beliefs: list of (belief, edge_weight) tuples.
        """
        # Sort by proximity: closest beliefs first (BC-AC-05)
        sorted_neighbors = sorted(
            neighbor_beliefs,
            key=lambda nb: abs(agent_belief - nb[0]),
        )
        current = agent_belief
        for neighbor_belief, edge_weight in sorted_neighbors:
            current = self.update_belief(current, neighbor_belief, edge_weight)
        return current


__all__ = ["OpinionDynamicsModel"]
