"""File-locked TSV scoreboard for cross-agent coordination.

Uses fcntl.LOCK_EX for atomic writes and lockless reads for display.
Append-only format survives agent crashes.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]

HEADER = "agent\tcommit\tmetric_value\telapsed_sec\tstatus\tdescription\ttimestamp\n"
FIELDS = ["agent", "commit", "metric_value", "elapsed_sec", "status", "description", "timestamp"]


class SwarmScoreboard:
    """Thread-safe TSV scoreboard for swarm agent coordination.

    Uses ``fcntl.LOCK_EX`` for atomic writes. Reads are lockless (safe for
    display). Append-only format means the file survives agent crashes.

    Args:
        scoreboard_path: Path to the ``.swarm/scoreboard.tsv`` file.
        lock_path: Path to the lock file. Defaults to ``scoreboard_path.with_suffix(".lock")``.
        direction: ``"maximize"`` or ``"minimize"`` for best-score comparison.
    """

    def __init__(
        self,
        scoreboard_path: Path,
        lock_path: Path | None = None,
        direction: str = "maximize",
    ) -> None:
        if fcntl is None:
            raise RuntimeError(
                "Swarm mode requires Unix (fcntl). Use WSL on Windows."
            )
        self.scoreboard_path = scoreboard_path
        self.lock_path = lock_path or scoreboard_path.with_suffix(".lock")
        self.direction = direction

    def publish_result(
        self,
        agent: str,
        commit: str,
        metric_value: float,
        elapsed_sec: float,
        status: str,
        description: str,
    ) -> bool:
        """Append a result row and return True if it is a new global best.

        Acquires ``fcntl.LOCK_EX`` for the full read-check-write cycle.
        """
        self.scoreboard_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.touch(exist_ok=True)

        lock_fd = open(self.lock_path, "r+")  # noqa: SIM115
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)

            # Create file with header if needed
            if not self.scoreboard_path.exists():
                self.scoreboard_path.write_text(HEADER)

            # Read current best while holding lock
            current_best = self._parse_best()

            # Build and append new row
            timestamp = datetime.now(timezone.utc).isoformat()
            row = f"{agent}\t{commit}\t{metric_value}\t{elapsed_sec}\t{status}\t{description}\t{timestamp}\n"
            with open(self.scoreboard_path, "a") as f:
                f.write(row)

            # Determine if new global best
            if current_best is None:
                return True
            if self.direction == "maximize":
                return metric_value > current_best
            return metric_value < current_best
        finally:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()

    def read_best(self) -> tuple[float | None, str | None]:
        """Lockless read returning ``(best_metric, best_agent)`` or ``(None, None)``."""
        rows = self._parse_rows()
        if not rows:
            return None, None

        if self.direction == "maximize":
            best = max(rows, key=lambda r: float(r["metric_value"]))
        else:
            best = min(rows, key=lambda r: float(r["metric_value"]))
        return float(best["metric_value"]), best["agent"]

    def read_all(self) -> list[dict]:
        """Lockless read returning all result rows as list of dicts."""
        return self._parse_rows()

    def _parse_best(self) -> float | None:
        """Parse current best metric from file (call while holding lock)."""
        rows = self._parse_rows()
        if not rows:
            return None
        values = [float(r["metric_value"]) for r in rows]
        return max(values) if self.direction == "maximize" else min(values)

    def _parse_rows(self) -> list[dict]:
        """Parse all data rows from TSV file."""
        if not self.scoreboard_path.exists():
            return []
        content = self.scoreboard_path.read_text()
        reader = csv.DictReader(io.StringIO(content), delimiter="\t")
        return list(reader)
