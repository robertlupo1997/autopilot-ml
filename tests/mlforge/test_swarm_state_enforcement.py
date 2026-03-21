"""Tests for swarm state enforcement: _collect_agent_result fallback chain and subprocess capture."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mlforge.config import Config
from mlforge.swarm import SwarmManager


# ---------------------------------------------------------------------------
# _collect_agent_result fallback chain
# ---------------------------------------------------------------------------


class TestCollectAgentResultFallback:
    """_collect_agent_result uses state.json -> checkpoint.json fallback."""

    def _make_manager(self, tmp_path: Path) -> SwarmManager:
        config = Config(metric="accuracy", direction="maximize", budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=2)
        sm._worktree_paths = [
            tmp_path / "agent-0",
            tmp_path / "agent-1",
        ]
        for wt in sm._worktree_paths:
            (wt / ".mlforge").mkdir(parents=True, exist_ok=True)
        return sm

    def test_returns_metric_commit_from_state_json(self, tmp_path: Path) -> None:
        sm = self._make_manager(tmp_path)
        state_path = sm._worktree_paths[0] / ".mlforge" / "state.json"
        state_path.write_text(json.dumps({"best_metric": 0.92, "best_commit": "abc123"}))

        metric, commit = sm._collect_agent_result(0)
        assert metric == pytest.approx(0.92)
        assert commit == "abc123"

    def test_falls_back_to_checkpoint_when_state_missing(self, tmp_path: Path) -> None:
        sm = self._make_manager(tmp_path)
        # No state.json, but checkpoint.json exists
        ckpt_path = sm._worktree_paths[0] / ".mlforge" / "checkpoint.json"
        ckpt_path.write_text(json.dumps({
            "schema_version": 1,
            "state": {"best_metric": 0.85, "best_commit": "def456"},
            "timestamp": "2026-01-01T00:00:00Z",
        }))

        metric, commit = sm._collect_agent_result(0)
        assert metric == pytest.approx(0.85)
        assert commit == "def456"

    def test_falls_back_to_checkpoint_when_state_malformed(self, tmp_path: Path) -> None:
        sm = self._make_manager(tmp_path)
        state_path = sm._worktree_paths[0] / ".mlforge" / "state.json"
        state_path.write_text("not valid json {{{")
        ckpt_path = sm._worktree_paths[0] / ".mlforge" / "checkpoint.json"
        ckpt_path.write_text(json.dumps({
            "schema_version": 1,
            "state": {"best_metric": 0.80, "best_commit": "ghi789"},
            "timestamp": "2026-01-01T00:00:00Z",
        }))

        metric, commit = sm._collect_agent_result(0)
        assert metric == pytest.approx(0.80)
        assert commit == "ghi789"

    def test_returns_none_empty_when_both_missing(self, tmp_path: Path) -> None:
        sm = self._make_manager(tmp_path)
        # No state.json, no checkpoint.json

        metric, commit = sm._collect_agent_result(0)
        assert metric is None
        assert commit == ""

    def test_handles_checkpoint_nested_schema(self, tmp_path: Path) -> None:
        sm = self._make_manager(tmp_path)
        ckpt_path = sm._worktree_paths[1] / ".mlforge" / "checkpoint.json"
        ckpt_path.write_text(json.dumps({
            "schema_version": 1,
            "state": {"best_metric": 0.77, "best_commit": "nest01", "experiment_count": 5},
            "timestamp": "2026-01-01T00:00:00Z",
        }))

        metric, commit = sm._collect_agent_result(1)
        assert metric == pytest.approx(0.77)
        assert commit == "nest01"


# ---------------------------------------------------------------------------
# Subprocess stdout capture
# ---------------------------------------------------------------------------


class TestSubprocessCapture:
    """SwarmManager.run() uses stdout=subprocess.PIPE and writes state.json from output."""

    def test_run_uses_stdout_pipe(self, tmp_path: Path) -> None:
        config = Config(metric="accuracy", direction="maximize", budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=1)
        sm._worktree_paths = [tmp_path / ".swarm" / "agent-0"]
        (sm._worktree_paths[0] / ".mlforge").mkdir(parents=True, exist_ok=True)

        mock_proc = MagicMock()
        mock_proc.wait.return_value = 0
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.read.return_value = b""

        with (
            patch("mlforge.swarm.subprocess.Popen", return_value=mock_proc) as mock_popen,
            patch.object(sm, "create_child_configs", return_value=[config]),
            patch.object(sm, "_build_agent_command", return_value=["echo", "test"]),
            patch.object(sm.scoreboard, "read_best", return_value=(None, "")),
            patch.object(sm.scoreboard, "read_all", return_value=[]),
            patch("mlforge.swarm.verify_best_result", return_value=None),
        ):
            sm.run()

        # Verify subprocess.PIPE was passed for stdout
        call_kwargs = mock_popen.call_args
        assert call_kwargs[1].get("stdout") == subprocess.PIPE or \
               (len(call_kwargs[0]) > 1 and call_kwargs[0][1] == subprocess.PIPE)

    def test_run_writes_state_json_from_subprocess_output(self, tmp_path: Path) -> None:
        config = Config(metric="accuracy", direction="maximize", budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=1)
        wt_path = tmp_path / ".swarm" / "agent-0"
        sm._worktree_paths = [wt_path]
        (wt_path / ".mlforge").mkdir(parents=True, exist_ok=True)

        # Simulate claude -p --output-format json output
        claude_output = json.dumps({
            "type": "result",
            "result": "Done. Final result:\n{\"metric_value\": 0.93, \"best_commit\": \"xyz999\"}",
            "cost_usd": 1.5,
        })

        mock_proc = MagicMock()
        mock_proc.wait.return_value = 0
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.read.return_value = claude_output.encode()

        with (
            patch("mlforge.swarm.subprocess.Popen", return_value=mock_proc),
            patch.object(sm, "create_child_configs", return_value=[config]),
            patch.object(sm, "_build_agent_command", return_value=["echo", "test"]),
            patch.object(sm.scoreboard, "read_best", return_value=(0.93, "agent-0")),
            patch.object(sm.scoreboard, "read_all", return_value=[]),
            patch.object(sm.scoreboard, "publish_result"),
            patch("mlforge.swarm.verify_best_result", return_value=None),
        ):
            sm.run()

        # state.json should have been written from parsed subprocess output
        state_path = wt_path / ".mlforge" / "state.json"
        assert state_path.exists()
        data = json.loads(state_path.read_text())
        assert data["best_metric"] == pytest.approx(0.93)

    def test_budget_split_agents_produce_scoreboard_entries_via_fallback(
        self, tmp_path: Path
    ) -> None:
        """Budget-split child agents produce scoreboard entries even when AI writes no files,
        by falling back to checkpoint.json written by the engine."""
        config = Config(metric="accuracy", direction="maximize", budget_usd=6.0)
        sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=2)
        sm._worktree_paths = [
            tmp_path / ".swarm" / "agent-0",
            tmp_path / ".swarm" / "agent-1",
        ]
        for wt in sm._worktree_paths:
            (wt / ".mlforge").mkdir(parents=True, exist_ok=True)

        # Agent 0: no state.json, no subprocess output, but has checkpoint.json
        (sm._worktree_paths[0] / ".mlforge" / "checkpoint.json").write_text(json.dumps({
            "schema_version": 1,
            "state": {"best_metric": 0.88, "best_commit": "ckpt01"},
            "timestamp": "2026-01-01T00:00:00Z",
        }))
        # Agent 1: no files at all
        # (nothing written)

        mock_proc = MagicMock()
        mock_proc.wait.return_value = 0
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.read.return_value = b""

        with (
            patch("mlforge.swarm.subprocess.Popen", return_value=mock_proc),
            patch.object(sm, "create_child_configs", return_value=[config, config]),
            patch.object(sm, "_build_agent_command", return_value=["echo", "test"]),
            patch.object(sm.scoreboard, "publish_result") as mock_publish,
            patch.object(sm.scoreboard, "read_best", return_value=(0.88, "agent-0")),
            patch.object(sm.scoreboard, "read_all", return_value=[]),
            patch("mlforge.swarm.verify_best_result", return_value=None),
        ):
            sm.run()

        # Agent 0 should have published via checkpoint fallback, agent 1 should not
        assert mock_publish.call_count == 1
        call_args = mock_publish.call_args
        assert call_args[1]["agent"] == "agent-0" or call_args[0][0] == "agent-0"
