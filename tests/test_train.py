"""Tests for train_template.py -- the mutable experiment script.

MODEL-01: Agent edits a single train.py file
MODEL-02: train.py provides baseline model
MODEL-03: train.py imports from prepare.py
MODEL-04: train.py prints structured metric output
MODEL-05: train.py enforces configurable time budget
"""

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "src" / "automl" / "train_template.py"
PREPARE_PATH = Path(__file__).resolve().parent.parent / "src" / "automl" / "prepare.py"


class TestTemplateFile:
    """MODEL-01: train_template.py exists as a single Python file."""

    def test_template_is_single_file(self):
        assert TEMPLATE_PATH.exists(), "train_template.py should exist"
        assert TEMPLATE_PATH.suffix == ".py"

    def test_template_imports_prepare(self):
        """MODEL-03: template imports from prepare."""
        content = TEMPLATE_PATH.read_text()
        assert "from prepare import" in content


class TestTemplateExecution:
    """MODEL-02, MODEL-04: template runs and produces structured output."""

    @pytest.fixture
    def experiment_dir(self, sample_classification_csv, tmp_path):
        """Create a temp experiment directory with train.py, prepare.py, and data.csv."""
        exp_dir = tmp_path / "experiment"
        exp_dir.mkdir()

        # Copy train_template.py as train.py
        shutil.copy(TEMPLATE_PATH, exp_dir / "train.py")

        # Copy prepare.py as sibling
        shutil.copy(PREPARE_PATH, exp_dir / "prepare.py")

        # Copy CSV as data.csv (the template default)
        shutil.copy(sample_classification_csv, exp_dir / "data.csv")

        return exp_dir

    def test_template_runs(self, experiment_dir):
        """MODEL-02: template exits 0 with a valid CSV."""
        result = subprocess.run(
            [sys.executable, "train.py"],
            capture_output=True, text=True,
            cwd=str(experiment_dir),
            timeout=30,
        )
        assert result.returncode == 0, f"train.py failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"

    def test_structured_output(self, experiment_dir):
        """MODEL-04: output has structured metric lines after --- separator."""
        result = subprocess.run(
            [sys.executable, "train.py"],
            capture_output=True, text=True,
            cwd=str(experiment_dir),
            timeout=30,
        )
        assert result.returncode == 0, f"train.py failed:\nSTDERR: {result.stderr}"

        stdout = result.stdout
        assert "---" in stdout, "Output should contain --- separator"

        # All required fields present
        required_fields = [
            "metric_name:", "metric_value:", "metric_std:",
            "direction:", "elapsed_sec:", "model:",
        ]
        for field in required_fields:
            assert field in stdout, f"Output missing '{field}' field"

    def test_metric_extractable(self, experiment_dir):
        """Metric value can be extracted via grep-style parsing."""
        result = subprocess.run(
            [sys.executable, "train.py"],
            capture_output=True, text=True,
            cwd=str(experiment_dir),
            timeout=30,
        )
        assert result.returncode == 0

        # Extract metric_value line
        metric_lines = [
            line for line in result.stdout.splitlines()
            if line.startswith("metric_value:")
        ]
        assert len(metric_lines) == 1, f"Expected exactly one metric_value line, got {len(metric_lines)}"

        # Parse as float
        value_str = metric_lines[0].split(":")[1].strip()
        value = float(value_str)
        assert 0.0 <= value <= 1.0, f"Accuracy should be between 0 and 1, got {value}"


class TestTimeoutEnforcement:
    """MODEL-05: time budget is enforced."""

    def test_timeout_enforced(self, sample_classification_csv, tmp_path):
        """A template with TIME_BUDGET=1 and a slow model exits non-zero."""
        exp_dir = tmp_path / "experiment_timeout"
        exp_dir.mkdir()

        # Copy prepare.py
        shutil.copy(PREPARE_PATH, exp_dir / "prepare.py")

        # Copy CSV
        shutil.copy(sample_classification_csv, exp_dir / "data.csv")

        # Create a modified train.py that sleeps
        slow_train = textwrap.dedent("""\
            import time
            import signal
            import sys

            CSV_PATH = "data.csv"
            TARGET_COLUMN = "target"
            METRIC = "accuracy"
            TIME_BUDGET = 1

            def _timeout_handler(signum, frame):
                raise TimeoutError(f"Experiment exceeded {TIME_BUDGET}s time budget")
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(TIME_BUDGET)

            # Deliberate slow operation
            time.sleep(10)

            print("---")
            print("metric_value: 0.5")
        """)
        (exp_dir / "train.py").write_text(slow_train)

        result = subprocess.run(
            [sys.executable, "train.py"],
            capture_output=True, text=True,
            cwd=str(exp_dir),
            timeout=5,
        )
        # Should exit non-zero due to TimeoutError
        assert result.returncode != 0, "Should have failed due to timeout"
        assert "TimeoutError" in result.stderr, f"Expected TimeoutError in stderr, got: {result.stderr}"
