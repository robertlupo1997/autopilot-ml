"""Checkpoint save/load with schema versioning.

Saves SessionState to checkpoint.json with atomic write-then-rename
to prevent corruption on crash. Includes schema_version for future
migration support.
"""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from datetime import UTC, datetime
from pathlib import Path

from mlforge.state import SessionState

CHECKPOINT_FILE = "checkpoint.json"
SCHEMA_VERSION = 1


def save_checkpoint(state: SessionState, checkpoint_dir: Path) -> None:
    """Save SessionState to checkpoint.json with schema versioning.

    Uses atomic write-then-rename to prevent corruption on crash.
    Creates checkpoint_dir if it does not exist.

    Args:
        state: The session state to persist.
        checkpoint_dir: Directory to write checkpoint.json into.
    """
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / CHECKPOINT_FILE
    tmp_path = checkpoint_dir / (CHECKPOINT_FILE + ".tmp")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "state": asdict(state),
        "timestamp": datetime.now(UTC).isoformat(),
    }

    tmp_path.write_text(json.dumps(payload, indent=2) + "\n")
    tmp_path.rename(checkpoint_path)


def load_checkpoint(checkpoint_dir: Path) -> SessionState | None:
    """Load SessionState from checkpoint.json.

    Returns None if the checkpoint file does not exist (clean start).
    Ignores unknown fields in the state dict for forward compatibility.

    Args:
        checkpoint_dir: Directory containing checkpoint.json.

    Returns:
        Restored SessionState, or None if no checkpoint exists.

    Raises:
        ValueError: If checkpoint.json contains corrupt/invalid JSON.
    """
    checkpoint_path = checkpoint_dir / CHECKPOINT_FILE
    if not checkpoint_path.exists():
        return None

    try:
        data = json.loads(checkpoint_path.read_text())
    except json.JSONDecodeError as exc:
        msg = f"Corrupt checkpoint JSON in {checkpoint_path}: {exc}"
        raise ValueError(msg) from exc

    state_data = data.get("state", {})
    known = {f.name for f in fields(SessionState)}
    return SessionState(**{k: v for k, v in state_data.items() if k in known})
