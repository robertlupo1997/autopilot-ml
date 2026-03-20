"""Tests for mlforge.retrospective -- run retrospective report generation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mlforge.config import Config
from mlforge.results import ExperimentResult, ResultsTracker
from mlforge.state import SessionState


def _make_tracker(tmp_path: Path, results: list[ExperimentResult] | None = None) -> ResultsTracker:
    """Create a ResultsTracker with optional pre-loaded results."""
    tracker = ResultsTracker(tmp_path / "results.jsonl")
    if results:
        for r in results:
            tracker.add(r)
    return tracker


def _make_result(
    experiment_id: int = 1,
    status: str = "keep",
    metric_value: float | None = 0.85,
    description: str = "test experiment",
    commit_hash: str | None = "abc1234",
) -> ExperimentResult:
    """Create a synthetic ExperimentResult."""
    return ExperimentResult(
        experiment_id=experiment_id,
        commit_hash=commit_hash,
        metric_name="accuracy",
        metric_value=metric_value,
        status=status,
        description=description,
        timestamp="2026-03-20T00:00:00Z",
    )


class TestGenerateRetrospective:
    """generate_retrospective produces markdown report."""

    def test_header_present(self, tmp_path: Path) -> None:
        from mlforge.retrospective import generate_retrospective

        tracker = _make_tracker(tmp_path)
        state = SessionState()
        config = Config()

        result = generate_retrospective(tracker, state, config)
        assert "# mlforge Run Retrospective" in result

    def test_summary_table_present(self, tmp_path: Path) -> None:
        from mlforge.retrospective import generate_retrospective

        results = [
            _make_result(1, "keep", 0.85),
            _make_result(2, "revert", 0.80),
            _make_result(3, "crash", None, commit_hash=None),
        ]
        tracker = _make_tracker(tmp_path, results)
        state = SessionState(experiment_count=3, cost_spent_usd=0.50)
        config = Config()

        output = generate_retrospective(tracker, state, config)
        assert "## Summary" in output
        assert "3" in output  # total experiments
        assert "1" in output  # keeps
        assert "0.50" in output  # cost

    def test_successful_approaches_listed(self, tmp_path: Path) -> None:
        from mlforge.retrospective import generate_retrospective

        results = [
            _make_result(1, "keep", 0.85, "Ridge regression with L2"),
            _make_result(2, "keep", 0.90, "XGBoost with tuned params"),
        ]
        tracker = _make_tracker(tmp_path, results)
        state = SessionState(experiment_count=2, cost_spent_usd=0.30)
        config = Config()

        output = generate_retrospective(tracker, state, config)
        assert "## Successful Approaches" in output
        assert "Ridge regression with L2" in output
        assert "XGBoost with tuned params" in output
        assert "0.85" in output
        assert "0.9" in output

    def test_failed_approaches_listed(self, tmp_path: Path) -> None:
        from mlforge.retrospective import generate_retrospective

        results = [
            _make_result(1, "keep", 0.85, "Ridge"),
            _make_result(2, "revert", 0.70, "Bad random forest config"),
            _make_result(3, "revert", 0.60, "Overfit neural net"),
        ]
        tracker = _make_tracker(tmp_path, results)
        state = SessionState(experiment_count=3, cost_spent_usd=0.40)
        config = Config()

        output = generate_retrospective(tracker, state, config)
        assert "## Failed Approaches" in output
        assert "Bad random forest config" in output
        assert "Overfit neural net" in output

    def test_zero_experiments_handled(self, tmp_path: Path) -> None:
        from mlforge.retrospective import generate_retrospective

        tracker = _make_tracker(tmp_path)
        state = SessionState(experiment_count=0, cost_spent_usd=0.0)
        config = Config()

        output = generate_retrospective(tracker, state, config)
        # Should not raise, should contain recommendation
        assert "No improvements found" in output or "No successful experiments" in output

    def test_high_revert_rate_recommendation(self, tmp_path: Path) -> None:
        from mlforge.retrospective import generate_retrospective

        results = [
            _make_result(1, "keep", 0.85, "One good one"),
            _make_result(2, "revert", 0.70, "bad 1"),
            _make_result(3, "revert", 0.60, "bad 2"),
            _make_result(4, "revert", 0.65, "bad 3"),
            _make_result(5, "revert", 0.55, "bad 4"),
        ]
        tracker = _make_tracker(tmp_path, results)
        state = SessionState(experiment_count=5, cost_spent_usd=0.80)
        config = Config()

        output = generate_retrospective(tracker, state, config)
        assert "High revert rate" in output

    def test_retrospective_written_to_file(self, tmp_path: Path) -> None:
        from mlforge.retrospective import generate_retrospective

        tracker = _make_tracker(tmp_path)
        state = SessionState()
        config = Config()

        output = generate_retrospective(tracker, state, config)
        retro_path = tmp_path / "RETROSPECTIVE.md"
        retro_path.write_text(output)
        assert retro_path.exists()
        assert "# mlforge Run Retrospective" in retro_path.read_text()
