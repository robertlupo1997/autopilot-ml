"""Tests for mlforge.results — structured experiment results tracking."""

from __future__ import annotations

from pathlib import Path

from mlforge.results import ExperimentResult, ResultsTracker


class TestExperimentResultDataclass:
    """ExperimentResult captures all required fields."""

    def test_experiment_result_dataclass(self):
        """All fields present and typed correctly."""
        result = ExperimentResult(
            experiment_id=1,
            commit_hash="abc1234",
            metric_name="rmse",
            metric_value=0.85,
            status="keep",
            description="Added feature X",
            timestamp="2026-03-20T00:00:00Z",
        )
        assert result.experiment_id == 1
        assert result.commit_hash == "abc1234"
        assert result.metric_name == "rmse"
        assert result.metric_value == 0.85
        assert result.status == "keep"
        assert result.description == "Added feature X"
        assert result.timestamp == "2026-03-20T00:00:00Z"

    def test_experiment_result_none_metric(self):
        """metric_value and commit_hash can be None."""
        result = ExperimentResult(
            experiment_id=2,
            commit_hash=None,
            metric_name="rmse",
            metric_value=None,
            status="crash",
            description="crashed",
            timestamp="2026-03-20T00:00:00Z",
        )
        assert result.metric_value is None
        assert result.commit_hash is None


class TestResultsTrackerAddAndLoad:
    """ResultsTracker persists to JSONL and loads correctly."""

    def test_tracker_add_and_load(self, tmp_dir: Path):
        """Round-trip JSONL persistence."""
        path = tmp_dir / "results.jsonl"
        tracker = ResultsTracker(path)

        r1 = ExperimentResult(1, "abc", "rmse", 0.9, "keep", "exp1", "2026-01-01T00:00:00Z")
        r2 = ExperimentResult(2, "def", "rmse", 0.8, "keep", "exp2", "2026-01-01T01:00:00Z")
        tracker.add(r1)
        tracker.add(r2)

        # Load from disk
        loaded = ResultsTracker.load(path)
        assert len(loaded.results) == 2
        assert loaded.results[0].experiment_id == 1
        assert loaded.results[1].metric_value == 0.8

    def test_tracker_load_nonexistent(self, tmp_dir: Path):
        """Loading from nonexistent file gives empty tracker."""
        path = tmp_dir / "nonexistent.jsonl"
        tracker = ResultsTracker(path)
        assert len(tracker.results) == 0


class TestResultsTrackerGetBest:
    """get_best returns the best result by metric."""

    def test_tracker_get_best_maximize(self, tmp_dir: Path):
        """Returns result with highest metric."""
        path = tmp_dir / "results.jsonl"
        tracker = ResultsTracker(path)
        tracker.add(ExperimentResult(1, "a", "acc", 0.8, "keep", "d1", "t1"))
        tracker.add(ExperimentResult(2, "b", "acc", 0.95, "keep", "d2", "t2"))
        tracker.add(ExperimentResult(3, "c", "acc", 0.9, "keep", "d3", "t3"))

        best = tracker.get_best(direction="maximize")
        assert best is not None
        assert best.experiment_id == 2
        assert best.metric_value == 0.95

    def test_tracker_get_best_minimize(self, tmp_dir: Path):
        """Returns result with lowest metric."""
        path = tmp_dir / "results.jsonl"
        tracker = ResultsTracker(path)
        tracker.add(ExperimentResult(1, "a", "rmse", 0.8, "keep", "d1", "t1"))
        tracker.add(ExperimentResult(2, "b", "rmse", 0.3, "keep", "d2", "t2"))
        tracker.add(ExperimentResult(3, "c", "rmse", 0.5, "keep", "d3", "t3"))

        best = tracker.get_best(direction="minimize")
        assert best is not None
        assert best.experiment_id == 2
        assert best.metric_value == 0.3

    def test_tracker_get_best_empty(self, tmp_dir: Path):
        """Returns None for empty tracker."""
        path = tmp_dir / "results.jsonl"
        tracker = ResultsTracker(path)

        assert tracker.get_best() is None

    def test_tracker_get_best_all_none_metrics(self, tmp_dir: Path):
        """Returns None when all metrics are None."""
        path = tmp_dir / "results.jsonl"
        tracker = ResultsTracker(path)
        tracker.add(ExperimentResult(1, None, "rmse", None, "crash", "d1", "t1"))
        tracker.add(ExperimentResult(2, None, "rmse", None, "crash", "d2", "t2"))

        assert tracker.get_best() is None


class TestResultsTrackerGetByStatus:
    """get_by_status filters results correctly."""

    def test_tracker_get_by_status(self, tmp_dir: Path):
        """Filters correctly by keep/revert/crash."""
        path = tmp_dir / "results.jsonl"
        tracker = ResultsTracker(path)
        tracker.add(ExperimentResult(1, "a", "rmse", 0.8, "keep", "d1", "t1"))
        tracker.add(ExperimentResult(2, "b", "rmse", 0.9, "revert", "d2", "t2"))
        tracker.add(ExperimentResult(3, "c", "rmse", None, "crash", "d3", "t3"))
        tracker.add(ExperimentResult(4, "d", "rmse", 0.7, "keep", "d4", "t4"))

        keeps = tracker.get_by_status("keep")
        assert len(keeps) == 2
        assert all(r.status == "keep" for r in keeps)

        reverts = tracker.get_by_status("revert")
        assert len(reverts) == 1

        crashes = tracker.get_by_status("crash")
        assert len(crashes) == 1

        assert tracker.get_by_status("nonexistent") == []


class TestResultsTrackerSummary:
    """summary() provides complete experiment statistics."""

    def test_tracker_summary(self, tmp_dir: Path):
        """Correct counts and best metric/commit."""
        path = tmp_dir / "results.jsonl"
        tracker = ResultsTracker(path)
        tracker.add(ExperimentResult(1, "abc", "rmse", 0.8, "keep", "d1", "t1"))
        tracker.add(ExperimentResult(2, "def", "rmse", 0.5, "keep", "d2", "t2"))
        tracker.add(ExperimentResult(3, None, "rmse", None, "crash", "d3", "t3"))
        tracker.add(ExperimentResult(4, "ghi", "rmse", 0.9, "revert", "d4", "t4"))

        s = tracker.summary()
        assert s["total_experiments"] == 4
        assert s["keeps"] == 2
        assert s["reverts"] == 1
        assert s["crashes"] == 1
        # Default maximize: best is 0.9
        assert s["best_metric"] == 0.9
        assert s["best_commit"] == "ghi"

    def test_tracker_summary_empty(self, tmp_dir: Path):
        """Handles empty tracker gracefully."""
        path = tmp_dir / "results.jsonl"
        tracker = ResultsTracker(path)

        s = tracker.summary()
        assert s["total_experiments"] == 0
        assert s["keeps"] == 0
        assert s["reverts"] == 0
        assert s["crashes"] == 0
        assert s["best_metric"] is None
        assert s["best_commit"] is None
