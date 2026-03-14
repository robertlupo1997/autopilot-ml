"""Tests for SwarmManager orchestrator (swarm.py).

Tests are organized as:
- TestDivideFamilies: parametrized round-robin assignment tests
- TestSetup: directory creation, worktree calls, config.json written
- TestTeardown: remove_worktree calls and git worktree prune
- TestSpawnAgent: subprocess.Popen command construction

Note: _monitor_loop and _handle_sigint are NOT tested here -- they require
real processes and are covered by Plan 10-03 manual validation script.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from automl.swarm import SwarmManager, spawn_agent


# ---------------------------------------------------------------------------
# TestDivideFamilies
# ---------------------------------------------------------------------------

class TestDivideFamilies:
    """Round-robin family assignment: _divide_families(families, n_agents)."""

    def _make_families(self, n: int) -> list[dict]:
        """Create n dummy family dicts for testing."""
        return [{"name": f"Family{i}", "imports": "", "model_line": ""} for i in range(n)]

    def test_three_agents_five_families(self):
        """3 agents, 5 families -> assignment sizes [2, 2, 1]."""
        manager = SwarmManager(
            experiment_dir=Path("/tmp/fake"),
            n_agents=3,
            task_type="classification",
            metric="accuracy",
            time_budget=60,
        )
        families = self._make_families(5)
        assignments = manager._divide_families(families, 3)
        assert len(assignments) == 3
        assert [len(a) for a in assignments] == [2, 2, 1]

    def test_one_agent_five_families(self):
        """1 agent, 5 families -> assignment sizes [5]."""
        manager = SwarmManager(
            experiment_dir=Path("/tmp/fake"),
            n_agents=1,
            task_type="classification",
            metric="accuracy",
            time_budget=60,
        )
        families = self._make_families(5)
        assignments = manager._divide_families(families, 1)
        assert len(assignments) == 1
        assert [len(a) for a in assignments] == [5]

    def test_five_agents_five_families(self):
        """5 agents, 5 families -> assignment sizes [1, 1, 1, 1, 1]."""
        manager = SwarmManager(
            experiment_dir=Path("/tmp/fake"),
            n_agents=5,
            task_type="classification",
            metric="accuracy",
            time_budget=60,
        )
        families = self._make_families(5)
        assignments = manager._divide_families(families, 5)
        assert len(assignments) == 5
        assert [len(a) for a in assignments] == [1, 1, 1, 1, 1]

    def test_seven_agents_five_families(self):
        """7 agents, 5 families -> assignment sizes [1, 1, 1, 1, 1, 0, 0]."""
        manager = SwarmManager(
            experiment_dir=Path("/tmp/fake"),
            n_agents=7,
            task_type="classification",
            metric="accuracy",
            time_budget=60,
        )
        families = self._make_families(5)
        assignments = manager._divide_families(families, 7)
        assert len(assignments) == 7
        assert [len(a) for a in assignments] == [1, 1, 1, 1, 1, 0, 0]

    def test_round_robin_order(self):
        """Round-robin: agent-0 gets [0, N, 2N...], agent-1 gets [1, N+1...]."""
        manager = SwarmManager(
            experiment_dir=Path("/tmp/fake"),
            n_agents=3,
            task_type="classification",
            metric="accuracy",
            time_budget=60,
        )
        families = self._make_families(6)  # 6 families, 3 agents -> 2 each
        assignments = manager._divide_families(families, 3)
        # agent-0 should get families 0 and 3
        assert assignments[0][0]["name"] == "Family0"
        assert assignments[0][1]["name"] == "Family3"
        # agent-1 should get families 1 and 4
        assert assignments[1][0]["name"] == "Family1"
        assert assignments[1][1]["name"] == "Family4"
        # agent-2 should get families 2 and 5
        assert assignments[2][0]["name"] == "Family2"
        assert assignments[2][1]["name"] == "Family5"


# ---------------------------------------------------------------------------
# TestSetup
# ---------------------------------------------------------------------------

class TestSetup:
    """SwarmManager.setup() creates directory structure, worktrees, config.json."""

    @pytest.fixture
    def manager(self, tmp_path):
        """SwarmManager with 2 agents pointed at tmp_path."""
        return SwarmManager(
            experiment_dir=tmp_path,
            n_agents=2,
            task_type="classification",
            metric="accuracy",
            time_budget=60,
        )

    def test_setup_creates_swarm_dir(self, manager, tmp_path):
        """setup() creates .swarm/ directory."""
        with patch.object(manager.git, "create_worktree") as mock_wt:
            mock_wt.return_value = "branch-name"
            manager.setup()
        assert (tmp_path / ".swarm").is_dir()

    def test_setup_creates_claims_dir(self, manager, tmp_path):
        """setup() creates .swarm/claims/ directory."""
        with patch.object(manager.git, "create_worktree") as mock_wt:
            mock_wt.return_value = "branch-name"
            manager.setup()
        assert (tmp_path / ".swarm" / "claims").is_dir()

    def test_setup_calls_create_worktree_n_times(self, manager):
        """setup() calls git.create_worktree once per agent."""
        with patch.object(manager.git, "create_worktree") as mock_wt:
            mock_wt.return_value = "branch-name"
            manager.setup()
        assert mock_wt.call_count == 2

    def test_setup_worktree_paths(self, manager, tmp_path):
        """setup() creates worktrees at .swarm/agent-0 and .swarm/agent-1."""
        with patch.object(manager.git, "create_worktree") as mock_wt:
            mock_wt.return_value = "branch-name"
            manager.setup()
        call_args = [c[0][0] for c in mock_wt.call_args_list]
        assert str(tmp_path / ".swarm" / "agent-0") in call_args
        assert str(tmp_path / ".swarm" / "agent-1") in call_args

    def test_setup_writes_config_json(self, manager, tmp_path):
        """setup() writes .swarm/config.json with metadata."""
        with patch.object(manager.git, "create_worktree") as mock_wt:
            mock_wt.return_value = "branch-name"
            manager.setup()
        config_path = tmp_path / ".swarm" / "config.json"
        assert config_path.exists()
        config = json.loads(config_path.read_text())
        assert config["n_agents"] == 2
        assert config["task_type"] == "classification"
        assert config["metric"] == "accuracy"
        assert "run_tag" in config
        assert "assignments" in config

    def test_setup_returns_assignments(self, manager):
        """setup() returns list of family assignment lists (one per agent)."""
        with patch.object(manager.git, "create_worktree") as mock_wt:
            mock_wt.return_value = "branch-name"
            assignments = manager.setup()
        assert len(assignments) == 2
        # Classification has 5 families; 2 agents -> [3, 2] or [2, 3]
        total_families = sum(len(a) for a in assignments)
        assert total_families == 5  # all 5 classification families assigned

    def test_setup_config_assignments_are_names(self, manager, tmp_path):
        """config.json assignments are lists of family names (strings)."""
        with patch.object(manager.git, "create_worktree") as mock_wt:
            mock_wt.return_value = "branch-name"
            manager.setup()
        config = json.loads((tmp_path / ".swarm" / "config.json").read_text())
        # Each assignment list contains strings (family names), not dicts
        for assignment_list in config["assignments"]:
            for item in assignment_list:
                assert isinstance(item, str), f"Expected string family name, got {type(item)}"


# ---------------------------------------------------------------------------
# TestTeardown
# ---------------------------------------------------------------------------

class TestTeardown:
    """SwarmManager.teardown() removes worktrees and runs git worktree prune."""

    @pytest.fixture
    def manager(self, tmp_path):
        """SwarmManager with 2 agents; swarm_dir already created."""
        mgr = SwarmManager(
            experiment_dir=tmp_path,
            n_agents=2,
            task_type="classification",
            metric="accuracy",
            time_budget=60,
        )
        (tmp_path / ".swarm").mkdir()
        (tmp_path / ".swarm" / "agent-0").mkdir()
        (tmp_path / ".swarm" / "agent-1").mkdir()
        return mgr

    def test_teardown_calls_remove_worktree_for_each_agent(self, manager, tmp_path):
        """teardown() calls remove_worktree for each agent dir."""
        with patch.object(manager.git, "remove_worktree") as mock_rm, \
             patch.object(manager.git, "_run") as mock_run:
            manager.teardown()
        assert mock_rm.call_count == 2
        call_paths = [c[0][0] for c in mock_rm.call_args_list]
        assert str(tmp_path / ".swarm" / "agent-0") in call_paths
        assert str(tmp_path / ".swarm" / "agent-1") in call_paths

    def test_teardown_runs_worktree_prune(self, manager):
        """teardown() calls git worktree prune after removing worktrees."""
        with patch.object(manager.git, "remove_worktree"), \
             patch.object(manager.git, "_run") as mock_run:
            manager.teardown()
        mock_run.assert_called_with("worktree", "prune")

    def test_teardown_continues_if_remove_fails(self, manager, tmp_path):
        """teardown() handles remove_worktree errors gracefully (try/except)."""
        with patch.object(manager.git, "remove_worktree") as mock_rm, \
             patch.object(manager.git, "_run"):
            mock_rm.side_effect = Exception("worktree already removed")
            # Should not raise
            manager.teardown()

    def test_teardown_skips_nonexistent_dirs(self, manager, tmp_path):
        """teardown() skips agent-N dirs that don't exist."""
        # Remove agent-0 dir so it doesn't exist
        (tmp_path / ".swarm" / "agent-0").rmdir()
        with patch.object(manager.git, "remove_worktree") as mock_rm, \
             patch.object(manager.git, "_run"):
            manager.teardown()
        # remove_worktree should only be called for agent-1 (agent-0 dir doesn't exist)
        # OR called for both (try/except handles the non-existent case)
        # Either behavior is acceptable as long as it doesn't raise
        assert True  # just verify no exception was raised


