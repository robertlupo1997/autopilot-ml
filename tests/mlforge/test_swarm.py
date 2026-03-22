"""Tests for SwarmManager, budget inheritance, verifier, and swarm_claude.md.j2 template."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mlforge.config import Config
from mlforge.swarm import SwarmManager
from mlforge.swarm.scoreboard import SwarmScoreboard
from mlforge.swarm.verifier import verify_best_result
from mlforge.templates import get_template_env

# ---------------------------------------------------------------------------
# SwarmManager init
# ---------------------------------------------------------------------------

class TestSwarmManagerInit:
    def test_accepts_config_n_agents_experiment_dir(self, tmp_path: Path) -> None:
        config = Config(metric="accuracy", direction="maximize", budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=3)
        assert sm.config is config
        assert sm.n_agents == 3
        assert sm.experiment_dir == tmp_path

    def test_creates_scoreboard_with_correct_direction(self, tmp_path: Path) -> None:
        config = Config(direction="minimize")
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=2)
        assert sm.scoreboard.direction == "minimize"


# ---------------------------------------------------------------------------
# Budget inheritance
# ---------------------------------------------------------------------------

class TestBudgetInheritance:
    def test_splits_budget_evenly_3_agents(self, tmp_path: Path) -> None:
        config = Config(budget_usd=6.0, budget_minutes=30, budget_experiments=15)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=3)
        children = sm.create_child_configs()
        assert len(children) == 3
        for child in children:
            assert child.budget_usd == pytest.approx(2.0)
            assert child.budget_minutes == 10
            assert child.budget_experiments == 5

    def test_splits_budget_evenly_5_agents(self, tmp_path: Path) -> None:
        config = Config(budget_usd=10.0, budget_minutes=50, budget_experiments=25)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=5)
        children = sm.create_child_configs()
        assert len(children) == 5
        for child in children:
            assert child.budget_usd == pytest.approx(2.0)
            assert child.budget_minutes == 10
            assert child.budget_experiments == 5

    def test_child_inherits_domain_metric_direction(self, tmp_path: Path) -> None:
        config = Config(domain="tabular", metric="f1", direction="maximize", budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=3)
        children = sm.create_child_configs()
        for child in children:
            assert child.domain == "tabular"
            assert child.metric == "f1"
            assert child.direction == "maximize"

    def test_child_inherits_per_experiment_settings(self, tmp_path: Path) -> None:
        config = Config(
            per_experiment_timeout_sec=120,
            per_experiment_budget_usd=0.5,
            max_turns_per_experiment=20,
            budget_usd=6.0,
        )
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=3)
        children = sm.create_child_configs()
        for child in children:
            assert child.per_experiment_timeout_sec == 120
            assert child.per_experiment_budget_usd == 0.5
            assert child.max_turns_per_experiment == 20

    def test_child_inherits_plugin_settings(self, tmp_path: Path) -> None:
        config = Config(plugin_settings={"key": "value"}, budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=3)
        children = sm.create_child_configs()
        for child in children:
            assert child.plugin_settings == {"key": "value"}

    def test_child_has_no_swarm_capability(self, tmp_path: Path) -> None:
        """Children must not recursively spawn sub-swarms."""
        config = Config(budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=3)
        children = sm.create_child_configs()
        for child in children:
            # Children are plain Config -- no swarm attributes
            assert not hasattr(child, "swarm_enabled")
            assert not hasattr(child, "n_agents")


# ---------------------------------------------------------------------------
# Setup and teardown
# ---------------------------------------------------------------------------

class TestSetupTeardown:
    def test_setup_creates_swarm_dir_and_worktrees(self, tmp_path: Path) -> None:
        config = Config(budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=3)
        mock_repo = MagicMock()
        with patch.object(sm, "_get_repo", return_value=mock_repo):
            paths = sm.setup()
        assert len(paths) == 3
        assert (tmp_path / ".swarm").exists()
        assert mock_repo.git.worktree.call_count == 3

    def test_setup_calls_worktree_add_for_each_agent(self, tmp_path: Path) -> None:
        config = Config(budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=2)
        mock_repo = MagicMock()
        with patch.object(sm, "_get_repo", return_value=mock_repo):
            sm.setup()
        calls = mock_repo.git.worktree.call_args_list
        assert len(calls) == 2
        # Each call should have "add" as first arg
        for call in calls:
            assert call[0][0] == "add"

    def test_teardown_removes_worktrees(self, tmp_path: Path) -> None:
        config = Config(budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=2)
        mock_repo = MagicMock()
        # Simulate setup having created worktree paths
        sm._worktree_paths = [
            tmp_path / ".swarm" / "agent-0",
            tmp_path / ".swarm" / "agent-1",
        ]
        with patch.object(sm, "_get_repo", return_value=mock_repo):
            sm.teardown()
        # Should have called worktree remove for each + prune
        remove_calls = [c for c in mock_repo.git.worktree.call_args_list if c[0][0] == "remove"]
        assert len(remove_calls) == 2

    def test_teardown_handles_already_removed_worktrees(self, tmp_path: Path) -> None:
        """Crash recovery: some worktrees may already be gone."""
        config = Config(budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=2)
        sm._worktree_paths = [
            tmp_path / ".swarm" / "agent-0",
            tmp_path / ".swarm" / "agent-1",
        ]
        mock_repo = MagicMock()
        # First remove succeeds, second raises (already gone)
        from git import GitCommandError
        mock_repo.git.worktree.side_effect = [
            None,  # remove agent-0
            GitCommandError("worktree remove", "not a worktree"),  # remove agent-1
            None,  # prune
        ]
        with patch.object(sm, "_get_repo", return_value=mock_repo):
            sm.teardown()  # Should not raise


# ---------------------------------------------------------------------------
# _build_agent_command
# ---------------------------------------------------------------------------

class TestBuildAgentCommand:
    def test_produces_claude_command(self, tmp_path: Path) -> None:
        config = Config(
            metric="accuracy", direction="maximize",
            budget_usd=6.0, budget_minutes=30, budget_experiments=15,
        )
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=3)
        sm._worktree_paths = [tmp_path / ".swarm" / f"agent-{i}" for i in range(3)]
        child_configs = sm.create_child_configs()
        cmd = sm._build_agent_command(0, child_configs[0])
        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert "--cwd" not in cmd

    def test_renders_swarm_template_in_prompt(self, tmp_path: Path) -> None:
        config = Config(
            metric="accuracy", direction="maximize",
            budget_usd=6.0, budget_minutes=30, budget_experiments=15,
        )
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=3)
        sm._worktree_paths = [tmp_path / ".swarm" / f"agent-{i}" for i in range(3)]
        child_configs = sm.create_child_configs()
        cmd = sm._build_agent_command(0, child_configs[0])
        # Find the prompt argument (after -p)
        prompt_idx = cmd.index("-p") + 1
        prompt = cmd[prompt_idx]
        assert "agent-0" in prompt
        assert "accuracy" in prompt
        assert "maximize" in prompt


# ---------------------------------------------------------------------------
# swarm_claude.md.j2 template rendering
# ---------------------------------------------------------------------------

class TestSwarmTemplate:
    def test_renders_with_required_variables(self) -> None:
        env = get_template_env()
        template = env.get_template("swarm_claude.md.j2")
        rendered = template.render(
            agent_id="agent-2",
            scoreboard_path="/tmp/scoreboard.tsv",
            metric="f1",
            direction="maximize",
            budget_usd=2.0,
            budget_minutes=10,
            budget_experiments=5,
        )
        assert "agent-2" in rendered
        assert "/tmp/scoreboard.tsv" in rendered
        assert "f1" in rendered
        assert "maximize" in rendered
        assert "2.0" in rendered


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

class TestVerifier:
    def test_returns_match_true_when_metrics_close(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv", direction="maximize")
        sb.publish_result("agent-0", "abc123", 0.95, 10.0, "keep", "best model")

        eval_output = json.dumps({"metric_value": 0.9501})
        with patch("mlforge.swarm.verifier.subprocess") as mock_sub:
            mock_proc = MagicMock()
            mock_proc.stdout = eval_output
            mock_proc.returncode = 0
            mock_sub.run.return_value = mock_proc
            with patch("mlforge.swarm.verifier._checkout_in_worktree"):
                with patch("mlforge.swarm.verifier._cleanup_worktree"):
                    result = verify_best_result(tmp_path, sb)

        assert result["match"] is True
        assert result["claimed_metric"] == pytest.approx(0.95)
        assert result["agent"] == "agent-0"

    def test_returns_match_false_when_metrics_diverge(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv", direction="maximize")
        sb.publish_result("agent-0", "abc123", 0.95, 10.0, "keep", "best model")

        eval_output = json.dumps({"metric_value": 0.80})
        with patch("mlforge.swarm.verifier.subprocess") as mock_sub:
            mock_proc = MagicMock()
            mock_proc.stdout = eval_output
            mock_proc.returncode = 0
            mock_sub.run.return_value = mock_proc
            with patch("mlforge.swarm.verifier._checkout_in_worktree"):
                with patch("mlforge.swarm.verifier._cleanup_worktree"):
                    result = verify_best_result(tmp_path, sb)

        assert result["match"] is False
        assert result["verified_metric"] == pytest.approx(0.80)

    def test_returns_none_when_no_results(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv", direction="maximize")
        result = verify_best_result(tmp_path, sb)
        assert result is None


# ---------------------------------------------------------------------------
# Verifier wiring in SwarmManager.run()
# ---------------------------------------------------------------------------

class TestVerifierWiringInRun:
    """SwarmManager.run() calls verify_best_result and includes result in return dict."""

    def test_run_returns_verification_key(self, tmp_path: Path) -> None:
        config = Config(metric="accuracy", direction="maximize", budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=1)
        sm._worktree_paths = [tmp_path / ".swarm" / "agent-0"]
        (sm._worktree_paths[0] / ".mlforge").mkdir(parents=True, exist_ok=True)

        mock_proc = MagicMock()
        mock_proc.wait.return_value = 0
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.read.return_value = b""

        with (
            patch("mlforge.swarm.subprocess.Popen", return_value=mock_proc),
            patch.object(sm, "create_child_configs", return_value=[config]),
            patch.object(sm, "_build_agent_command", return_value=["echo", "test"]),
            patch.object(sm.scoreboard, "read_best", return_value=(0.95, "agent-0")),
            patch.object(sm.scoreboard, "read_all", return_value=[]),
            patch("mlforge.swarm.verify_best_result", return_value={"match": True}),
        ):
            result = sm.run()
        assert "verification" in result

class TestPublishResultWiring:
    """publish_result() is called after agent completion in SwarmManager.run()."""

    def test_publish_result_called_after_agent(self, tmp_path: Path) -> None:
        config = Config(metric="accuracy", direction="maximize", budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=1)
        sm._worktree_paths = [tmp_path / ".swarm" / "agent-0"]

        # Create a state.json the agent would leave behind
        state_dir = sm._worktree_paths[0] / ".mlforge"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "state.json").write_text(json.dumps({
            "best_metric": 0.92,
            "best_commit": "abc123",
        }))

        mock_proc = MagicMock()
        mock_proc.wait.return_value = 0
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.read.return_value = b""

        with (
            patch("mlforge.swarm.subprocess.Popen", return_value=mock_proc),
            patch.object(sm, "create_child_configs", return_value=[config]),
            patch.object(sm, "_build_agent_command", return_value=["echo", "test"]),
            patch.object(sm.scoreboard, "publish_result") as mock_publish,
            patch.object(sm.scoreboard, "read_best", return_value=(0.92, "agent-0")),
            patch.object(sm.scoreboard, "read_all", return_value=[]),
            patch("mlforge.swarm.verify_best_result", return_value=None),
        ):
            sm.run()
            mock_publish.assert_called_once()
            call_kwargs = mock_publish.call_args
            assert call_kwargs[1]["agent"] == "agent-0" or call_kwargs[0][0] == "agent-0"

    def test_scoreboard_populated_after_swarm(self, tmp_path: Path) -> None:
        config = Config(metric="accuracy", direction="maximize", budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=2)
        sm._worktree_paths = [
            tmp_path / ".swarm" / "agent-0",
            tmp_path / ".swarm" / "agent-1",
        ]

        # Create state.json for each agent
        for i, wt in enumerate(sm._worktree_paths):
            state_dir = wt / ".mlforge"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "state.json").write_text(json.dumps({
                "best_metric": 0.90 + i * 0.05,
                "best_commit": f"commit-{i}",
            }))

        mock_proc = MagicMock()
        mock_proc.wait.return_value = 0
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.read.return_value = b""

        with (
            patch("mlforge.swarm.subprocess.Popen", return_value=mock_proc),
            patch.object(sm, "create_child_configs", return_value=[config, config]),
            patch.object(sm, "_build_agent_command", return_value=["echo", "test"]),
            patch.object(sm.scoreboard, "publish_result") as mock_publish,
            patch.object(sm.scoreboard, "read_best", return_value=(0.95, "agent-1")),
            patch.object(sm.scoreboard, "read_all", return_value=[]),
            patch("mlforge.swarm.verify_best_result", return_value=None),
        ):
            sm.run()
            assert mock_publish.call_count == 2


    def test_run_calls_verify_best_result(self, tmp_path: Path) -> None:
        config = Config(metric="accuracy", direction="maximize", budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=1)
        sm._worktree_paths = [tmp_path / ".swarm" / "agent-0"]
        (sm._worktree_paths[0] / ".mlforge").mkdir(parents=True, exist_ok=True)

        mock_proc = MagicMock()
        mock_proc.wait.return_value = 0
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.read.return_value = b""

        mock_verify = MagicMock(return_value={"match": True, "claimed_metric": 0.95})

        with (
            patch("mlforge.swarm.subprocess.Popen", return_value=mock_proc),
            patch.object(sm, "create_child_configs", return_value=[config]),
            patch.object(sm, "_build_agent_command", return_value=["echo", "test"]),
            patch.object(sm.scoreboard, "read_best", return_value=(0.95, "agent-0")),
            patch.object(sm.scoreboard, "read_all", return_value=[]),
            patch("mlforge.swarm.verify_best_result", new=mock_verify),
        ):
            sm.run()
        # verify_best_result should have been called with experiment_dir and scoreboard
        mock_verify.assert_called_once_with(tmp_path, sm.scoreboard)


class TestVerifierDefaultEvalScript:
    """verify_best_result default eval_script is 'python train.py' (no --eval-only)."""

    def test_verify_default_eval_script(self) -> None:
        import inspect

        sig = inspect.signature(verify_best_result)
        default = sig.parameters["eval_script"].default
        assert default == "python train.py"
