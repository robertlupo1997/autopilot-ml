"""Tests for mlforge.state — SessionState dataclass with JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path

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


class TestSessionStateJsonRoundTrip:
    """SessionState serializes to JSON and deserializes with all fields intact."""

    def test_round_trip_preserves_all_fields(self, tmp_dir: Path, sample_state: SessionState):
        path = tmp_dir / "state.json"
        sample_state.to_json(path)
        restored = SessionState.from_json(path)
        assert restored.experiment_count == sample_state.experiment_count
        assert restored.best_metric == sample_state.best_metric
        assert restored.best_commit == sample_state.best_commit
        assert restored.budget_remaining == sample_state.budget_remaining
        assert restored.consecutive_reverts == sample_state.consecutive_reverts
        assert restored.total_keeps == sample_state.total_keeps
        assert restored.total_reverts == sample_state.total_reverts
        assert restored.run_id == sample_state.run_id

    def test_round_trip_defaults(self, tmp_dir: Path):
        path = tmp_dir / "state.json"
        state = SessionState()
        state.to_json(path)
        restored = SessionState.from_json(path)
        assert restored == state

    def test_to_json_creates_valid_json(self, tmp_dir: Path, sample_state: SessionState):
        path = tmp_dir / "state.json"
        sample_state.to_json(path)
        data = json.loads(path.read_text())
        assert data["experiment_count"] == 5
        assert data["best_metric"] == 0.95


class TestSessionStateAtomicWrite:
    """to_json uses atomic write-then-rename (.json.tmp -> .json)."""

    def test_no_tmp_file_after_write(self, tmp_dir: Path, sample_state: SessionState):
        path = tmp_dir / "state.json"
        sample_state.to_json(path)
        tmp_file = path.with_suffix(".json.tmp")
        assert not tmp_file.exists()
        assert path.exists()


class TestSessionStateForwardCompat:
    """from_json ignores unknown fields for forward compatibility."""

    def test_ignores_unknown_fields(self, tmp_dir: Path):
        path = tmp_dir / "state.json"
        data = {
            "experiment_count": 3,
            "best_metric": 0.8,
            "best_commit": None,
            "budget_remaining": 30.0,
            "consecutive_reverts": 0,
            "total_keeps": 2,
            "total_reverts": 1,
            "run_id": "run-1",
            "future_field": "should_be_ignored",
            "another_new_field": 42,
        }
        path.write_text(json.dumps(data))
        state = SessionState.from_json(path)
        assert state.experiment_count == 3
        assert not hasattr(state, "future_field")

    def test_missing_file_raises(self, tmp_dir: Path):
        import pytest

        path = tmp_dir / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            SessionState.from_json(path)
