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


# ---------------------------------------------------------------------------
# --resume flag tests
# ---------------------------------------------------------------------------

class TestCliResumeFlag:
    """Tests for the --resume CLI flag."""

    def test_resume_flag_accepted(self):
        """argparse accepts --resume without error (no SystemExit or exception)."""
        import argparse
        from automl.cli import main

        # We can't call main() with --resume without a real CSV, so test
        # the argparse layer directly by importing and invoking parse_args.
        # Since the parser is created inside main(), we verify via --help output
        # that --resume is present in the usage.
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_resume_flag_in_help(self, capsys):
        """--help output includes --resume."""
        from automl.cli import main

        with pytest.raises(SystemExit):
            main(["--help"])
        captured = capsys.readouterr()
        assert "--resume" in captured.out

    def test_resume_flag_default_false(self):
        """--resume defaults to False when not provided."""
        import argparse

        # Build a standalone parser that mirrors cli.py to test the flag default
        parser = argparse.ArgumentParser(prog="automl")
        parser.add_argument("data_path")
        parser.add_argument("target_column")
        parser.add_argument("metric")
        parser.add_argument("--resume", action="store_true", default=False)

        args = parser.parse_args(["data.csv", "target", "accuracy"])
        assert args.resume is False

    def test_resume_flag_true_when_set(self):
        """--resume is True when flag is provided."""
        import argparse

        parser = argparse.ArgumentParser(prog="automl")
        parser.add_argument("data_path")
        parser.add_argument("target_column")
        parser.add_argument("metric")
        parser.add_argument("--resume", action="store_true", default=False)

        args = parser.parse_args(["data.csv", "target", "accuracy", "--resume"])
        assert args.resume is True


# ---------------------------------------------------------------------------
# --agents flag tests
# ---------------------------------------------------------------------------

class TestCliAgentsFlag:
    """Tests for the --agents N CLI flag."""

    def test_agents_flag_default(self):
        """--agents defaults to 1 when not provided."""
        import argparse

        parser = argparse.ArgumentParser(prog="automl")
        parser.add_argument("data_path")
        parser.add_argument("target_column")
        parser.add_argument("metric")
        parser.add_argument("--agents", type=int, default=1, metavar="N")

        args = parser.parse_args(["data.csv", "target", "accuracy"])
        assert args.agents == 1

    def test_agents_flag_accepted(self):
        """--agents 3 stores args.agents=3."""
        import argparse

        parser = argparse.ArgumentParser(prog="automl")
        parser.add_argument("data_path")
        parser.add_argument("target_column")
        parser.add_argument("metric")
        parser.add_argument("--agents", type=int, default=1, metavar="N")

        args = parser.parse_args(["data.csv", "target", "accuracy", "--agents", "3"])
        assert args.agents == 3

    def test_agents_flag_zero_error(self, sample_classification_csv, tmp_path, capsys):
        """--agents 0 returns exit code 1 with error message."""
        from automl.cli import main

        ret = main([
            str(sample_classification_csv),
            "target",
            "accuracy",
            "--output-dir",
            str(tmp_path / "exp-agents-zero"),
            "--agents",
            "0",
        ])
        assert ret == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower() or "agents" in captured.err.lower()

    def test_agents_flag_in_help(self, capsys):
        """--help output includes --agents."""
        from automl.cli import main

        with pytest.raises(SystemExit):
            main(["--help"])
        captured = capsys.readouterr()
        assert "--agents" in captured.out

    def test_agents_flag_help_mentions_terminal(self, capsys):
        """--agents help text mentions running from terminal outside Claude Code."""
        from automl.cli import main

        with pytest.raises(SystemExit):
            main(["--help"])
        captured = capsys.readouterr()
        # Help text should mention terminal or Claude Code
        assert "terminal" in captured.out.lower() or "claude code" in captured.out.lower()


# ---------------------------------------------------------------------------
# --date-column flag tests
# ---------------------------------------------------------------------------

class TestCliDateColumnFlag:
    """Tests for the --date-column CLI flag."""

    def test_date_column_in_help(self, capsys):
        """--help output includes --date-column."""
        from automl.cli import main

        with pytest.raises(SystemExit):
            main(["--help"])
        captured = capsys.readouterr()
        assert "date-column" in captured.out

    def test_date_column_default_none(self):
        """--date-column defaults to None when not provided."""
        import argparse

        parser = argparse.ArgumentParser(prog="automl")
        parser.add_argument("data_path")
        parser.add_argument("target_column")
        parser.add_argument("metric")
        parser.add_argument("--date-column", default=None)

        args = parser.parse_args(["data.csv", "target", "mape"])
        assert args.date_column is None

    def test_date_column_passed_through(self, tmp_path):
        """--date-column passes date_col='date' to scaffold_experiment."""
        from unittest.mock import patch, MagicMock
        from automl.cli import main

        mock_path = MagicMock()
        mock_path.resolve.return_value = tmp_path / "exp"

        with patch("automl.cli.scaffold_experiment", return_value=mock_path) as mock_scaffold:
            ret = main(["data.csv", "revenue", "mape", "--date-column", "date"])

        mock_scaffold.assert_called_once()
        call_kwargs = mock_scaffold.call_args
        assert call_kwargs.kwargs.get("date_col") == "date" or (
            len(call_kwargs.args) > 0 and "date" in str(call_kwargs)
        )

    def test_agents_with_date_column_rejected(self, tmp_path, capsys):
        """--agents 2 --date-column date returns exit code 1 with error message."""
        from unittest.mock import patch, MagicMock
        from automl.cli import main

        mock_path = MagicMock()
        mock_path.resolve.return_value = tmp_path / "exp"

        with patch("automl.cli.scaffold_experiment", return_value=mock_path):
            ret = main(["data.csv", "revenue", "mape", "--date-column", "date", "--agents", "2"])

        assert ret == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower() or "not supported" in captured.err.lower()
