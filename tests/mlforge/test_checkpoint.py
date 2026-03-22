"""Tests for mlforge.checkpoint -- save/load with schema versioning."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mlforge.checkpoint import CHECKPOINT_FILE, SCHEMA_VERSION, load_checkpoint, save_checkpoint
from mlforge.state import SessionState


class TestCheckpointRoundTrip:
    """save_checkpoint + load_checkpoint preserves all state fields."""

    def test_save_and_load_roundtrip(self, tmp_dir: Path, sample_state: SessionState):
        save_checkpoint(sample_state, tmp_dir)
        restored = load_checkpoint(tmp_dir)
        assert restored is not None
        assert restored.experiment_count == sample_state.experiment_count
        assert restored.best_metric == sample_state.best_metric
        assert restored.best_commit == sample_state.best_commit
        assert restored.budget_remaining == sample_state.budget_remaining
        assert restored.consecutive_reverts == sample_state.consecutive_reverts
        assert restored.total_keeps == sample_state.total_keeps
        assert restored.total_reverts == sample_state.total_reverts
        assert restored.run_id == sample_state.run_id

    def test_roundtrip_default_state(self, tmp_dir: Path):
        state = SessionState()
        save_checkpoint(state, tmp_dir)
        restored = load_checkpoint(tmp_dir)
        assert restored is not None
        assert restored == state


class TestCheckpointMissing:
    """load_checkpoint returns None when no checkpoint file exists."""

    def test_load_missing_checkpoint_returns_none(self, tmp_dir: Path):
        result = load_checkpoint(tmp_dir)
        assert result is None

    def test_load_nonexistent_dir_returns_none(self, tmp_dir: Path):
        result = load_checkpoint(tmp_dir / "nonexistent")
        assert result is None


class TestCheckpointSchema:
    """Checkpoint file includes schema_version and timestamp."""

    def test_checkpoint_contains_schema_version(self, tmp_dir: Path, sample_state: SessionState):
        save_checkpoint(sample_state, tmp_dir)
        raw = json.loads((tmp_dir / CHECKPOINT_FILE).read_text())
        assert raw["schema_version"] == SCHEMA_VERSION

    def test_checkpoint_contains_timestamp(self, tmp_dir: Path, sample_state: SessionState):
        save_checkpoint(sample_state, tmp_dir)
        raw = json.loads((tmp_dir / CHECKPOINT_FILE).read_text())
        assert "timestamp" in raw
        assert isinstance(raw["timestamp"], str)
        # ISO format contains 'T' between date and time
        assert "T" in raw["timestamp"]

    def test_schema_version_is_one(self):
        assert SCHEMA_VERSION == 1


class TestCheckpointForwardCompat:
    """load_checkpoint ignores unknown fields in the state dict."""

    def test_load_ignores_unknown_state_fields(self, tmp_dir: Path):
        checkpoint_data = {
            "schema_version": 1,
            "state": {
                "experiment_count": 7,
                "best_metric": 0.99,
                "best_commit": "def5678",
                "budget_remaining": 20.0,
                "consecutive_reverts": 0,
                "total_keeps": 5,
                "total_reverts": 2,
                "run_id": "compat-test",
                "future_field": "should_be_ignored",
                "v99_feature": True,
            },
            "timestamp": "2026-01-01T00:00:00+00:00",
        }
        (tmp_dir / CHECKPOINT_FILE).write_text(json.dumps(checkpoint_data))
        state = load_checkpoint(tmp_dir)
        assert state is not None
        assert state.experiment_count == 7
        assert state.run_id == "compat-test"
        assert not hasattr(state, "future_field")


class TestCheckpointCorruption:
    """load_checkpoint raises ValueError on corrupt JSON."""

    def test_load_corrupt_json_raises(self, tmp_dir: Path):
        (tmp_dir / CHECKPOINT_FILE).write_text("not valid json {{{")
        with pytest.raises(ValueError, match="[Cc]orrupt|JSON|json"):
            load_checkpoint(tmp_dir)


class TestCheckpointAtomicWrite:
    """save_checkpoint uses atomic write-then-rename."""

    def test_save_is_atomic(self, tmp_dir: Path, sample_state: SessionState):
        save_checkpoint(sample_state, tmp_dir)
        # The .tmp file should not exist after a successful save
        tmp_file = tmp_dir / (CHECKPOINT_FILE + ".tmp")
        assert not tmp_file.exists()
        # But the actual checkpoint file should exist
        assert (tmp_dir / CHECKPOINT_FILE).exists()
