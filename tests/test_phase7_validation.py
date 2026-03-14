"""Phase 7 validation tests: noisy fixture and validation harness script.

VAL-01: noisy.csv fixture exists with 300 rows and binary target column
VAL-02: run-validation-test.sh passes bash syntax check and has correct properties
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
NOISY_CSV = REPO_ROOT / "tests" / "fixtures" / "noisy.csv"
VALIDATION_SCRIPT = REPO_ROOT / "scripts" / "run-validation-test.sh"


class TestNoisyDatasetFixture:
    """VAL-01: noisy.csv is present and correctly formed."""

    def test_noisy_csv_exists(self):
        """VAL-01: noisy.csv fixture file is present on disk."""
        assert NOISY_CSV.exists(), f"noisy.csv not found at {NOISY_CSV}"

    def test_noisy_csv_has_300_rows(self):
        """VAL-01: noisy.csv contains exactly 300 data rows (excluding header)."""
        df = pd.read_csv(NOISY_CSV)
        assert len(df) == 300, f"Expected 300 rows, got {len(df)}"

    def test_noisy_csv_has_target_column(self):
        """VAL-01: noisy.csv contains a column named 'target'."""
        df = pd.read_csv(NOISY_CSV)
        assert "target" in df.columns, f"'target' column not found; columns: {list(df.columns)}"

    def test_noisy_csv_target_is_binary(self):
        """VAL-01: target column contains only binary values (0 and 1)."""
        df = pd.read_csv(NOISY_CSV)
        unique_values = set(df["target"].unique())
        assert unique_values <= {0, 1}, f"Expected binary target (0/1), got: {unique_values}"

    def test_noisy_csv_has_feature_columns(self):
        """VAL-01: noisy.csv has 10 feature columns plus the target column."""
        df = pd.read_csv(NOISY_CSV)
        feature_cols = [c for c in df.columns if c != "target"]
        assert len(feature_cols) == 10, f"Expected 10 feature columns, got {len(feature_cols)}: {feature_cols}"


class TestValidationHarnessScript:
    """VAL-02: run-validation-test.sh is present and correctly structured."""

    def test_validation_script_exists(self):
        """VAL-02: run-validation-test.sh exists in scripts/ directory."""
        assert VALIDATION_SCRIPT.exists(), f"Script not found at {VALIDATION_SCRIPT}"

    def test_validation_script_is_executable(self):
        """VAL-02: run-validation-test.sh has executable permission bit set."""
        assert VALIDATION_SCRIPT.stat().st_mode & 0o111, (
            f"Script is not executable: {VALIDATION_SCRIPT}"
        )

    def test_validation_script_passes_bash_syntax_check(self):
        """VAL-02: run-validation-test.sh passes bash -n syntax check."""
        result = subprocess.run(
            ["bash", "-n", str(VALIDATION_SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"bash -n failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_validation_script_uses_max_turns_50(self):
        """VAL-02: script uses --max-turns 50 (not the Phase 4 default of 30)."""
        content = VALIDATION_SCRIPT.read_text()
        assert "max-turns 50" in content, (
            "Expected '--max-turns 50' in run-validation-test.sh"
        )

    def test_validation_script_uses_parse_run_result(self):
        """VAL-02: script calls parse_run_result.py for automated stop_reason extraction."""
        content = VALIDATION_SCRIPT.read_text()
        assert "parse_run_result.py" in content, (
            "Expected 'parse_run_result.py' reference in run-validation-test.sh"
        )

    def test_validation_script_references_noisy_csv(self):
        """VAL-02: script uses noisy.csv (not iris.csv) as the dataset."""
        content = VALIDATION_SCRIPT.read_text()
        assert "noisy.csv" in content, "Expected 'noisy.csv' reference in run-validation-test.sh"

    def test_validation_script_has_claudecode_guard(self):
        """VAL-02: script guards against running inside a Claude Code session."""
        content = VALIDATION_SCRIPT.read_text()
        assert "CLAUDECODE" in content, (
            "Expected CLAUDECODE guard in run-validation-test.sh to prevent nested sessions"
        )
