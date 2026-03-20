"""Structured experiment results tracking with JSONL persistence.

Provides a queryable log of experiment outcomes. Each result captures the
experiment ID, commit hash, metric value, status, and timestamp. The tracker
supports filtering by status, finding the best result, and generating
summary statistics.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ExperimentResult:
    """A single experiment result record.

    Attributes:
        experiment_id: Sequential experiment number.
        commit_hash: Git short hash if kept (or None if reverted/crashed).
        metric_name: Name of the tracked metric (e.g., ``"rmse"``).
        metric_value: Observed metric value (or None if crashed).
        status: Outcome -- ``"keep"``, ``"revert"``, or ``"crash"``.
        description: Human-readable description of the experiment.
        timestamp: UTC ISO timestamp string.
    """

    experiment_id: int
    commit_hash: str | None
    metric_name: str
    metric_value: float | None
    status: str  # "keep" | "revert" | "crash"
    description: str
    timestamp: str


class ResultsTracker:
    """Manages a list of experiment results with JSONL persistence.

    Args:
        path: Path to the JSONL file for persistence.

    Usage::

        tracker = ResultsTracker(Path("results.jsonl"))
        tracker.add(ExperimentResult(...))
        best = tracker.get_best(direction="minimize")
        summary = tracker.summary()
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._results: list[ExperimentResult] = []
        if path.exists():
            self._load_from_disk()

    @property
    def results(self) -> list[ExperimentResult]:
        """Return the list of tracked experiment results."""
        return list(self._results)

    def add(self, result: ExperimentResult) -> None:
        """Append a result to the tracker and persist to JSONL.

        Args:
            result: The experiment result to add.
        """
        self._results.append(result)
        with open(self._path, "a") as f:
            f.write(json.dumps(asdict(result)) + "\n")

    @classmethod
    def load(cls, path: Path) -> ResultsTracker:
        """Create a tracker from an existing JSONL file.

        Args:
            path: Path to the JSONL file.

        Returns:
            A new ResultsTracker populated with the file contents.
        """
        return cls(path)

    def get_best(self, direction: str = "maximize") -> ExperimentResult | None:
        """Return the result with the best metric value.

        Args:
            direction: ``"maximize"`` for highest or ``"minimize"`` for lowest.

        Returns:
            The best ExperimentResult, or None if no results have metrics.
        """
        candidates = [r for r in self._results if r.metric_value is not None]
        if not candidates:
            return None
        if direction == "minimize":
            return min(candidates, key=lambda r: r.metric_value)  # type: ignore[arg-type]
        return max(candidates, key=lambda r: r.metric_value)  # type: ignore[arg-type]

    def get_by_status(self, status: str) -> list[ExperimentResult]:
        """Return results filtered by status.

        Args:
            status: The status to filter by (e.g., ``"keep"``, ``"revert"``).

        Returns:
            List of matching ExperimentResults. Empty list if none match.
        """
        return [r for r in self._results if r.status == status]

    def summary(self) -> dict:
        """Generate summary statistics for all tracked experiments.

        Returns:
            Dict with keys: total_experiments, keeps, reverts, crashes,
            best_metric, best_commit.
        """
        best = self.get_best()
        return {
            "total_experiments": len(self._results),
            "keeps": len(self.get_by_status("keep")),
            "reverts": len(self.get_by_status("revert")),
            "crashes": len(self.get_by_status("crash")),
            "best_metric": best.metric_value if best else None,
            "best_commit": best.commit_hash if best else None,
        }

    def _load_from_disk(self) -> None:
        """Load results from the JSONL file on disk."""
        for line in self._path.read_text().splitlines():
            stripped = line.strip()
            if stripped:
                data = json.loads(stripped)
                self._results.append(ExperimentResult(**data))
