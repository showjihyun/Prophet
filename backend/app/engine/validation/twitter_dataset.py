"""Twitter15/16 validation dataset loader and comparator.
SPEC: docs/spec/platform/13_SCALE_VALIDATION_SPEC.md#validation
SPEC: docs/spec/10_VALIDATION_SPEC.md

Assumes Twitter15/16 dataset is available at a configured path.
Dataset format: JSON lines with cascade trees.
"""
from dataclasses import dataclass, field
from pathlib import Path
import json
import math


@dataclass
class CascadeTree:
    """A single real-world cascade from Twitter15/16 dataset."""
    root_id: str
    category: str           # e.g., "non-rumor", "false", "true", "unverified"
    scale: int              # total participants
    depth: int              # max propagation depth
    max_breadth: int        # max breadth at any level
    timestamps: list[float] # relative timestamps of each node
    edges: list[tuple[str, str]]  # (parent, child) pairs


@dataclass
class ValidationMetrics:
    """NRMSE comparison between simulated and real cascades."""
    scale_nrmse: float      # normalized RMSE for cascade scale
    depth_nrmse: float      # normalized RMSE for cascade depth
    max_breadth_nrmse: float  # normalized RMSE for max breadth
    overall_nrmse: float    # weighted average
    sample_count: int
    category_breakdown: dict[str, dict[str, float]] = field(default_factory=dict)


class TwitterDatasetLoader:
    """Loads Twitter15/16 cascade data for validation.

    SPEC: docs/spec/10_VALIDATION_SPEC.md

    Expected directory structure:
        data_dir/
        ├── twitter15/
        │   ├── tree/          # cascade tree files
        │   └── label.txt      # category labels
        └── twitter16/
            ├── tree/
            └── label.txt
    """

    def __init__(self, data_dir: str = "./data/twitter_datasets"):
        self._data_dir = Path(data_dir)

    def load(self, dataset: str = "twitter15") -> list[CascadeTree]:
        """Load cascade trees from dataset.

        Args:
            dataset: "twitter15" or "twitter16"

        Returns:
            List of CascadeTree objects

        Raises:
            FileNotFoundError: if dataset directory doesn't exist
        """
        ds_dir = self._data_dir / dataset
        if not ds_dir.exists():
            raise FileNotFoundError(
                f"Dataset not found at {ds_dir}. "
                f"Download Twitter15/16 dataset and place in {self._data_dir}"
            )

        labels = self._load_labels(ds_dir / "label.txt")
        trees = []
        tree_dir = ds_dir / "tree"

        for tree_file in sorted(tree_dir.glob("*.txt")):
            root_id = tree_file.stem
            category = labels.get(root_id, "unknown")
            edges, timestamps = self._parse_tree(tree_file)

            if not edges:
                continue

            depth = self._compute_depth(edges)
            breadth = self._compute_max_breadth(edges)

            trees.append(CascadeTree(
                root_id=root_id,
                category=category,
                scale=len(set(n for e in edges for n in e)),
                depth=depth,
                max_breadth=breadth,
                timestamps=timestamps,
                edges=edges,
            ))

        return trees

    def _load_labels(self, path: Path) -> dict[str, str]:
        labels: dict[str, str] = {}
        if not path.exists():
            return labels
        for line in path.read_text().strip().split("\n"):
            parts = line.strip().split(":")
            if len(parts) == 2:
                labels[parts[0].strip()] = parts[1].strip()
        return labels

    def _parse_tree(self, path: Path) -> tuple[list[tuple[str, str]], list[float]]:
        edges: list[tuple[str, str]] = []
        timestamps: list[float] = []
        for line in path.read_text().strip().split("\n"):
            parts = line.strip().split("->")
            if len(parts) != 2:
                continue
            parent_info, child_info = parts
            parent_id = parent_info.strip().split(",")[0].strip("'\" ")
            child_parts = child_info.strip().split(",")
            child_id = child_parts[0].strip("'\" ")
            ts = float(child_parts[1].strip()) if len(child_parts) > 1 else 0.0
            edges.append((parent_id, child_id))
            timestamps.append(ts)
        return edges, timestamps

    def _compute_depth(self, edges: list[tuple[str, str]]) -> int:
        if not edges:
            return 0
        children: dict[str, list[str]] = {}
        all_children: set[str] = set()
        for parent, child in edges:
            children.setdefault(parent, []).append(child)
            all_children.add(child)
        roots = [e[0] for e in edges if e[0] not in all_children]
        if not roots:
            return 0

        max_depth = 0
        stack = [(roots[0], 0)]
        visited: set[str] = set()
        while stack:
            node, d = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            max_depth = max(max_depth, d)
            for child in children.get(node, []):
                stack.append((child, d + 1))
        return max_depth

    def _compute_max_breadth(self, edges: list[tuple[str, str]]) -> int:
        if not edges:
            return 0
        children: dict[str, list[str]] = {}
        all_children: set[str] = set()
        for parent, child in edges:
            children.setdefault(parent, []).append(child)
            all_children.add(child)
        roots = [e[0] for e in edges if e[0] not in all_children]
        if not roots:
            return 1

        max_breadth = 1
        level = [roots[0]]
        visited = {roots[0]}
        while level:
            next_level = []
            for node in level:
                for child in children.get(node, []):
                    if child not in visited:
                        visited.add(child)
                        next_level.append(child)
            if next_level:
                max_breadth = max(max_breadth, len(next_level))
            level = next_level
        return max_breadth
