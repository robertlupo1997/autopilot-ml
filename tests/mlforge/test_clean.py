"""Tests for mlforge.clean -- cleanup of old experiment artifacts."""

from __future__ import annotations

from mlforge.clean import clean_experiments


class TestCleanExperiments:
    """clean_experiments removes old mlforge experiment dirs."""

    def test_no_dirs_to_clean(self, tmp_path):
        result = clean_experiments(tmp_path)
        assert result["dirs_removed"] == 0

    def test_dry_run_does_not_delete(self, tmp_path):
        exp_dir = tmp_path / "mlforge-data"
        exp_dir.mkdir()
        (exp_dir / "train.py").write_text("# training")

        result = clean_experiments(tmp_path, dry_run=True)
        assert result["dirs_removed"] == 1
        assert exp_dir.exists()  # Not actually removed

    def test_removes_experiment_dirs(self, tmp_path):
        exp_dir = tmp_path / "mlforge-data"
        exp_dir.mkdir()
        (exp_dir / "train.py").write_text("# training")

        result = clean_experiments(tmp_path, dry_run=False)
        assert result["dirs_removed"] == 1
        assert not exp_dir.exists()

    def test_removes_multiple_dirs(self, tmp_path):
        for name in ["mlforge-a", "mlforge-b", "mlforge-c"]:
            d = tmp_path / name
            d.mkdir()
            (d / "data.csv").write_text("a,b\n1,2\n")

        result = clean_experiments(tmp_path, dry_run=False)
        assert result["dirs_removed"] == 3
