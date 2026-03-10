"""End-to-end tests: scaffold a project and run train.py.

CLI-04: Generated project is immediately runnable.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from automl.scaffold import scaffold_experiment


@pytest.mark.slow
def test_scaffolded_project_runs(sample_classification_csv, tmp_path):
    """Scaffold a project from sample CSV, run train.py, verify structured output."""
    out_dir = tmp_path / "experiment"
    scaffold_experiment(
        data_path=str(sample_classification_csv),
        target_column="target",
        metric="accuracy",
        goal="Predict binary target",
        output_dir=str(out_dir),
    )

    result = subprocess.run(
        [sys.executable, "train.py"],
        cwd=str(out_dir),
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, (
        f"train.py failed with code {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "metric_name:" in result.stdout
    assert "metric_value:" in result.stdout
    assert "direction:" in result.stdout


@pytest.mark.slow
def test_scaffolded_train_py_metrics_parseable(sample_classification_csv, tmp_path):
    """Structured output from train.py contains parseable float and valid direction."""
    out_dir = tmp_path / "experiment-parse"
    scaffold_experiment(
        data_path=str(sample_classification_csv),
        target_column="target",
        metric="accuracy",
        goal="Predict binary target",
        output_dir=str(out_dir),
    )

    result = subprocess.run(
        [sys.executable, "train.py"],
        cwd=str(out_dir),
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, (
        f"train.py failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    stdout = result.stdout

    # Extract metric_value and parse as float
    match = re.search(r"metric_value:\s*(.+)", stdout)
    assert match is not None, f"metric_value not found in stdout:\n{stdout}"
    metric_value = float(match.group(1).strip())
    assert isinstance(metric_value, float)
    assert metric_value >= 0.0

    # Extract direction and validate
    match = re.search(r"direction:\s*(.+)", stdout)
    assert match is not None, f"direction not found in stdout:\n{stdout}"
    direction = match.group(1).strip()
    assert direction in ("maximize", "minimize")
