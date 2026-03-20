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


class TestCommandFlags:
    """Verify corrected CLI flag structure in _run_one_experiment."""

    def test_uses_append_system_prompt_with_inline_content(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("my protocol content")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config()
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
            assert "--append-system-prompt" in cmd
            idx = cmd.index("--append-system-prompt")
            assert cmd[idx + 1] == "my protocol content"
            assert "--append-system-prompt-file" not in cmd
        engine.git.close()

    def test_no_max_turns_flag(self, tmp_path):
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
            "result": json.dumps({"metric_value": 0.9}),
            "total_cost_usd": 0.1,
        })

        with patch("subprocess.run", return_value=mock_result) as mock_sub:
            engine._run_one_experiment()
            cmd = mock_sub.call_args[0][0]
            assert "--max-turns" not in cmd
        engine.git.close()

    def test_no_append_system_prompt_when_claude_md_missing(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        # Do NOT create CLAUDE.md
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config()
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
            assert "--append-system-prompt" not in cmd
        engine.git.close()

    def test_max_budget_usd_still_present(self, tmp_path):
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(per_experiment_budget_usd=1.50)
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
            assert "--max-budget-usd" in cmd
            idx = cmd.index("--max-budget-usd")
            assert cmd[idx + 1] == "1.5"
        engine.git.close()


class TestIntelligenceIntegration:
    """Tests for baseline, journal, and stagnation integration in RunEngine."""

    def test_compute_baselines_called_before_loop(self, tmp_path):
        """When domain=='tabular' and prepare.py exists with X_train/y_train,
        compute_baselines() is called and result stored in state.baselines."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")

        # Create a prepare.py with X_train and y_train
        prepare_code = (
            "import numpy as np\n"
            "X_train = np.array([[1,2],[3,4],[5,6],[7,8],[9,10]])\n"
            "y_train = np.array([0,1,0,1,0])\n"
        )
        (tmp_path / "prepare.py").write_text(prepare_code)

        config = Config(domain="tabular", budget_experiments=1)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": json.dumps({"metric_value": 0.9}),
            "total_cost_usd": 0.1,
        })

        baselines_result = {"most_frequent": {"score": 0.5, "std": 0.1}}

        with (
            patch("subprocess.run", return_value=mock_result),
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
            patch.object(engine.progress, "start"),
            patch.object(engine.progress, "stop"),
            patch.object(engine.progress, "update"),
            patch.object(engine.progress, "log"),
            patch("mlforge.engine.compute_baselines", return_value=baselines_result) as mock_bl,
        ):
            engine.run()

        mock_bl.assert_called_once()
        assert state.baselines == baselines_result
        engine.git.close()

    def test_baselines_skipped_for_non_tabular(self, tmp_path):
        """When domain!='tabular', baselines are None and loop runs normally."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(domain="dl", budget_experiments=1)
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

        assert state.baselines is None
        assert state.experiment_count == 1
        engine.git.close()

    def test_baseline_gate_rejects_sub_baseline_keep(self, tmp_path):
        """When metric_value does not beat baselines, _process_result returns 'revert'."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        # Set baselines that are higher than the metric
        state.baselines = {"most_frequent": {"score": 0.8, "std": 0.05}}
        engine = RunEngine(tmp_path, config, state)

        # metric 0.7 does NOT beat baseline 0.8 (maximize direction)
        result = {"metric_value": 0.7, "total_cost_usd": 0.1, "status": "ok"}

        with (
            patch.object(engine.git, "revert_to_last_commit"),
            patch("mlforge.engine.passes_baseline_gate", return_value=False) as mock_gate,
            patch("mlforge.engine.append_journal_entry"),
            patch("mlforge.engine.load_journal", return_value=[]),
            patch("mlforge.engine.render_journal_markdown", return_value=""),
        ):
            action = engine._process_result(result)

        assert action == "revert"
        assert state.total_reverts == 1
        assert state.consecutive_reverts == 1
        engine.git.close()

    def test_baseline_gate_passes_when_beating_baselines(self, tmp_path):
        """When metric_value beats all baselines, keep proceeds normally."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        state.baselines = {"most_frequent": {"score": 0.5, "std": 0.05}}
        engine = RunEngine(tmp_path, config, state)

        result = {"metric_value": 0.9, "total_cost_usd": 0.1, "status": "ok"}

        with (
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
            patch("mlforge.engine.passes_baseline_gate", return_value=True),
            patch("mlforge.engine.append_journal_entry"),
            patch("mlforge.engine.load_journal", return_value=[]),
            patch("mlforge.engine.render_journal_markdown", return_value=""),
            patch("mlforge.engine.get_last_diff", return_value="some diff"),
        ):
            action = engine._process_result(result)

        assert action == "keep"
        assert state.total_keeps == 1
        assert state.best_metric == 0.9
        engine.git.close()

    def test_journal_entry_written_on_keep(self, tmp_path):
        """After a keep action, append_journal_entry() is called with correct fields."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        result = {"metric_value": 0.9, "total_cost_usd": 0.1, "status": "ok"}

        with (
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
            patch("mlforge.engine.append_journal_entry") as mock_append,
            patch("mlforge.engine.load_journal", return_value=[]),
            patch("mlforge.engine.render_journal_markdown", return_value=""),
            patch("mlforge.engine.get_last_diff", return_value="diff text"),
        ):
            engine._process_result(result)

        mock_append.assert_called_once()
        entry = mock_append.call_args[0][1]
        assert entry.status == "keep"
        assert entry.metric_value == 0.9
        assert entry.commit_hash == "abc12345"
        engine.git.close()

    def test_journal_entry_written_on_revert(self, tmp_path):
        """After a revert action, append_journal_entry() is called with status='revert'."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState(best_metric=0.95)
        engine = RunEngine(tmp_path, config, state)

        result = {"metric_value": 0.8, "total_cost_usd": 0.1, "status": "ok"}

        with (
            patch.object(engine.git, "revert_to_last_commit"),
            patch("mlforge.engine.append_journal_entry") as mock_append,
            patch("mlforge.engine.load_journal", return_value=[]),
            patch("mlforge.engine.render_journal_markdown", return_value=""),
            patch("mlforge.engine.check_stagnation", return_value=False),
        ):
            engine._process_result(result)

        mock_append.assert_called_once()
        entry = mock_append.call_args[0][1]
        assert entry.status == "revert"
        assert entry.metric_value == 0.8
        engine.git.close()

    def test_journal_diff_captured_on_keep(self, tmp_path):
        """On keep, get_last_diff() is called and diff is stored in journal entry."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        result = {"metric_value": 0.9, "total_cost_usd": 0.1, "status": "ok"}

        with (
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
            patch("mlforge.engine.append_journal_entry") as mock_append,
            patch("mlforge.engine.load_journal", return_value=[]),
            patch("mlforge.engine.render_journal_markdown", return_value=""),
            patch("mlforge.engine.get_last_diff", return_value="my diff content") as mock_diff,
        ):
            engine._process_result(result)

        mock_diff.assert_called_once_with(tmp_path)
        entry = mock_append.call_args[0][1]
        assert entry.diff == "my diff content"
        engine.git.close()

    def test_stagnation_branch_triggered(self, tmp_path):
        """After consecutive_reverts reaches threshold, stagnation branch is triggered."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState(
            best_metric=0.95,
            best_commit="abc1234",
            consecutive_reverts=2,  # Will become 3 after this revert
        )
        engine = RunEngine(tmp_path, config, state)

        result = {"metric_value": 0.8, "total_cost_usd": 0.1, "status": "ok"}

        with (
            patch.object(engine.git, "revert_to_last_commit"),
            patch("mlforge.engine.append_journal_entry"),
            patch("mlforge.engine.load_journal", return_value=[]),
            patch("mlforge.engine.render_journal_markdown", return_value=""),
            patch("mlforge.engine.check_stagnation", return_value=True) as mock_check,
            patch("mlforge.engine.trigger_stagnation_branch", return_value="explore-random_forest") as mock_branch,
        ):
            engine._process_result(result)

        mock_check.assert_called_once()
        mock_branch.assert_called_once()
        engine.git.close()

    def test_stagnation_picks_untried_family(self, tmp_path):
        """Stagnation picks a family from ALGORITHM_FAMILIES not already in tried_families."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState(
            best_metric=0.95,
            best_commit="abc1234",
            consecutive_reverts=2,
            tried_families=["linear"],  # linear already tried
        )
        engine = RunEngine(tmp_path, config, state)

        result = {"metric_value": 0.8, "total_cost_usd": 0.1, "status": "ok"}

        with (
            patch.object(engine.git, "revert_to_last_commit"),
            patch("mlforge.engine.append_journal_entry"),
            patch("mlforge.engine.load_journal", return_value=[]),
            patch("mlforge.engine.render_journal_markdown", return_value=""),
            patch("mlforge.engine.check_stagnation", return_value=True),
            patch("mlforge.engine.trigger_stagnation_branch", return_value="explore-random_forest") as mock_branch,
            patch("mlforge.engine.ALGORITHM_FAMILIES", {"linear": {}, "random_forest": {}, "xgboost": {}}),
        ):
            engine._process_result(result)

        # Should pick random_forest (first untried), not linear (already tried)
        call_args = mock_branch.call_args
        new_family = call_args[0][2]
        assert new_family == "random_forest"
        assert "random_forest" in state.tried_families
        engine.git.close()

    def test_no_stagnation_below_threshold(self, tmp_path):
        """With fewer than 3 consecutive reverts, no stagnation branch is triggered."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        config = Config()
        state = SessionState(best_metric=0.95, consecutive_reverts=0)
        engine = RunEngine(tmp_path, config, state)

        result = {"metric_value": 0.8, "total_cost_usd": 0.1, "status": "ok"}

        with (
            patch.object(engine.git, "revert_to_last_commit"),
            patch("mlforge.engine.append_journal_entry"),
            patch("mlforge.engine.load_journal", return_value=[]),
            patch("mlforge.engine.render_journal_markdown", return_value=""),
            patch("mlforge.engine.check_stagnation", return_value=False) as mock_check,
            patch("mlforge.engine.trigger_stagnation_branch") as mock_branch,
        ):
            engine._process_result(result)

        mock_check.assert_called_once()
        mock_branch.assert_not_called()
        engine.git.close()


