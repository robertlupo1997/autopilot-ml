"""Tests for mlforge.engine -- RunEngine experiment loop."""

from __future__ import annotations

import json
import signal
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from mlforge.config import Config
from mlforge.state import SessionState


def _make_claude_response(
    metric_value: float | None = 0.85,
    total_cost_usd: float = 0.10,
    status: str = "ok",
    error: str = "",
) -> dict:
    """Build a mock claude -p JSON response."""
    resp = {
        "result": "",
        "total_cost_usd": total_cost_usd,
    }
    if status == "ok":
        resp["result"] = json.dumps({"metric_value": metric_value})
    if error:
        resp["error"] = error
    return resp


class TestRunEngineInit:
    """RunEngine.__init__ creates all components."""

    def test_creates_git_manager(self, tmp_path):
        from mlforge.engine import RunEngine

        # Need a git repo
        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)
        assert engine.git is not None
        engine.git.close()

    def test_creates_guardrails(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)
        assert engine.guardrails is not None
        engine.git.close()

    def test_creates_cost_tracker(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)
        assert engine.cost_tracker is not None
        engine.git.close()

    def test_creates_deviation_handler(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)
        assert engine.deviation is not None
        engine.git.close()

    def test_creates_progress(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)
        assert engine.progress is not None
        engine.git.close()


class TestRunOneExperiment:
    """_run_one_experiment subprocess integration."""

    def test_returns_crash_on_nonzero_returncode(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = engine._run_one_experiment()
        assert result["status"] == "crash"
        engine.git.close()

    def test_returns_timeout_on_timeout_expired(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 300)):
            result = engine._run_one_experiment()
        assert result["status"] == "timeout"
        engine.git.close()

    def test_returns_crash_on_json_decode_error(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "NOT VALID JSON"

        with patch("subprocess.run", return_value=mock_result):
            result = engine._run_one_experiment()
        assert result["status"] == "crash"
        engine.git.close()

    def test_returns_parsed_json_on_success(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": json.dumps({"metric_value": 0.95}),
            "total_cost_usd": 0.15,
        })

        with patch("subprocess.run", return_value=mock_result):
            result = engine._run_one_experiment()
        assert result["total_cost_usd"] == 0.15
        engine.git.close()

    def test_passes_model_flag_when_set(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(model="sonnet")
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": json.dumps({"metric_value": 0.9}),
            "total_cost_usd": 0.1,
        })

        with patch("subprocess.run", return_value=mock_result) as mock_sub:
            engine._run_one_experiment()
            cmd = mock_sub.call_args[0][0]
            assert "--model" in cmd
            assert "sonnet" in cmd
        engine.git.close()

    def test_no_model_flag_when_not_set(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(model=None)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": json.dumps({"metric_value": 0.9}),
            "total_cost_usd": 0.1,
        })

        with patch("subprocess.run", return_value=mock_result) as mock_sub:
            engine._run_one_experiment()
            cmd = mock_sub.call_args[0][0]
            assert "--model" not in cmd
        engine.git.close()


