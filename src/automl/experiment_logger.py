"""TSV logging and run.log management for experiment tracking.

Provides append-only results.tsv logging and per-run stdout/stderr capture.
"""

import os

RESULTS_FILE = "results.tsv"
RUN_LOG_FILE = "run.log"
HEADER = "commit\tmetric_value\tmemory_mb\telapsed_sec\tstatus\tdescription\n"


class ExperimentLogger:
    """Log experiment results to TSV and capture run output."""

    def __init__(self, experiment_dir="."):
        self.experiment_dir = experiment_dir
        self.results_path = os.path.join(experiment_dir, RESULTS_FILE)
        self.run_log_path = os.path.join(experiment_dir, RUN_LOG_FILE)

    def init_results(self):
        """Create results.tsv with header if it doesn't exist."""
        if not os.path.exists(self.results_path):
            with open(self.results_path, "w") as f:
                f.write(HEADER)

    def log_result(self, commit, metric_value, memory_mb, elapsed_sec, status, description):
        """Append one experiment result row to results.tsv."""
        with open(self.results_path, "a") as f:
            f.write(
                f"{commit}\t{metric_value:.6f}\t{memory_mb:.1f}\t"
                f"{elapsed_sec:.1f}\t{status}\t{description}\n"
            )

    def write_run_log(self, stdout, stderr=""):
        """Write experiment output to run.log (overwrites previous content)."""
        with open(self.run_log_path, "w") as f:
            f.write(stdout)
            if stderr:
                f.write("\n--- STDERR ---\n")
                f.write(stderr)
