"""Experiment runner -- executes train.py as a subprocess and extracts results.

Provides ExperimentRunner (subprocess execution, metric extraction, run.log capture)
and ExperimentResult (structured result dataclass).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExperimentResult:
    """Structured result from a single experiment run."""

    metric_value: Optional[float]
    metric_std: Optional[float]
    elapsed_sec: float
    status: str  # "success", "crash", "timeout"
    model_name: str
    error: Optional[str]
    description: str


class ExperimentRunner:
    """Execute train.py as a subprocess, capture output, and extract metrics.

    Parameters
    ----------
    experiment_dir : str
        Path to the experiment directory containing train.py.
    time_budget : int
        Time budget in seconds. The hard kill timeout is 2x this value.
    python_cmd : list[str] | None
        Command to run Python. Defaults to ["uv", "run", "python"].
        Override to [sys.executable] in tests where uv may not be configured.
    """

    def __init__(
        self,
        experiment_dir: str,
        time_budget: int = 60,
        python_cmd: list[str] | None = None,
    ):
        self.experiment_dir = experiment_dir
        self.time_budget = time_budget
        self.python_cmd = python_cmd or ["uv", "run", "python"]
        self.run_log_path = os.path.join(experiment_dir, "run.log")

    def run(self) -> ExperimentResult:
        """Execute train.py and return structured result."""
        hard_timeout = self.time_budget * 2

        try:
            result = subprocess.run(
                [*self.python_cmd, "train.py"],
                capture_output=True,
                text=True,
                timeout=hard_timeout,
                cwd=self.experiment_dir,
            )
            # Write run.log (overwrite mode)
            self._write_run_log(result.stdout, result.stderr)

            if result.returncode != 0:
                return ExperimentResult(
                    metric_value=None,
                    metric_std=None,
                    elapsed_sec=0,
                    status="crash",
                    model_name="unknown",
                    error=result.stderr,
                    description=f"Crash: {result.stderr[:200]}",
                )

            return self._parse_output(result.stdout)

        except subprocess.TimeoutExpired as e:
            stdout = e.stdout or ""
            stderr = e.stderr or ""
            # Decode bytes if needed
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            self._write_run_log(stdout, stderr)
            return ExperimentResult(
                metric_value=None,
                metric_std=None,
                elapsed_sec=hard_timeout,
                status="timeout",
                model_name="unknown",
                error=f"Exceeded {hard_timeout}s hard timeout",
                description="Timeout: exceeded hard time limit",
            )

    def _parse_output(self, stdout: str) -> ExperimentResult:
        """Extract structured fields from train.py output."""
        metric_value = self._extract_field(stdout, "metric_value")
        metric_std = self._extract_field(stdout, "metric_std")
        elapsed = self._extract_field(stdout, "elapsed_sec")
        model_name = self._extract_string_field(stdout, "model")
        metric_name = self._extract_string_field(stdout, "metric_name")

        if metric_value is None:
            return ExperimentResult(
                metric_value=None,
                metric_std=None,
                elapsed_sec=elapsed or 0,
                status="crash",
                model_name=model_name or "unknown",
                error="Could not parse metric_value from output",
                description="Parse error: no metric_value in output",
            )

        return ExperimentResult(
            metric_value=metric_value,
            metric_std=metric_std,
            elapsed_sec=elapsed or 0,
            status="success",
            model_name=model_name or "unknown",
            error=None,
            description=f"{model_name}: {metric_name}={metric_value:.6f}",
        )

    def _extract_field(self, text: str, field_name: str) -> Optional[float]:
        """Extract float value from 'field_name: value' line."""
        match = re.search(rf"^{field_name}:\s+(.+)$", text, re.MULTILINE)
        if match:
            try:
                return float(match.group(1).strip())
            except ValueError:
                return None
        return None

    def _extract_string_field(self, text: str, field_name: str) -> Optional[str]:
        """Extract string value from 'field_name: value' line."""
        match = re.search(rf"^{field_name}:\s+(.+)$", text, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _write_run_log(self, stdout: str, stderr: str) -> None:
        """Write stdout+stderr to run.log (overwrite mode)."""
        with open(self.run_log_path, "w") as f:
            f.write(stdout)
            if stderr:
                f.write("\n--- STDERR ---\n")
                f.write(stderr)
