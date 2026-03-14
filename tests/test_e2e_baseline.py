"""Phase 4 E2E baseline artifact verification tests.

04-01-01: iris.csv fixture exists and has correct shape (150 rows, 5 columns).
04-01-02: run-baseline-test.sh is executable and passes bash syntax check.
04-01-04: FINDINGS.md exists with required observation sections.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IRIS_CSV = REPO_ROOT / "tests" / "fixtures" / "iris.csv"
RUN_SCRIPT = REPO_ROOT / "scripts" / "run-baseline-test.sh"
FINDINGS_MD = REPO_ROOT / ".planning" / "phases" / "04-e2e-baseline-test" / "FINDINGS.md"


def test_iris_fixture_has_correct_shape():
    """iris.csv exists with 150 data rows and 5 columns (4 features + species target)."""
    assert IRIS_CSV.exists(), f"iris.csv not found at {IRIS_CSV}"

    lines = IRIS_CSV.read_text().strip().splitlines()
    # 1 header + 150 data rows
    assert len(lines) == 151, f"Expected 151 lines (header + 150 rows), got {len(lines)}"

    header = lines[0].split(",")
    assert len(header) == 5, f"Expected 5 columns, got {len(header)}: {header}"
    assert "species" in header, f"'species' column not found in header: {header}"
    assert any("sepal" in col for col in header), f"No sepal column found in header: {header}"


def test_run_baseline_script_is_executable_and_valid_bash():
    """run-baseline-test.sh is executable and passes bash -n syntax check."""
    assert RUN_SCRIPT.exists(), f"run-baseline-test.sh not found at {RUN_SCRIPT}"
    assert RUN_SCRIPT.stat().st_mode & 0o111, "run-baseline-test.sh is not executable"

    result = subprocess.run(
        ["bash", "-n", str(RUN_SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"bash -n syntax check failed.\nstderr: {result.stderr}"
    )


def test_run_baseline_script_contains_claude_invocation():
    """run-baseline-test.sh contains claude -p invocation with --allowedTools."""
    assert RUN_SCRIPT.exists(), f"run-baseline-test.sh not found at {RUN_SCRIPT}"
    content = RUN_SCRIPT.read_text()
    assert "claude -p" in content, "run-baseline-test.sh must invoke 'claude -p'"
    assert "--allowedTools" in content, "run-baseline-test.sh must pass --allowedTools flag"


def test_findings_md_exists_with_required_sections():
    """FINDINGS.md exists and contains ## Observations and ## Issues Found sections."""
    assert FINDINGS_MD.exists(), f"FINDINGS.md not found at {FINDINGS_MD}"

    content = FINDINGS_MD.read_text()
    assert "## Observations" in content, "FINDINGS.md missing '## Observations' section"
    assert "## Issues Found" in content, "FINDINGS.md missing '## Issues Found' section"
