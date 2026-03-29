"""Compare simulated cascades with real-world data.
SPEC: docs/spec/10_VALIDATION_SPEC.md
"""
import math
from dataclasses import dataclass

from .twitter_dataset import CascadeTree, ValidationMetrics


@dataclass
class SimulatedCascade:
    """Cascade data extracted from a Prophet simulation run."""
    cascade_id: str
    scale: int          # total agents who adopted/shared
    depth: int          # max propagation depth
    max_breadth: int    # max breadth at any step


class CascadeComparator:
    """Compare simulated vs real cascade metrics using NRMSE.

    SPEC: docs/spec/10_VALIDATION_SPEC.md
    """

    @staticmethod
    def nrmse(predicted: list[float], actual: list[float]) -> float:
        """Normalized Root Mean Square Error.
        NRMSE = RMSE / (max - min of actual)
        """
        if not predicted or not actual or len(predicted) != len(actual):
            return float('inf')

        n = len(predicted)
        mse = sum((p - a) ** 2 for p, a in zip(predicted, actual)) / n
        rmse = math.sqrt(mse)

        actual_range = max(actual) - min(actual)
        if actual_range == 0:
            return 0.0 if rmse == 0 else float('inf')

        return rmse / actual_range

    def compare(
        self,
        simulated: list[SimulatedCascade],
        real: list[CascadeTree],
    ) -> ValidationMetrics:
        """Compare simulated cascades against real dataset.

        Matches by index (first N simulated vs first N real).
        """
        n = min(len(simulated), len(real))
        if n == 0:
            return ValidationMetrics(
                scale_nrmse=float('inf'),
                depth_nrmse=float('inf'),
                max_breadth_nrmse=float('inf'),
                overall_nrmse=float('inf'),
                sample_count=0,
            )

        sim_scales = [float(s.scale) for s in simulated[:n]]
        real_scales = [float(r.scale) for r in real[:n]]
        sim_depths = [float(s.depth) for s in simulated[:n]]
        real_depths = [float(r.depth) for r in real[:n]]
        sim_breadths = [float(s.max_breadth) for s in simulated[:n]]
        real_breadths = [float(r.max_breadth) for r in real[:n]]

        scale_nrmse = self.nrmse(sim_scales, real_scales)
        depth_nrmse = self.nrmse(sim_depths, real_depths)
        breadth_nrmse = self.nrmse(sim_breadths, real_breadths)

        overall = (scale_nrmse + depth_nrmse + breadth_nrmse) / 3

        # Category breakdown
        categories: dict[str, list[tuple[SimulatedCascade, CascadeTree]]] = {}
        for s, r in zip(simulated[:n], real[:n]):
            categories.setdefault(r.category, []).append((s, r))

        category_breakdown: dict[str, dict[str, float]] = {}
        for cat, pairs in categories.items():
            cat_sim_scales = [float(s.scale) for s, _ in pairs]
            cat_real_scales = [float(r.scale) for _, r in pairs]
            category_breakdown[cat] = {
                "scale_nrmse": round(self.nrmse(cat_sim_scales, cat_real_scales), 4),
                "count": len(pairs),
            }

        return ValidationMetrics(
            scale_nrmse=round(scale_nrmse, 4),
            depth_nrmse=round(depth_nrmse, 4),
            max_breadth_nrmse=round(breadth_nrmse, 4),
            overall_nrmse=round(overall, 4),
            sample_count=n,
            category_breakdown=category_breakdown,
        )
