"""Tests for mlforge.status -- show past experiment runs."""

from __future__ import annotations

import json

from mlforge.status import show_status


class TestShowStatus:
    """show_status scans for mlforge experiment dirs."""

    def test_no_runs_returns_empty(self, tmp_path):
        result = show_status(tmp_path)
        assert result == []

    def test_finds_experiment_with_checkpoint(self, tmp_path):
        exp_dir = tmp_path / "mlforge-data"
        exp_dir.mkdir()
        mlforge_dir = exp_dir / ".mlforge"
        mlforge_dir.mkdir()
        checkpoint = {
            "run_id": "run-123",
            "experiment_count": 5,
            "best_metric": 0.95,
            "cost_spent_usd": 1.23,
            "total_keeps": 3,
            "total_reverts": 2,
        }
        (mlforge_dir / "checkpoint.json").write_text(json.dumps(checkpoint))

        result = show_status(tmp_path)
        assert len(result) == 1
        assert result[0]["run_id"] == "run-123"
        assert result[0]["experiments"] == 5
        assert result[0]["best_metric"] == 0.95
        assert result[0]["cost_usd"] == 1.23

    def test_skips_dirs_without_checkpoint(self, tmp_path):
        exp_dir = tmp_path / "mlforge-data"
        exp_dir.mkdir()
        result = show_status(tmp_path)
        assert result == []

    def test_multiple_runs(self, tmp_path):
        for name, run_id in [("mlforge-a", "run-1"), ("mlforge-b", "run-2")]:
            d = tmp_path / name / ".mlforge"
            d.mkdir(parents=True)
            (d / "checkpoint.json").write_text(
                json.dumps({"run_id": run_id, "experiment_count": 1})
            )
        result = show_status(tmp_path)
        assert len(result) == 2
