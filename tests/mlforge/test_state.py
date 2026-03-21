"""Tests for mlforge.state — SessionState dataclass with JSON persistence."""

from __future__ import annotations

from mlforge.state import SessionState


class TestSessionStateDefaults:
    """SessionState can be created with defaults."""

    def test_default_experiment_count(self):
        state = SessionState()
        assert state.experiment_count == 0

    def test_default_best_metric_is_none(self):
        state = SessionState()
        assert state.best_metric is None

    def test_default_best_commit_is_none(self):
        state = SessionState()
        assert state.best_commit is None

    def test_default_budget_remaining(self):
        state = SessionState()
        assert state.budget_remaining == 0.0

    def test_default_consecutive_reverts(self):
        state = SessionState()
        assert state.consecutive_reverts == 0

    def test_default_run_id_is_empty(self):
        state = SessionState()
        assert state.run_id == ""


