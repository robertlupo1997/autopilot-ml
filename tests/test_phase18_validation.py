"""Phase 18 validation tests: v3.0 intelligent iteration harness script.

EVAL-03: Agent reads and modifies experiments.md (journal usage)
EVAL-04: Agent creates explore-* branches after 3+ consecutive reverts (stagnation)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
V3_SCRIPT = REPO_ROOT / "scripts" / "run-v3-validation-test.sh"


class TestV3ValidationHarnessScript:
    """Smoke tests for the run-v3-validation-test.sh harness script."""

    def test_script_exists(self):
        """run-v3-validation-test.sh exists in scripts/ directory."""
        assert V3_SCRIPT.exists(), f"Script not found at {V3_SCRIPT}"

    def test_script_is_executable(self):
        """run-v3-validation-test.sh has executable permission bit set."""
        assert V3_SCRIPT.stat().st_mode & 0o111, (
            f"Script is not executable: {V3_SCRIPT}"
        )

    def test_script_passes_bash_syntax_check(self):
        """run-v3-validation-test.sh passes bash -n syntax check."""
        result = subprocess.run(
            ["bash", "-n", str(V3_SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"bash -n failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_script_uses_max_turns_75(self):
        """Script uses --max-turns 75 for the claude -p invocation."""
        content = V3_SCRIPT.read_text()
        assert "max-turns 75" in content, (
            "Expected '--max-turns 75' in run-v3-validation-test.sh"
        )

    def test_script_uses_parse_run_result(self):
        """Script calls parse_run_result.py for automated stop_reason extraction."""
        content = V3_SCRIPT.read_text()
        assert "parse_run_result.py" in content, (
            "Expected 'parse_run_result.py' reference in run-v3-validation-test.sh"
        )

    def test_script_references_quarterly_revenue(self):
        """Script uses quarterly_revenue dataset (reuses Phase 14 fixture)."""
        content = V3_SCRIPT.read_text()
        assert "quarterly_revenue" in content, (
            "Expected 'quarterly_revenue' reference in run-v3-validation-test.sh"
        )

    def test_script_has_claudecode_guard(self):
        """Script guards against running inside a Claude Code session."""
        content = V3_SCRIPT.read_text()
        assert "CLAUDECODE" in content, (
            "Expected CLAUDECODE guard in run-v3-validation-test.sh"
        )

    def test_script_uses_date_column_flag(self):
        """Script passes --date-column quarter to the scaffold command."""
        content = V3_SCRIPT.read_text()
        assert "--date-column quarter" in content, (
            "Expected '--date-column quarter' in scaffold command in run-v3-validation-test.sh"
        )

    def test_script_checks_experiments_md(self):
        """Script checks experiments.md for journal usage (EVAL-03)."""
        content = V3_SCRIPT.read_text()
        assert "experiments.md" in content, (
            "Expected 'experiments.md' reference in run-v3-validation-test.sh"
        )

    def test_script_checks_explore_branches(self):
        """Script checks for explore-* branches (EVAL-04 branch-on-stagnation)."""
        content = V3_SCRIPT.read_text()
        assert "explore-" in content, (
            "Expected 'explore-' branch pattern reference in run-v3-validation-test.sh"
        )

    def test_script_checks_consecutive_reverts(self):
        """Script counts consecutive reverts to verify stagnation condition (EVAL-04)."""
        content = V3_SCRIPT.read_text()
        assert "consecutive" in content, (
            "Expected 'consecutive' in run-v3-validation-test.sh (stagnation counting)"
        )
        assert "revert" in content.lower(), (
            "Expected 'revert' in run-v3-validation-test.sh (stagnation counting)"
        )

    def test_script_has_eval03_section(self):
        """Script contains EVAL-03 (journal usage) diagnostic section."""
        content = V3_SCRIPT.read_text()
        assert "EVAL-03" in content, (
            "Expected 'EVAL-03' section in run-v3-validation-test.sh"
        )

    def test_script_has_eval04_section(self):
        """Script contains EVAL-04 (branch-on-stagnation) diagnostic section."""
        content = V3_SCRIPT.read_text()
        assert "EVAL-04" in content, (
            "Expected 'EVAL-04' section in run-v3-validation-test.sh"
        )
