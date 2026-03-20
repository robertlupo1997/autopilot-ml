"""SessionState dataclass with JSON persistence.

Tracks experiment session state across context resets. Uses atomic
write-then-rename to prevent corruption on crash.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


@dataclass
class SessionState:
    """Mutable state tracked across the experiment session."""

    experiment_count: int = 0
    best_metric: float | None = None
    best_commit: str | None = None
    budget_remaining: float = 0.0
    consecutive_reverts: int = 0
    total_keeps: int = 0
    total_reverts: int = 0
    run_id: str = ""
    cost_spent_usd: float = 0.0
    baselines: dict | None = None
    tried_families: list = field(default_factory=list)
    task: str = "classification"

    def to_json(self, path: Path) -> None:
        """Atomic write: write to .tmp file then rename.

        This prevents corrupt state files if the process crashes mid-write.
        """
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2) + "\n")
        tmp.rename(path)

    @classmethod
    def from_json(cls, path: Path) -> SessionState:
        """Load SessionState from a JSON file.

        Ignores unknown fields for forward compatibility -- newer versions
        of mlforge may add fields that older versions should skip.

        Raises:
            FileNotFoundError: If the JSON file does not exist.
        """
        data = json.loads(path.read_text())
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})
