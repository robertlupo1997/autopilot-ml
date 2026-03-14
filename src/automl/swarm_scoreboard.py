"""File-locked scoreboard for cross-agent experiment results.

SwarmScoreboard writes results to a shared TSV file using fcntl.LOCK_EX
to prevent corruption from concurrent agent writes. Reads are lockless
(append-only TSV lines are atomic enough for reads; worst case is one stale
row which is acceptable).

No external dependencies -- stdlib only (fcntl, pathlib, time).
"""

import fcntl
import time
from pathlib import Path

HEADER = "agent\tcommit\tmetric_value\telapsed_sec\tstatus\tdescription\ttimestamp\n"


class SwarmScoreboard:
    """Shared scoreboard for tracking experiment results across swarm agents."""

    def __init__(self, swarm_dir: Path):
        self.scoreboard_path = swarm_dir / "scoreboard.tsv"
        self.lock_path = swarm_dir / "scoreboard.lock"
        self.best_train_path = swarm_dir / "best_train.py"

    def read_best(self) -> tuple[float | None, str | None]:
        """Return (score, agent_id) of the highest 'keep' entry.

        Lockless read -- worst case reads stale by one row, which is
        acceptable for the global best check.

        Returns (None, None) when no scoreboard exists or no 'keep' entries.
        """
        if not self.scoreboard_path.exists():
            return None, None
        best_score: float | None = None
        best_agent: str | None = None
        with open(self.scoreboard_path) as f:
            next(f, None)  # skip header
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 5 and parts[4] == "keep":
                    try:
                        score = float(parts[2])
                    except ValueError:
                        continue
                    if best_score is None or score > best_score:
                        best_score = score
                        best_agent = parts[0]
        return best_score, best_agent

    def publish_result(
        self,
        agent_id: str,
        commit: str,
        metric_value: float,
        elapsed_sec: float,
        status: str,
        description: str,
        train_py_source: str | None = None,
    ) -> bool:
        """Append result row to scoreboard. Returns True if this is a new global best.

        Acquires LOCK_EX on scoreboard.lock before writing to ensure atomic
        multi-line operations (header creation + row append + best detection).
        Lock is always released in the finally block even on exception.

        Args:
            agent_id: Identifier for this agent (e.g., "agent-0").
            commit: Short git commit hash for this experiment.
            metric_value: Metric score for this experiment.
            elapsed_sec: Wall-clock time for this experiment in seconds.
            status: One of "keep", "discard", "crash".
            description: Human-readable experiment description.
            train_py_source: Contents of train.py to copy to best_train.py
                             if this is a new global best.

        Returns:
            True if status=="keep" and metric_value exceeds the current global best.
        """
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(self.lock_path, "w") as lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            try:
                if not self.scoreboard_path.exists():
                    self.scoreboard_path.write_text(HEADER)
                current_best, _ = self.read_best()
                with open(self.scoreboard_path, "a") as f:
                    f.write(
                        f"{agent_id}\t{commit}\t{metric_value:.6f}\t"
                        f"{elapsed_sec:.1f}\t{status}\t{description}\t{timestamp}\n"
                    )
                is_new_best = status == "keep" and (
                    current_best is None or metric_value > current_best
                )
                if is_new_best and train_py_source is not None:
                    self.best_train_path.write_text(train_py_source)
                return is_new_best
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
