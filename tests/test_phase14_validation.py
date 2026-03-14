"""Phase 14 validation tests: quarterly_revenue fixture and forecast harness script.

EVAL-01: Agent beats seasonal-naive baseline MAPE (walk-forward)
EVAL-02: At least 5 experiments and at least 1 keep decision
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
QUARTERLY_CSV = REPO_ROOT / "tests" / "fixtures" / "quarterly_revenue.csv"
FORECAST_SCRIPT = REPO_ROOT / "scripts" / "run-forecast-validation-test.sh"


class TestQuarterlyRevenueFixture:
    """Smoke tests for the quarterly_revenue.csv fixture."""

    def test_csv_exists(self):
        """quarterly_revenue.csv fixture file is present on disk."""
        assert QUARTERLY_CSV.exists(), f"quarterly_revenue.csv not found at {QUARTERLY_CSV}"

    def test_csv_has_40_rows(self):
        """quarterly_revenue.csv contains exactly 40 data rows (excluding header)."""
        df = pd.read_csv(QUARTERLY_CSV)
        assert len(df) == 40, f"Expected 40 rows, got {len(df)}"

    def test_csv_has_quarter_column(self):
        """quarterly_revenue.csv contains a column named 'quarter'."""
        df = pd.read_csv(QUARTERLY_CSV)
        assert "quarter" in df.columns, (
            f"'quarter' column not found; columns: {list(df.columns)}"
        )

    def test_csv_has_revenue_column(self):
        """quarterly_revenue.csv contains a column named 'revenue'."""
        df = pd.read_csv(QUARTERLY_CSV)
        assert "revenue" in df.columns, (
            f"'revenue' column not found; columns: {list(df.columns)}"
        )

    def test_csv_quarter_is_parseable_datetime(self):
        """quarter column can be parsed as datetime without errors."""
        df = pd.read_csv(QUARTERLY_CSV)
        parsed = pd.to_datetime(df["quarter"])
        assert len(parsed) == 40, "Expected 40 parsed datetime values"
        assert parsed.isna().sum() == 0, "quarter column contains unparseable values"

    def test_csv_revenue_is_numeric(self):
        """revenue column dtype is float64."""
        df = pd.read_csv(QUARTERLY_CSV)
        assert df["revenue"].dtype == "float64", (
            f"Expected float64, got {df['revenue'].dtype}"
        )


class TestForecastValidationHarnessScript:
    """Smoke tests for the run-forecast-validation-test.sh harness script."""

    def test_script_exists(self):
        """run-forecast-validation-test.sh exists in scripts/ directory."""
        assert FORECAST_SCRIPT.exists(), f"Script not found at {FORECAST_SCRIPT}"

    def test_script_is_executable(self):
        """run-forecast-validation-test.sh has executable permission bit set."""
        assert FORECAST_SCRIPT.stat().st_mode & 0o111, (
            f"Script is not executable: {FORECAST_SCRIPT}"
        )

    def test_script_passes_bash_syntax_check(self):
        """run-forecast-validation-test.sh passes bash -n syntax check."""
        result = subprocess.run(
            ["bash", "-n", str(FORECAST_SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"bash -n failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_script_uses_max_turns_50(self):
        """Script uses --max-turns 50 for the claude -p invocation."""
        content = FORECAST_SCRIPT.read_text()
        assert "max-turns 50" in content, (
            "Expected '--max-turns 50' in run-forecast-validation-test.sh"
        )

    def test_script_uses_parse_run_result(self):
        """Script calls parse_run_result.py for automated stop_reason extraction."""
        content = FORECAST_SCRIPT.read_text()
        assert "parse_run_result.py" in content, (
            "Expected 'parse_run_result.py' reference in run-forecast-validation-test.sh"
        )

    def test_script_references_quarterly_revenue(self):
        """Script uses quarterly_revenue dataset (not noisy.csv or iris.csv)."""
        content = FORECAST_SCRIPT.read_text()
        assert "quarterly_revenue" in content, (
            "Expected 'quarterly_revenue' reference in run-forecast-validation-test.sh"
        )

    def test_script_has_claudecode_guard(self):
        """Script guards against running inside a Claude Code session."""
        content = FORECAST_SCRIPT.read_text()
        assert "CLAUDECODE" in content, (
            "Expected CLAUDECODE guard in run-forecast-validation-test.sh"
        )

    def test_script_uses_date_column_flag(self):
        """Script passes --date-column quarter to the scaffold command."""
        content = FORECAST_SCRIPT.read_text()
        assert "--date-column quarter" in content, (
            "Expected '--date-column quarter' in scaffold command in run-forecast-validation-test.sh"
        )

    def test_script_checks_forecast_py_frozen(self):
        """Script checks that forecast.py was not modified (frozen file compliance)."""
        content = FORECAST_SCRIPT.read_text()
        # Script must check forecast.py in a git diff context
        assert "forecast.py" in content, (
            "Expected 'forecast.py' reference in run-forecast-validation-test.sh"
        )
        # Verify it appears in a frozen-file-check context (git diff or unchanged check)
        lines = content.splitlines()
        forecast_py_lines = [l for l in lines if "forecast.py" in l]
        git_diff_context = any(
            "git diff" in l or "unchanged" in l or "frozen" in l or "FAIL" in l
            for l in forecast_py_lines
        )
        assert git_diff_context, (
            "forecast.py is referenced but not in a frozen-file-check context "
            "(expected git diff or FAIL assertion)\n"
            f"forecast.py lines: {forecast_py_lines}"
        )
