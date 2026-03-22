"""Smoke integration test -- validates the full pipeline with real file I/O.

Only subprocess.run (the ``claude -p`` call) is mocked. Everything else
(scaffold, git, checkpoint, engine result processing) uses real operations.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from mlforge.config import Config
from mlforge.engine import RunEngine
from mlforge.git_ops import GitManager
from mlforge.scaffold import scaffold_experiment
from mlforge.state import SessionState


@pytest.mark.slow
class TestSmokeIntegration:
    """End-to-end smoke test with canned subprocess response."""

    @pytest.fixture
    def experiment_setup(self, tmp_path):
        """Create a real scaffolded experiment directory."""
        import subprocess

        dataset = tmp_path / "data.csv"
        lines = ["feature1,feature2,target"]
        for i in range(30):
            lines.append(f"{i},{float(i) * 0.5},{i % 2}")
        dataset.write_text("\n".join(lines) + "\n")

        config = Config(
            domain="tabular",
            metric="accuracy",
            direction="maximize",
            budget_experiments=2,
            budget_usd=1.0,
            budget_minutes=5,
        )
        config.plugin_settings["dataset_path"] = dataset.name
        config.plugin_settings["task"] = "classification"
        config.plugin_settings["target_column"] = "target"
        config.plugin_settings["csv_path"] = dataset.name

        target_dir = tmp_path / "mlforge-smoke"
        target_dir.mkdir()
        run_id = "run-smoke"

        # Initialize git repo before scaffolding (scaffold expects a git repo)
        subprocess.run(["git", "init"], cwd=str(target_dir), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(target_dir), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(target_dir), capture_output=True, check=True)

        scaffold_experiment(
            config=config,
            dataset_path=dataset,
            target_dir=target_dir,
            run_id=run_id,
        )

        # Initial commit so branches work
        subprocess.run(["git", "add", "."], cwd=str(target_dir), capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=str(target_dir), capture_output=True, check=True)

        git = GitManager(target_dir)
        git.create_run_branch(run_id)
        git.close()

        state = SessionState(run_id=run_id, budget_remaining=config.budget_usd)

        return config, target_dir, state

    def test_scaffold_creates_expected_files(self, experiment_setup):
        """Scaffold creates all expected files in the experiment directory."""
        _config, target_dir, _state = experiment_setup

        assert (target_dir / "CLAUDE.md").exists()
        assert (target_dir / "train.py").exists()
        assert (target_dir / "prepare.py").exists()
        assert (target_dir / "experiments.md").exists()
        assert (target_dir / "mlforge.config.toml").exists()

    def test_scaffold_config_is_valid_toml(self, experiment_setup):
        """Scaffolded config file is parseable."""
        import tomllib

        _config, target_dir, _state = experiment_setup
        config_text = (target_dir / "mlforge.config.toml").read_text()
        parsed = tomllib.loads(config_text)
        assert parsed["domain"] == "tabular"

    def test_git_branch_created(self, experiment_setup):
        """Git branch mlforge/run-smoke exists."""
        _config, target_dir, _state = experiment_setup
        from git import Repo

        repo = Repo(target_dir)
        branch_names = [b.name for b in repo.branches]
        assert any(b.startswith("mlforge/") for b in branch_names)

    def test_engine_processes_canned_response(self, experiment_setup):
        """Engine processes a canned claude response (keep decision)."""
        config, target_dir, state = experiment_setup

        canned_response = json.dumps({
            "result": json.dumps({"metric_value": 0.85}),
            "total_cost_usd": 0.05,
        })

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = canned_response
        mock_proc.stderr = ""

        engine = RunEngine(target_dir, config, state)

        with patch("subprocess.run", return_value=mock_proc):
            engine.run()

        assert state.experiment_count == 2  # budget_experiments=2
        assert state.best_metric is not None

    def test_checkpoint_survives_run(self, experiment_setup):
        """Checkpoint file exists after a run."""
        config, target_dir, state = experiment_setup

        canned_response = json.dumps({
            "result": json.dumps({"metric_value": 0.85}),
            "total_cost_usd": 0.05,
        })

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = canned_response
        mock_proc.stderr = ""

        engine = RunEngine(target_dir, config, state)

        with patch("subprocess.run", return_value=mock_proc):
            engine.run()

        checkpoint_path = target_dir / ".mlforge" / "checkpoint.json"
        assert checkpoint_path.exists()
        data = json.loads(checkpoint_path.read_text())
        assert data["state"]["experiment_count"] == 2
