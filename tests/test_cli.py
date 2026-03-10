"""Tests for CLI entry point (automl.cli)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


def test_cli_help(capsys):
    """main(["--help"]) exits 0 and prints usage info."""
    from automl.cli import main

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower()
    assert "data_path" in captured.out


def test_cli_missing_args():
    """main([]) exits non-zero (missing required positional args)."""
    from automl.cli import main

    ret = main([])
    assert ret != 0


def test_cli_valid_args(sample_classification_csv, tmp_path):
    """main([csv_path, "target", "accuracy"]) exits 0 and creates experiment directory."""
    from automl.cli import main

    out_dir = tmp_path / "exp-out"
    ret = main([
        str(sample_classification_csv),
        "target",
        "accuracy",
        "--output-dir",
        str(out_dir),
    ])
    assert ret == 0
    assert out_dir.exists()
    assert (out_dir / "train.py").exists()
    assert (out_dir / "prepare.py").exists()
    assert (out_dir / "program.md").exists()


def test_cli_with_optional_flags(sample_classification_csv, tmp_path):
    """main() accepts --goal, --output-dir, --time-budget optional flags."""
    from automl.cli import main

    out_dir = tmp_path / "exp-flags"
    ret = main([
        str(sample_classification_csv),
        "target",
        "accuracy",
        "--goal", "predict something",
        "--output-dir", str(out_dir),
        "--time-budget", "120",
    ])
    assert ret == 0
    assert out_dir.exists()
    # Verify time_budget made it into train.py
    train_content = (out_dir / "train.py").read_text()
    assert "TIME_BUDGET = 120" in train_content


def test_cli_bad_csv(capsys):
    """main(["nonexistent.csv", "target", "accuracy"]) exits 1 and prints error to stderr."""
    from automl.cli import main

    ret = main(["nonexistent.csv", "target", "accuracy"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "not found" in captured.err.lower()


def test_cli_bad_metric(sample_classification_csv, capsys, tmp_path):
    """main([csv_path, "target", "bogus_metric"]) exits 1 and prints error to stderr."""
    from automl.cli import main

    ret = main([
        str(sample_classification_csv),
        "target",
        "bogus_metric",
        "--output-dir",
        str(tmp_path / "exp-bad-metric"),
    ])
    assert ret == 1
    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "metric" in captured.err.lower()
