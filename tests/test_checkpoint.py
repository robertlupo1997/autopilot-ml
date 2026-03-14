"""Tests for checkpoint persistence module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from automl.loop_helpers import LoopState


class TestSaveCheckpoint:
    """save_checkpoint() writes valid JSON to checkpoint.json atomically."""

    def test_save_creates_checkpoint_json(self, tmp_path):
        from automl.checkpoint import CHECKPOINT_FILE, save_checkpoint

        state = LoopState()
        save_checkpoint(state, "iteration", 5, path=str(tmp_path))
        assert (tmp_path / CHECKPOINT_FILE).exists()

    def test_save_writes_valid_json(self, tmp_path):
        from automl.checkpoint import CHECKPOINT_FILE, save_checkpoint

        state = LoopState(best_score=0.95, best_commit="abc1234", total_experiments=5)
        save_checkpoint(state, "iteration", 5, path=str(tmp_path))

        data = json.loads((tmp_path / CHECKPOINT_FILE).read_text())
        assert isinstance(data, dict)

    def test_save_includes_all_loop_state_fields(self, tmp_path):
        from automl.checkpoint import CHECKPOINT_FILE, save_checkpoint

        state = LoopState(
            best_score=0.95,
            best_commit="abc1234",
            consecutive_reverts=2,
            consecutive_crashes=1,
            last_crash_error="timeout",
            total_experiments=10,
            total_keeps=4,
            total_reverts=5,
            total_crashes=1,
            strategy_categories_tried=["hyperparameter_tuning"],
            stagnation_threshold=5,
            crash_threshold=3,
        )
        save_checkpoint(state, "iteration", 10, path=str(tmp_path))

        data = json.loads((tmp_path / CHECKPOINT_FILE).read_text())
        assert data["best_score"] == 0.95
        assert data["best_commit"] == "abc1234"
        assert data["consecutive_reverts"] == 2
        assert data["consecutive_crashes"] == 1
        assert data["last_crash_error"] == "timeout"
        assert data["total_experiments"] == 10
        assert data["total_keeps"] == 4
        assert data["total_reverts"] == 5
        assert data["total_crashes"] == 1
        assert data["strategy_categories_tried"] == ["hyperparameter_tuning"]
        assert data["stagnation_threshold"] == 5
        assert data["crash_threshold"] == 3

    def test_save_includes_metadata_fields(self, tmp_path):
        from automl.checkpoint import CHECKPOINT_FILE, SCHEMA_VERSION, save_checkpoint

        state = LoopState()
        save_checkpoint(state, "draft", 3, path=str(tmp_path))

        data = json.loads((tmp_path / CHECKPOINT_FILE).read_text())
        assert data["loop_phase"] == "draft"
        assert data["iteration"] == 3
        assert data["schema_version"] == SCHEMA_VERSION

    def test_save_no_tmp_file_remains(self, tmp_path):
        """After save, the .tmp file should be gone (renamed to .json)."""
        from automl.checkpoint import save_checkpoint

        state = LoopState()
        save_checkpoint(state, "iteration", 1, path=str(tmp_path))

        tmp_file = tmp_path / "checkpoint.json.tmp"
        assert not tmp_file.exists()


class TestAtomicWrite:
    """save_checkpoint uses write-then-rename for atomicity."""

    def test_atomic_write_removes_tmp(self, tmp_path):
        """After successful save, .tmp file is gone."""
        from automl.checkpoint import save_checkpoint

        state = LoopState()
        save_checkpoint(state, "iteration", 1, path=str(tmp_path))

        assert not (tmp_path / "checkpoint.json.tmp").exists()
        assert (tmp_path / "checkpoint.json").exists()

    def test_atomic_write_overwrites_previous(self, tmp_path):
        """Second save overwrites the first correctly."""
        from automl.checkpoint import CHECKPOINT_FILE, save_checkpoint

        state1 = LoopState(best_score=0.8)
        save_checkpoint(state1, "iteration", 1, path=str(tmp_path))

        state2 = LoopState(best_score=0.9)
        save_checkpoint(state2, "iteration", 2, path=str(tmp_path))

        data = json.loads((tmp_path / CHECKPOINT_FILE).read_text())
        assert data["best_score"] == 0.9
        assert data["iteration"] == 2


class TestLoadCheckpoint:
    """load_checkpoint() returns dict or None."""

    def test_load_returns_dict_when_exists(self, tmp_path):
        from automl.checkpoint import load_checkpoint, save_checkpoint

        state = LoopState(best_score=0.75)
        save_checkpoint(state, "iteration", 7, path=str(tmp_path))

        result = load_checkpoint(path=str(tmp_path))
        assert isinstance(result, dict)

    def test_load_returns_none_when_absent(self, tmp_path):
        from automl.checkpoint import load_checkpoint

        result = load_checkpoint(path=str(tmp_path))
        assert result is None

    def test_load_returns_none_when_corrupt(self, tmp_path):
        from automl.checkpoint import CHECKPOINT_FILE, load_checkpoint

        (tmp_path / CHECKPOINT_FILE).write_text("this is not json {{{{")
        result = load_checkpoint(path=str(tmp_path))
        assert result is None

    def test_load_returns_correct_values(self, tmp_path):
        from automl.checkpoint import load_checkpoint, save_checkpoint

        state = LoopState(best_score=0.85, best_commit="deadbeef")
        save_checkpoint(state, "iteration", 12, path=str(tmp_path))

        data = load_checkpoint(path=str(tmp_path))
        assert data["best_score"] == 0.85
        assert data["best_commit"] == "deadbeef"
        assert data["loop_phase"] == "iteration"
        assert data["iteration"] == 12

    def test_load_returns_none_when_empty_file(self, tmp_path):
        from automl.checkpoint import CHECKPOINT_FILE, load_checkpoint

        (tmp_path / CHECKPOINT_FILE).write_text("")
        result = load_checkpoint(path=str(tmp_path))
        assert result is None


class TestLoadLoopState:
    """load_loop_state() reconstructs LoopState from checkpoint."""

    def test_load_loop_state_returns_loop_state(self, tmp_path):
        from automl.checkpoint import load_loop_state, save_checkpoint

        state = LoopState(best_score=0.9)
        save_checkpoint(state, "iteration", 5, path=str(tmp_path))

        result = load_loop_state(path=str(tmp_path))
        assert isinstance(result, LoopState)

    def test_load_loop_state_returns_none_when_no_checkpoint(self, tmp_path):
        from automl.checkpoint import load_loop_state

        result = load_loop_state(path=str(tmp_path))
        assert result is None

    def test_load_loop_state_filters_non_loop_state_fields(self, tmp_path):
        from automl.checkpoint import load_loop_state, save_checkpoint

        state = LoopState(best_score=0.88)
        save_checkpoint(state, "iteration", 3, path=str(tmp_path))

        result = load_loop_state(path=str(tmp_path))
        # These metadata fields should NOT be on the LoopState object
        assert not hasattr(result, "loop_phase")
        assert not hasattr(result, "iteration")
        assert not hasattr(result, "schema_version")

    def test_load_loop_state_correct_field_values(self, tmp_path):
        from automl.checkpoint import load_loop_state, save_checkpoint

        state = LoopState(
            best_score=0.91,
            best_commit="cafe1234",
            consecutive_reverts=3,
            consecutive_crashes=0,
            total_experiments=15,
            total_keeps=6,
            total_reverts=8,
            total_crashes=1,
            strategy_categories_tried=["hyperparameter_tuning", "algorithm_switch"],
        )
        save_checkpoint(state, "iteration", 15, path=str(tmp_path))

        result = load_loop_state(path=str(tmp_path))
        assert result.best_score == 0.91
        assert result.best_commit == "cafe1234"
        assert result.consecutive_reverts == 3
        assert result.consecutive_crashes == 0
        assert result.total_experiments == 15
        assert result.total_keeps == 6
        assert result.total_reverts == 8
        assert result.total_crashes == 1
        assert result.strategy_categories_tried == [
            "hyperparameter_tuning",
            "algorithm_switch",
        ]

    def test_load_loop_state_returns_none_on_corrupt(self, tmp_path):
        from automl.checkpoint import CHECKPOINT_FILE, load_loop_state

        (tmp_path / CHECKPOINT_FILE).write_text("not valid json")
        result = load_loop_state(path=str(tmp_path))
        assert result is None


class TestCheckpointExists:
    """checkpoint_exists() returns True/False based on file presence."""

    def test_exists_returns_false_when_absent(self, tmp_path):
        from automl.checkpoint import checkpoint_exists

        assert checkpoint_exists(path=str(tmp_path)) is False

    def test_exists_returns_true_when_present(self, tmp_path):
        from automl.checkpoint import checkpoint_exists, save_checkpoint

        state = LoopState()
        save_checkpoint(state, "iteration", 1, path=str(tmp_path))

        assert checkpoint_exists(path=str(tmp_path)) is True

    def test_exists_uses_correct_filename(self, tmp_path):
        from automl.checkpoint import CHECKPOINT_FILE, checkpoint_exists

        # Write an unrelated file — should not count
        (tmp_path / "other.json").write_text("{}")
        assert checkpoint_exists(path=str(tmp_path)) is False

        # Write the correct checkpoint file
        (tmp_path / CHECKPOINT_FILE).write_text("{}")
        assert checkpoint_exists(path=str(tmp_path)) is True


class TestRoundTrip:
    """LoopState round-trips through save/load without data loss."""

    def test_round_trip_all_fields(self, tmp_path):
        from automl.checkpoint import load_loop_state, save_checkpoint

        original = LoopState(
            best_score=0.9876,
            best_commit="abc123",
            consecutive_reverts=2,
            consecutive_crashes=1,
            last_crash_error="MemoryError",
            total_experiments=20,
            total_keeps=8,
            total_reverts=10,
            total_crashes=2,
            strategy_categories_tried=["hyperparameter_tuning", "ensemble_methods"],
            stagnation_threshold=5,
            crash_threshold=3,
        )
        save_checkpoint(original, "iteration", 20, path=str(tmp_path))
        restored = load_loop_state(path=str(tmp_path))

        assert restored.best_score == original.best_score
        assert restored.best_commit == original.best_commit
        assert restored.consecutive_reverts == original.consecutive_reverts
        assert restored.consecutive_crashes == original.consecutive_crashes
        assert restored.last_crash_error == original.last_crash_error
        assert restored.total_experiments == original.total_experiments
        assert restored.total_keeps == original.total_keeps
        assert restored.total_reverts == original.total_reverts
        assert restored.total_crashes == original.total_crashes
        assert restored.strategy_categories_tried == original.strategy_categories_tried
        assert restored.stagnation_threshold == original.stagnation_threshold
        assert restored.crash_threshold == original.crash_threshold

    def test_round_trip_preserves_none_fields(self, tmp_path):
        from automl.checkpoint import load_loop_state, save_checkpoint

        original = LoopState(best_score=None, best_commit=None, last_crash_error=None)
        save_checkpoint(original, "draft", 0, path=str(tmp_path))
        restored = load_loop_state(path=str(tmp_path))

        assert restored.best_score is None
        assert restored.best_commit is None
        assert restored.last_crash_error is None

    def test_round_trip_preserves_list_fields(self, tmp_path):
        from automl.checkpoint import load_loop_state, save_checkpoint

        original = LoopState(
            strategy_categories_tried=[
                "hyperparameter_tuning",
                "algorithm_switch",
                "ensemble_methods",
            ]
        )
        save_checkpoint(original, "iteration", 10, path=str(tmp_path))
        restored = load_loop_state(path=str(tmp_path))

        assert restored.strategy_categories_tried == [
            "hyperparameter_tuning",
            "algorithm_switch",
            "ensemble_methods",
        ]

    def test_round_trip_empty_list(self, tmp_path):
        from automl.checkpoint import load_loop_state, save_checkpoint

        original = LoopState(strategy_categories_tried=[])
        save_checkpoint(original, "draft", 0, path=str(tmp_path))
        restored = load_loop_state(path=str(tmp_path))

        assert restored.strategy_categories_tried == []
