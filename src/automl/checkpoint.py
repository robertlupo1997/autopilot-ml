"""Checkpoint persistence for session resume.

Writes LoopState + session metadata to checkpoint.json after each experiment.
Allows claude -p sessions to resume from where the last session left off.
"""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from pathlib import Path

CHECKPOINT_FILE = "checkpoint.json"
SCHEMA_VERSION = 1


def save_checkpoint(
    loop_state,
    loop_phase: str,
    iteration: int,
    path: str = ".",
) -> None:
    """Persist LoopState + session metadata to checkpoint.json atomically.

    Uses write-then-rename for atomicity: a partial write never leaves
    a corrupt checkpoint file.

    Parameters
    ----------
    loop_state : LoopState
        Current loop state (dataclass -- serialized with asdict).
    loop_phase : str
        "draft" or "iteration" -- which phase the agent is in.
    iteration : int
        Total number of experiments run this session.
    path : str
        Directory containing the experiment (default: cwd).
    """
    data = asdict(loop_state)
    data["loop_phase"] = loop_phase
    data["iteration"] = iteration
    data["schema_version"] = SCHEMA_VERSION

    checkpoint_path = Path(path) / CHECKPOINT_FILE
    tmp_path = checkpoint_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(data, indent=2) + "\n")
    tmp_path.rename(checkpoint_path)


def load_checkpoint(path: str = ".") -> dict | None:
    """Load checkpoint.json if it exists. Returns None if absent or corrupt."""
    checkpoint_path = Path(path) / CHECKPOINT_FILE
    if not checkpoint_path.exists():
        return None
    try:
        return json.loads(checkpoint_path.read_text())
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def load_loop_state(path: str = "."):
    """Load checkpoint and reconstruct LoopState. Returns None if no checkpoint.

    Filters out non-LoopState fields (loop_phase, iteration, schema_version)
    so deserialization is forward-compatible with future LoopState additions.
    """
    from automl.loop_helpers import LoopState

    data = load_checkpoint(path)
    if data is None:
        return None
    known_fields = {f.name for f in fields(LoopState)}
    state_dict = {k: v for k, v in data.items() if k in known_fields}
    return LoopState(**state_dict)


def checkpoint_exists(path: str = ".") -> bool:
    """Return True if checkpoint.json exists in path."""
    return (Path(path) / CHECKPOINT_FILE).exists()
