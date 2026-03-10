"""Tests for ExperimentRunner -- subprocess execution, metric extraction, run.log capture."""

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "src" / "automl" / "train_template.py"
PREPARE_PATH = Path(__file__).resolve().parent.parent / "src" / "automl" / "prepare.py"


@pytest.fixture
def experiment_dir(sample_classification_csv, tmp_path):
    """Create a temp experiment directory with train.py, prepare.py, and data.csv."""
    exp_dir = tmp_path / "experiment"
    exp_dir.mkdir()
    shutil.copy(TEMPLATE_PATH, exp_dir / "train.py")
    shutil.copy(PREPARE_PATH, exp_dir / "prepare.py")
    shutil.copy(sample_classification_csv, exp_dir / "data.csv")
    return exp_dir


@pytest.fixture
def crash_dir(tmp_path):
    """Experiment directory with a train.py that crashes."""
    exp_dir = tmp_path / "crash_experiment"
    exp_dir.mkdir()
    crash_script = textwrap.dedent("""\
        raise RuntimeError("Deliberate crash for testing")
    """)
    (exp_dir / "train.py").write_text(crash_script)
    return exp_dir


@pytest.fixture
def timeout_dir(tmp_path):
    """Experiment directory with a train.py that sleeps forever."""
    exp_dir = tmp_path / "timeout_experiment"
    exp_dir.mkdir()
    slow_script = textwrap.dedent("""\
        import time
        time.sleep(60)
        print("---")
        print("metric_value: 0.5")
    """)
    (exp_dir / "train.py").write_text(slow_script)
    return exp_dir


class TestExperimentRun:
    """ExperimentRunner.run() executes train.py and returns ExperimentResult."""

    def test_run_experiment(self, experiment_dir):
        from automl.runner import ExperimentRunner

        runner = ExperimentRunner(
            str(experiment_dir), time_budget=60,
            python_cmd=[sys.executable],
        )
        result = runner.run()

        assert result.status == "success"
        assert result.metric_value is not None
        assert isinstance(result.metric_value, float)
        assert result.elapsed_sec >= 0
        assert result.model_name == "LogisticRegression"

    def test_run_captures_log(self, experiment_dir):
        from automl.runner import ExperimentRunner

        runner = ExperimentRunner(
            str(experiment_dir), time_budget=60,
            python_cmd=[sys.executable],
        )
        runner.run()

        run_log = os.path.join(str(experiment_dir), "run.log")
        assert os.path.exists(run_log), "run.log should exist after run()"
        content = open(run_log).read()
        assert "metric_value:" in content

    def test_run_log_overwritten(self, experiment_dir):
        from automl.runner import ExperimentRunner

        runner = ExperimentRunner(
            str(experiment_dir), time_budget=60,
            python_cmd=[sys.executable],
        )
        # Run twice
        runner.run()
        runner.run()

        run_log = os.path.join(str(experiment_dir), "run.log")
        content = open(run_log).read()
        # Should contain exactly one set of structured output (overwritten, not appended)
        metric_lines = [l for l in content.splitlines() if l.startswith("metric_value:")]
        assert len(metric_lines) == 1, f"Expected 1 metric_value line (overwrite), got {len(metric_lines)}"


class TestMetricExtraction:
    """ExperimentRunner._extract_field parses structured output."""

    def test_extract_metric(self):
        from automl.runner import ExperimentRunner

        runner = ExperimentRunner("/tmp", time_budget=60)
        output = "---\nmetric_value: 0.850000\nmetric_std: 0.020000\n"
        value = runner._extract_field(output, "metric_value")
        assert value == pytest.approx(0.85)

    def test_extract_metric_missing(self):
        from automl.runner import ExperimentRunner

        runner = ExperimentRunner("/tmp", time_budget=60)
        result = runner._parse_output("some random output without metrics\n")
        assert result.metric_value is None
        assert result.status == "crash"


class TestErrorHandling:
    """Runner handles crashes and timeouts gracefully."""

    def test_run_crash(self, crash_dir):
        from automl.runner import ExperimentRunner

        runner = ExperimentRunner(
            str(crash_dir), time_budget=60,
            python_cmd=[sys.executable],
        )
        result = runner.run()

        assert result.status == "crash"
        assert result.metric_value is None
        assert result.error is not None
        assert "RuntimeError" in result.error

    def test_run_timeout(self, timeout_dir):
        from automl.runner import ExperimentRunner

        runner = ExperimentRunner(
            str(timeout_dir), time_budget=2,
            python_cmd=[sys.executable],
        )
        result = runner.run()

        assert result.status == "timeout"
        assert result.metric_value is None