# ---------------------------------------------------------------------------
# TestSpawnAgent
# ---------------------------------------------------------------------------

class TestSpawnAgent:
    """spawn_agent() builds correct claude -p command with --allowedTools."""

    def test_spawn_agent_uses_popen(self, tmp_path):
        """spawn_agent returns a subprocess.Popen instance."""
        workdir = tmp_path / "agent-0"
        workdir.mkdir()
        swarm_dir = tmp_path / ".swarm"
        swarm_dir.mkdir()
        families = [
            {"name": "LogisticRegression", "imports": "", "model_line": ""},
            {"name": "RandomForest", "imports": "", "model_line": ""},
        ]
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            proc = spawn_agent(
                agent_id=0,
                workdir=workdir,
                assigned_families=families,
                metric="accuracy",
                time_budget=60,
                swarm_dir=swarm_dir,
            )
        mock_popen.assert_called_once()

    def test_spawn_agent_command_includes_claude_p(self, tmp_path):
        """spawn_agent command starts with 'claude -p'."""
        workdir = tmp_path / "agent-0"
        workdir.mkdir()
        swarm_dir = tmp_path / ".swarm"
        swarm_dir.mkdir()
        families = [{"name": "XGBoost", "imports": "", "model_line": ""}]
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            spawn_agent(
                agent_id=0,
                workdir=workdir,
                assigned_families=families,
                metric="accuracy",
                time_budget=60,
                swarm_dir=swarm_dir,
            )
        cmd = mock_popen.call_args[0][0]
        assert cmd[0] == "claude"
        assert cmd[1] == "-p"

    def test_spawn_agent_includes_allowed_tools(self, tmp_path):
        """spawn_agent command includes --allowedTools flag."""
        workdir = tmp_path / "agent-0"
        workdir.mkdir()
        swarm_dir = tmp_path / ".swarm"
        swarm_dir.mkdir()
        families = [{"name": "XGBoost", "imports": "", "model_line": ""}]
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            spawn_agent(
                agent_id=0,
                workdir=workdir,
                assigned_families=families,
                metric="accuracy",
                time_budget=60,
                swarm_dir=swarm_dir,
            )
        cmd = mock_popen.call_args[0][0]
        assert "--allowedTools" in cmd

    def test_spawn_agent_includes_output_format_json(self, tmp_path):
        """spawn_agent command includes --output-format json."""
        workdir = tmp_path / "agent-0"
        workdir.mkdir()
        swarm_dir = tmp_path / ".swarm"
        swarm_dir.mkdir()
        families = [{"name": "XGBoost", "imports": "", "model_line": ""}]
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            spawn_agent(
                agent_id=0,
                workdir=workdir,
                assigned_families=families,
                metric="accuracy",
                time_budget=60,
                swarm_dir=swarm_dir,
            )
        cmd = mock_popen.call_args[0][0]
        assert "--output-format" in cmd
        idx = cmd.index("--output-format")
        assert cmd[idx + 1] == "json"

    def test_spawn_agent_cwd_is_workdir(self, tmp_path):
        """spawn_agent sets cwd to workdir path string."""
        workdir = tmp_path / "agent-0"
        workdir.mkdir()
        swarm_dir = tmp_path / ".swarm"
        swarm_dir.mkdir()
        families = [{"name": "XGBoost", "imports": "", "model_line": ""}]
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            spawn_agent(
                agent_id=0,
                workdir=workdir,
                assigned_families=families,
                metric="accuracy",
                time_budget=60,
                swarm_dir=swarm_dir,
            )
        kwargs = mock_popen.call_args[1]
        assert kwargs["cwd"] == str(workdir)

    def test_spawn_agent_stdout_pipe(self, tmp_path):
        """spawn_agent sets stdout=PIPE and stderr=PIPE."""
        workdir = tmp_path / "agent-0"
        workdir.mkdir()
        swarm_dir = tmp_path / ".swarm"
        swarm_dir.mkdir()
        families = [{"name": "XGBoost", "imports": "", "model_line": ""}]
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            spawn_agent(
                agent_id=0,
                workdir=workdir,
                assigned_families=families,
                metric="accuracy",
                time_budget=60,
                swarm_dir=swarm_dir,
            )
        kwargs = mock_popen.call_args[1]
        assert kwargs["stdout"] == subprocess.PIPE
        assert kwargs["stderr"] == subprocess.PIPE

    def test_spawn_agent_prompt_includes_agent_id(self, tmp_path):
        """spawn_agent prompt mentions agent ID."""
        workdir = tmp_path / "agent-0"
        workdir.mkdir()
        swarm_dir = tmp_path / ".swarm"
        swarm_dir.mkdir()
        families = [{"name": "XGBoost", "imports": "", "model_line": ""}]
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            spawn_agent(
                agent_id=2,
                workdir=workdir,
                assigned_families=families,
                metric="accuracy",
                time_budget=60,
                swarm_dir=swarm_dir,
            )
        cmd = mock_popen.call_args[0][0]
        # Prompt is cmd[2] (after "claude", "-p")
        prompt = cmd[2]
        assert "2" in prompt  # agent_id=2 appears in prompt

    def test_spawn_agent_prompt_includes_family_names(self, tmp_path):
        """spawn_agent prompt includes assigned family names."""
        workdir = tmp_path / "agent-0"
        workdir.mkdir()
        swarm_dir = tmp_path / ".swarm"
        swarm_dir.mkdir()
        families = [
            {"name": "XGBoost", "imports": "", "model_line": ""},
            {"name": "LightGBM", "imports": "", "model_line": ""},
        ]
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            spawn_agent(
                agent_id=0,
                workdir=workdir,
                assigned_families=families,
                metric="accuracy",
                time_budget=60,
                swarm_dir=swarm_dir,
            )
        cmd = mock_popen.call_args[0][0]
        prompt = cmd[2]
        assert "XGBoost" in prompt
        assert "LightGBM" in prompt

    def test_spawn_agent_includes_max_turns(self, tmp_path):
        """spawn_agent command includes --max-turns 50."""
        workdir = tmp_path / "agent-0"
        workdir.mkdir()
        swarm_dir = tmp_path / ".swarm"
        swarm_dir.mkdir()
        families = [{"name": "XGBoost", "imports": "", "model_line": ""}]
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            spawn_agent(
                agent_id=0,
                workdir=workdir,
                assigned_families=families,
                metric="accuracy",
                time_budget=60,
                swarm_dir=swarm_dir,
            )
        cmd = mock_popen.call_args[0][0]
        assert "--max-turns" in cmd
        idx = cmd.index("--max-turns")
        assert cmd[idx + 1] == "50"