class TestMultiDraftIntegration:
    """Tests for multi-draft phase wired into RunEngine."""

    def test_draft_phase_runs_when_enabled(self, tmp_path):
        """When config.enable_drafts=True, _run_draft_phase() is called before the main loop."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(enable_drafts=True, budget_experiments=1)
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
            patch.object(engine, "_run_draft_phase", return_value=[]) as mock_draft,
        ):
            engine.run()

        mock_draft.assert_called_once()
        engine.git.close()

    def test_draft_phase_skipped_when_disabled(self, tmp_path):
        """When config.enable_drafts=False, no draft phase runs."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(enable_drafts=False, budget_experiments=1)
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

        # _run_draft_phase should not exist as a patched call -- no draft phase invoked
        assert state.experiment_count == 1
        engine.git.close()

    def test_draft_runs_each_family(self, tmp_path):
        """_run_draft_phase() spawns one experiment per ALGORITHM_FAMILIES entry."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        config = Config(enable_drafts=True)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_exp_result = {
            "result": json.dumps({"metric_value": 0.85}),
            "total_cost_usd": 0.1,
        }

        with (
            patch.object(engine, "_run_one_experiment", return_value=mock_exp_result) as mock_run,
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
        ):
            results = engine._run_draft_phase()

        from mlforge.intelligence.drafts import ALGORITHM_FAMILIES
        assert mock_run.call_count == len(ALGORITHM_FAMILIES)
        assert len(results) == len(ALGORITHM_FAMILIES)
        engine.git.close()

    def test_best_draft_selected(self, tmp_path):
        """select_best_draft() is called with draft results and direction."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(enable_drafts=True, budget_experiments=1)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        from mlforge.intelligence.drafts import DraftResult
        draft_results = [
            DraftResult(name="linear", metric_value=0.7, status="draft-keep", commit_hash="aaa", description="Linear"),
            DraftResult(name="xgboost", metric_value=0.9, status="draft-keep", commit_hash="bbb", description="XGBoost"),
        ]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": json.dumps({"metric_value": 0.9}),
            "total_cost_usd": 0.1,
        })

        with (
            patch("subprocess.run", return_value=mock_result),
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
            patch.object(engine.git.repo, "git", MagicMock()),
            patch.object(engine.progress, "start"),
            patch.object(engine.progress, "stop"),
            patch.object(engine.progress, "update"),
            patch.object(engine.progress, "log"),
            patch.object(engine, "_run_draft_phase", return_value=draft_results),
            patch("mlforge.engine.select_best_draft", return_value=draft_results[1]) as mock_select,
        ):
            engine.run()

        mock_select.assert_called_once_with(draft_results, config.direction)
        engine.git.close()

    def test_best_draft_checkout(self, tmp_path):
        """After selection, git checkouts to the best draft's commit_hash."""
        from mlforge.engine import RunEngine
        from mlforge.intelligence.drafts import DraftResult

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(enable_drafts=True, budget_experiments=1)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        best = DraftResult(name="xgboost", metric_value=0.9, status="draft-keep", commit_hash="bbb123", description="XGBoost")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": json.dumps({"metric_value": 0.9}),
            "total_cost_usd": 0.1,
        })

        with (
            patch("subprocess.run", return_value=mock_result),
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
            patch.object(engine.git.repo, "git", MagicMock()),
            patch.object(engine.progress, "start"),
            patch.object(engine.progress, "stop"),
            patch.object(engine.progress, "update"),
            patch.object(engine.progress, "log"),
            patch.object(engine, "_run_draft_phase", return_value=[best]),
            patch("mlforge.engine.select_best_draft", return_value=best),
        ):
            engine.run()

        assert state.best_metric == 0.9
        assert state.best_commit == "bbb123"
        engine.git.close()

    def test_draft_results_none_handled(self, tmp_path):
        """When all drafts fail (metric_value=None), loop continues without checkout."""
        from mlforge.engine import RunEngine
        from mlforge.intelligence.drafts import DraftResult

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        (tmp_path / "experiments.md").write_text("# Journal")
        config = Config(enable_drafts=True, budget_experiments=1)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        failed_drafts = [
            DraftResult(name="linear", metric_value=None, status="draft-discard", commit_hash="", description="Failed"),
        ]

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
            patch.object(engine, "_run_draft_phase", return_value=failed_drafts),
            patch("mlforge.engine.select_best_draft", return_value=None),
        ):
            engine.run()

        # Loop ran normally despite all drafts failing
        assert state.experiment_count == 1
        assert state.best_commit is None or state.best_commit == "abc12345"
        engine.git.close()

    def test_tried_families_populated(self, tmp_path):
        """After draft phase, state.tried_families contains all family names tried."""
        from mlforge.engine import RunEngine

        _init_git(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("protocol")
        config = Config(enable_drafts=True)
        state = SessionState()
        engine = RunEngine(tmp_path, config, state)

        mock_exp_result = {
            "result": json.dumps({"metric_value": 0.85}),
            "total_cost_usd": 0.1,
        }

        with (
            patch.object(engine, "_run_one_experiment", return_value=mock_exp_result) as mock_run,
            patch.object(engine.git, "commit_experiment", return_value="abc12345"),
        ):
            results = engine._run_draft_phase()

        from mlforge.intelligence.drafts import ALGORITHM_FAMILIES
        for family_name in ALGORITHM_FAMILIES:
            assert family_name in state.tried_families
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
