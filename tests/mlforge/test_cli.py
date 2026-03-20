"""Tests for mlforge.cli -- CLI entry point with argparse."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from mlforge.cli import main


class TestCliNoArgs:
    """main([]) prints usage and returns 1."""

    def test_empty_args_returns_1(self, capsys):
        result = main([])
        assert result == 1

    def test_empty_args_prints_usage_to_stderr(self, capsys):
        main([])
        captured = capsys.readouterr()
        assert "usage:" in captured.err.lower()


class TestCliHelp:
    """main(["--help"]) exits 0 with help text."""

    def test_help_raises_system_exit_0(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0


class TestCliArgParsing:
    """Positional and optional args are parsed correctly."""

    def test_dataset_and_goal_parsed(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with patch("mlforge.cli.scaffold_experiment"):
            result = main([str(dataset), "predict price"])
        assert result == 0

    def test_domain_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with patch("mlforge.cli.scaffold_experiment") as mock_scaffold:
            main([str(dataset), "predict price", "--domain", "tabular"])
            config = mock_scaffold.call_args[1]["config"]
            assert config.domain == "tabular"

    def test_budget_usd_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with patch("mlforge.cli.scaffold_experiment") as mock_scaffold:
            main([str(dataset), "predict price", "--budget-usd", "10.0"])
            config = mock_scaffold.call_args[1]["config"]
            assert config.budget_usd == 10.0

    def test_budget_minutes_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with patch("mlforge.cli.scaffold_experiment") as mock_scaffold:
            main([str(dataset), "predict price", "--budget-minutes", "30"])
            config = mock_scaffold.call_args[1]["config"]
            assert config.budget_minutes == 30

    def test_budget_experiments_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with patch("mlforge.cli.scaffold_experiment") as mock_scaffold:
            main([str(dataset), "predict price", "--budget-experiments", "20"])
            config = mock_scaffold.call_args[1]["config"]
            assert config.budget_experiments == 20

    def test_resume_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with patch("mlforge.cli.scaffold_experiment") as mock_scaffold:
            main([str(dataset), "predict price", "--resume"])
            # resume is parsed -- check it's in the namespace
            # (resume doesn't go into Config, it's a CLI-only flag)

    def test_model_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with patch("mlforge.cli.scaffold_experiment") as mock_scaffold:
            main([str(dataset), "predict price", "--model", "sonnet"])
            config = mock_scaffold.call_args[1]["config"]
            assert config.model == "sonnet"

    def test_output_dir_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with patch("mlforge.cli.scaffold_experiment") as mock_scaffold:
            main([str(dataset), "predict price", "--output-dir", "/tmp/exp"])
            call_kwargs = mock_scaffold.call_args[1]
            assert str(call_kwargs["target_dir"]) == "/tmp/exp"


class TestCliValidation:
    """CLI validates inputs before proceeding."""

    def test_nonexistent_dataset_returns_1(self, capsys):
        result = main(["nonexistent.csv", "predict price"])
        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or "does not exist" in captured.err.lower()


class TestConfigNewFields:
    """Config dataclass has budget/timeout/model fields with correct defaults."""

    def test_budget_usd_default(self):
        from mlforge.config import Config
        config = Config()
        assert config.budget_usd == 5.0

    def test_per_experiment_timeout_sec_default(self):
        from mlforge.config import Config
        config = Config()
        assert config.per_experiment_timeout_sec == 300

    def test_per_experiment_budget_usd_default(self):
        from mlforge.config import Config
        config = Config()
        assert config.per_experiment_budget_usd == 1.0

    def test_max_turns_per_experiment_default(self):
        from mlforge.config import Config
        config = Config()
        assert config.max_turns_per_experiment == 30

    def test_model_default_none(self):
        from mlforge.config import Config
        config = Config()
        assert config.model is None

    def test_budget_usd_from_toml(self, tmp_path):
        from mlforge.config import Config, CONFIG_FILENAME
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text("""\
[budget]
usd = 25.0
per_experiment_timeout_sec = 600
per_experiment_budget_usd = 2.5
max_turns = 50
""")
        config = Config.load(config_path)
        assert config.budget_usd == 25.0
        assert config.per_experiment_timeout_sec == 600
        assert config.per_experiment_budget_usd == 2.5
        assert config.max_turns_per_experiment == 50

    def test_model_from_toml(self, tmp_path):
        from mlforge.config import Config, CONFIG_FILENAME
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text('model = "sonnet"\n')
        config = Config.load(config_path)
        assert config.model == "sonnet"
