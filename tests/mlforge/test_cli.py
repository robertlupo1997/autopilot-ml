"""Tests for mlforge.cli -- CLI entry point with argparse."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from mlforge.cli import main


def _mock_engine_run(state):
    """Return a mock RunEngine whose run() is a no-op."""
    mock_engine = MagicMock()
    mock_engine.run = MagicMock()
    return mock_engine


def _patch_all():
    """Context manager that patches scaffold, GitManager, and RunEngine."""
    return (
        patch("mlforge.cli.scaffold_experiment"),
        patch("mlforge.cli.GitManager"),
        patch("mlforge.cli.RunEngine"),
    )


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
        with (
            patch("mlforge.cli.scaffold_experiment"),
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            result = main([str(dataset), "predict price"])
        assert result == 0

    def test_domain_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([str(dataset), "predict price", "--domain", "tabular"])
            config = mock_scaffold.call_args[1]["config"]
            assert config.domain == "tabular"

    def test_budget_usd_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([str(dataset), "predict price", "--budget-usd", "10.0"])
            config = mock_scaffold.call_args[1]["config"]
            assert config.budget_usd == 10.0

    def test_budget_minutes_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([str(dataset), "predict price", "--budget-minutes", "30"])
            config = mock_scaffold.call_args[1]["config"]
            assert config.budget_minutes == 30

    def test_budget_experiments_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([str(dataset), "predict price", "--budget-experiments", "20"])
            config = mock_scaffold.call_args[1]["config"]
            assert config.budget_experiments == 20

    def test_resume_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment"),
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            # Resume requires a checkpoint to exist; without it, returns 1
            main([str(dataset), "predict price", "--resume"])

    def test_model_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([str(dataset), "predict price", "--model", "sonnet"])
            config = mock_scaffold.call_args[1]["config"]
            assert config.model == "sonnet"

    def test_output_dir_flag(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
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


class TestCliScaffoldEngineWiring:
    """CLI wires scaffold -> git init -> engine flow."""

    def test_scaffold_called_on_fresh_run(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([str(dataset), "predict price"])
            assert mock_scaffold.called

    def test_git_branch_created_on_fresh_run(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment"),
            patch("mlforge.cli.GitManager") as MockGit,
            patch("mlforge.cli.RunEngine"),
        ):
            main([str(dataset), "predict price"])
            mock_git_instance = MockGit.return_value
            assert mock_git_instance.create_run_branch.called

    def test_engine_run_called(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment"),
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine") as MockEngine,
        ):
            main([str(dataset), "predict price"])
            mock_engine_instance = MockEngine.return_value
            assert mock_engine_instance.run.called

    def test_resume_skips_scaffold(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        target_dir = tmp_path / "output"
        target_dir.mkdir()

        from mlforge.state import SessionState
        from mlforge.checkpoint import save_checkpoint

        state = SessionState(run_id="run-123", experiment_count=3)
        save_checkpoint(state, target_dir / ".mlforge")

        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            result = main([
                str(dataset), "predict price",
                "--resume", "--output-dir", str(target_dir),
            ])
            assert result == 0
            assert not mock_scaffold.called

    def test_resume_no_checkpoint_returns_1(self, tmp_path, capsys):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        target_dir = tmp_path / "output"
        target_dir.mkdir()

        result = main([
            str(dataset), "predict price",
            "--resume", "--output-dir", str(target_dir),
        ])
        assert result == 1
        captured = capsys.readouterr()
        assert "no checkpoint" in captured.err.lower()

    def test_prints_summary_on_completion(self, tmp_path, capsys):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment"),
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([str(dataset), "predict price"])
        captured = capsys.readouterr()
        assert "Completed" in captured.out or "completed" in captured.out.lower()


class TestExpertMode:
    """Expert mode CLI flags for custom CLAUDE.md, frozen, and mutable files."""

    def test_custom_claude_md_flag_parsed(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([
                str(dataset), "predict price",
                "--metric", "rmse",
                "--custom-claude-md", "/tmp/my-claude.md",
            ])
            config = mock_scaffold.call_args[1]["config"]
            assert config.custom_claude_md_path == Path("/tmp/my-claude.md")

    def test_custom_frozen_flag_parsed(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([
                str(dataset), "predict price",
                "--metric", "rmse",
                "--custom-frozen", "prepare.py", "evaluate.py",
            ])
            config = mock_scaffold.call_args[1]["config"]
            assert config.custom_frozen == ["prepare.py", "evaluate.py"]

    def test_custom_mutable_flag_parsed(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([
                str(dataset), "predict price",
                "--metric", "rmse",
                "--custom-mutable", "train.py", "features.py",
            ])
            config = mock_scaffold.call_args[1]["config"]
            assert config.custom_mutable == ["train.py", "features.py"]


class TestSimpleMode:
    """Simple mode auto-detects task type and metric from dataset."""

    def test_auto_detection_sets_metric(self, tmp_path):
        dataset = tmp_path / "data.csv"
        # Regression dataset: numeric target with many unique values
        import numpy as np
        lines = ["feature,target"]
        for i in range(50):
            lines.append(f"{i},{float(i) * 1.5 + 0.1 * i}")
        dataset.write_text("\n".join(lines) + "\n")

        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([str(dataset), "predict target"])
            config = mock_scaffold.call_args[1]["config"]
            assert config.metric == "r2"
            assert config.direction == "maximize"

    def test_auto_detection_prints_message(self, tmp_path, capsys):
        dataset = tmp_path / "data.csv"
        lines = ["feature,target"]
        for i in range(50):
            lines.append(f"{i},{float(i) * 1.5}")
        dataset.write_text("\n".join(lines) + "\n")

        with (
            patch("mlforge.cli.scaffold_experiment"),
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([str(dataset), "predict target"])
        captured = capsys.readouterr()
        assert "Auto-detected" in captured.out

    def test_explicit_metric_skips_profiling(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment") as mock_scaffold,
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
            patch("mlforge.cli.profile_dataset") as mock_profile,
        ):
            main([str(dataset), "predict b", "--metric", "rmse"])
            config = mock_scaffold.call_args[1]["config"]
            assert config.metric == "rmse"
            mock_profile.assert_not_called()


class TestSwarmCli:
    """Swarm mode CLI flags: --swarm, --n-agents."""

    def test_swarm_flag_routes_to_swarm_manager(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment"),
            patch("mlforge.cli.GitManager"),
            patch("mlforge.swarm.SwarmManager") as MockSM,
        ):
            mock_sm = MockSM.return_value
            mock_sm.run.return_value = {
                "agents": 3,
                "best_score": 0.9,
                "best_agent": "agent-0",
                "results": [],
                "verification": None,
            }
            result = main([str(dataset), "predict b", "--swarm"])
        assert result == 0
        assert MockSM.called
        mock_sm.setup.assert_called_once()
        mock_sm.run.assert_called_once()
        mock_sm.teardown.assert_called_once()

    def test_swarm_with_n_agents(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment"),
            patch("mlforge.cli.GitManager"),
            patch("mlforge.swarm.SwarmManager") as MockSM,
        ):
            mock_sm = MockSM.return_value
            mock_sm.run.return_value = {
                "agents": 5,
                "best_score": 0.9,
                "best_agent": "agent-0",
                "results": [],
                "verification": None,
            }
            main([str(dataset), "predict b", "--swarm", "--n-agents", "5"])
            call_kwargs = MockSM.call_args[1]
            assert call_kwargs["n_agents"] == 5

    def test_n_agents_without_swarm_warns(self, tmp_path, capsys):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment"),
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine"),
        ):
            main([str(dataset), "predict b", "--n-agents", "5"])
        captured = capsys.readouterr()
        assert "warning" in captured.err.lower()

    def test_swarm_with_resume_returns_error(self, tmp_path, capsys):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        result = main([str(dataset), "predict b", "--swarm", "--resume"])
        assert result == 1
        captured = capsys.readouterr()
        assert "cannot be used together" in captured.err.lower()

    def test_swarm_does_not_call_run_engine(self, tmp_path):
        dataset = tmp_path / "data.csv"
        dataset.write_text("a,b\n1,2\n")
        with (
            patch("mlforge.cli.scaffold_experiment"),
            patch("mlforge.cli.GitManager"),
            patch("mlforge.cli.RunEngine") as MockEngine,
            patch("mlforge.swarm.SwarmManager") as MockSM,
        ):
            mock_sm = MockSM.return_value
            mock_sm.run.return_value = {
                "agents": 3,
                "best_score": 0.9,
                "best_agent": "agent-0",
                "results": [],
                "verification": None,
            }
            main([str(dataset), "predict b", "--swarm"])
        assert not MockEngine.called


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