class TestProcessResult:
    """_process_result routes through DeviationHandler."""

    def test_keep_updates_state(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        result = {"metric_value": 0.9, "total_cost_usd": 0.1, "status": "ok"}

        with patch.object(engine.git, "commit_experiment", return_value="abc12345"):
            action = engine._process_result(result)

        assert action == "keep"
        assert state.total_keeps == 1
        assert state.best_metric == 0.9
        assert state.best_commit == "abc12345"
        assert state.consecutive_reverts == 0
        engine.git.close()

    def test_revert_updates_state(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState(best_metric=0.95)  # Already have a good metric
        engine = RunEngine(tmp_path, config, state)

        result = {"metric_value": 0.8, "total_cost_usd": 0.1, "status": "ok"}

        with patch.object(engine.git, "revert_to_last_commit"):
            action = engine._process_result(result)

        assert action == "revert"
        assert state.total_reverts == 1
        assert state.consecutive_reverts == 1
        engine.git.close()

    def test_cost_tracked(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        result = {"metric_value": 0.9, "total_cost_usd": 0.25, "status": "ok"}

        with patch.object(engine.git, "commit_experiment", return_value="abc12345"):
            engine._process_result(result)

        assert engine.cost_tracker.total_cost == 0.25
        assert state.cost_spent_usd == 0.25
        engine.git.close()

    def test_retry_on_oom(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        # OOM crash triggers retry which calls _run_one_experiment again.
        # Mock the recursive call to return a successful result on retry.
        oom_result = {"status": "crash", "error": "MemoryError", "total_cost_usd": 0.05}
        success_result = {"metric_value": 0.9, "total_cost_usd": 0.1, "status": "ok"}

        with (
            patch.object(engine, "_run_one_experiment", return_value=success_result),
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
        ):
            action = engine._process_result(oom_result)

        # The retry succeeded -> "keep"
        assert action == "keep"
        engine.git.close()

    def test_stop_on_repeated_oom(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        # Exhaust retries: 2 OOM retries via deviation handler, then stop
        oom_result = {"status": "crash", "error": "OOM", "total_cost_usd": 0.01}

        with patch.object(engine, "_run_one_experiment", return_value=oom_result):
            action = engine._process_result(oom_result)
        assert action == "stop"
        engine.git.close()


class TestRunLoop:
    """RunEngine.run() orchestrates the full loop."""

    def test_stops_when_guardrails_trip(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(budget_experiments=2)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": json.dumps({"metric_value": 0.9}),
            "total_cost_usd": 0.1,
        })

        with (
            patch("subprocess.run", return_value=mock_result),
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
            patch.object(engine.git, "revert_to_last_commit"),
            patch.object(engine.progress, "start"),
            patch.object(engine.progress, "stop"),
            patch.object(engine.progress, "update"),
        ):
            engine.run()

        assert state.experiment_count == 2
        engine.git.close()

    def test_saves_checkpoint_before_each_experiment(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(budget_experiments=2)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": json.dumps({"metric_value": 0.9}),
            "total_cost_usd": 0.1,
        })

        with (
            patch("subprocess.run", return_value=mock_result),
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
            patch.object(engine.progress, "start"),
            patch.object(engine.progress, "stop"),
            patch.object(engine.progress, "update"),
            patch("mlforge.engine.save_checkpoint") as mock_save,
        ):
            engine.run()

        # save_checkpoint called before each experiment + once in finally
        assert mock_save.call_count >= 3  # 2 before experiments + 1 in finally

    def test_stop_action_breaks_loop(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(budget_experiments=10)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        # Mock _run_one_experiment to always return OOM crash.
        # The deviation handler will retry up to MAX_RETRIES=2 then stop.
        oom_result = {"status": "crash", "error": "OOM", "total_cost_usd": 0.01}

        with (
            patch.object(engine, "_run_one_experiment", return_value=oom_result),
            patch.object(engine.progress, "start"),
            patch.object(engine.progress, "stop"),
            patch.object(engine.progress, "update"),
        ):
            engine.run()

        # Should stop well before budget_experiments=10
        assert state.experiment_count < 10
        engine.git.close()

    def test_cost_accumulates_across_experiments(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(budget_experiments=3)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": json.dumps({"metric_value": 0.9}),
            "total_cost_usd": 0.10,
        })

        with (
            patch("subprocess.run", return_value=mock_result),
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
            patch.object(engine.progress, "start"),
            patch.object(engine.progress, "stop"),
            patch.object(engine.progress, "update"),
        ):
            engine.run()

        assert engine.cost_tracker.total_cost == pytest.approx(0.30, abs=0.01)
        assert state.cost_spent_usd == pytest.approx(0.30, abs=0.01)
        engine.git.close()


class TestBuildPrompt:
    """_build_prompt reads experiments.md and constructs iteration prompt."""

    def test_includes_metric_info(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "experiments.md").write_text("# Experiments\nNo results yet.")
        config = Config(metric="rmse", direction="minimize")
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        prompt = engine._build_prompt()
        assert "rmse" in prompt
        assert "minimize" in prompt
        engine.git.close()

    def test_includes_experiment_number(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "experiments.md").write_text("# Experiments")
        config = Config()
        state = SessionState(experiment_count=5)
        engine = RunEngine(tmp_path, config, state)

        prompt = engine._build_prompt()
        assert "6" in prompt  # experiment_count + 1
        engine.git.close()


class TestSignalHandling:
    """RunEngine handles SIGINT gracefully."""

    def test_stop_requested_flag(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        assert engine._stop_requested is False
        engine.git.close()


class TestPostLoop:
    """RunEngine post-loop calls export and retrospective."""

    def test_engine_exports_artifact_after_run(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(budget_experiments=1)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": json.dumps({"metric_value": 0.9}),
            "total_cost_usd": 0.1,
        })

        with (
            patch("subprocess.run", return_value=mock_result),
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
            patch.object(engine.progress, "start"),
            patch.object(engine.progress, "stop"),
            patch.object(engine.progress, "update"),
            patch.object(engine.progress, "log"),
            patch("mlforge.engine.export_artifact", return_value=None) as mock_export,
        ):
            engine.run()

        mock_export.assert_called_once_with(tmp_path, state, config)
        engine.git.close()

    def test_engine_writes_retrospective_after_run(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(budget_experiments=1)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": json.dumps({"metric_value": 0.9}),
            "total_cost_usd": 0.1,
        })

        with (
            patch("subprocess.run", return_value=mock_result),
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
            patch.object(engine.progress, "start"),
            patch.object(engine.progress, "stop"),
            patch.object(engine.progress, "update"),
            patch.object(engine.progress, "log"),
            patch("mlforge.engine.generate_retrospective", return_value="# Retro") as mock_retro,
        ):
            engine.run()

        mock_retro.assert_called_once()
        retro_path = tmp_path / "RETROSPECTIVE.md"
        assert retro_path.exists()
        assert retro_path.read_text() == "# Retro"
        engine.git.close()

    def test_engine_records_results_in_tracker(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(budget_experiments=2)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": json.dumps({"metric_value": 0.9}),
            "total_cost_usd": 0.1,
        })

        with (
            patch("subprocess.run", return_value=mock_result),
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
            patch.object(engine.progress, "start"),
            patch.object(engine.progress, "stop"),
            patch.object(engine.progress, "update"),
            patch.object(engine.progress, "log"),
        ):
            engine.run()

        assert len(engine.results_tracker.results) == 2
        assert engine.results_tracker.results[0].status == "keep"
        engine.git.close()


# --- Helpers ---

def _init_git(path: Path) -> None:
    """Initialize a bare git repo with an initial commit."""
    import git

    repo = git.Repo.init(str(path))
    # Create an initial commit
    (path / ".gitkeep").write_text("")
    repo.index.add([".gitkeep"])
    repo.index.commit("Initial commit")
    repo.close()
