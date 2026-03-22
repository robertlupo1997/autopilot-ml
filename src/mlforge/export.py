"""Artifact export -- packages the best model with metadata after a session.

Copies the best model file or adapter directory to an ``artifacts/`` directory
alongside a ``metadata.json`` sidecar containing metric info, commit hash,
cost, and timestamp.  Supports tabular (.joblib), DL (.pt), and fine-tuning
(best_adapter/) artifacts.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from mlforge.config import Config
from mlforge.state import SessionState

# Ordered candidate list: first match wins.
# Each entry is (filename, is_directory).
_MODEL_CANDIDATES: list[tuple[str, bool]] = [
    ("best_model.joblib", False),  # tabular
    ("best_model.pt", False),      # DL
    ("best_adapter", True),        # FT (directory)
]


def export_artifact(
    experiment_dir: Path, state: SessionState, config: Config
) -> Path | None:
    """Export the best model artifact with metadata sidecar.

    Searches *experiment_dir* for model artifacts in priority order:
    ``best_model.joblib`` (tabular), ``best_model.pt`` (DL),
    ``best_adapter/`` (fine-tuning).  First match wins.  Copies the artifact
    to ``artifacts/`` and writes ``metadata.json`` alongside it.

    Args:
        experiment_dir: Path to the experiment directory.
        state: Current session state (provides metric value, commit hash, etc.).
        config: Session configuration (provides metric name and direction).

    Returns:
        Path to the ``artifacts/`` directory, or ``None`` if no model found.
    """
    found: Path | None = None
    is_dir_candidate = False
    for name, is_dir in _MODEL_CANDIDATES:
        candidate = experiment_dir / name
        if is_dir and candidate.is_dir():
            found = candidate
            is_dir_candidate = True
            break
        elif not is_dir and candidate.is_file():
            found = candidate
            is_dir_candidate = False
            break

    if found is None:
        return None

    artifacts_dir = experiment_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    # Copy model (not move) to preserve the original
    if is_dir_candidate:
        shutil.copytree(found, artifacts_dir / found.name, dirs_exist_ok=True)
    else:
        shutil.copy2(found, artifacts_dir / found.name)

    # Write metadata sidecar
    metadata = {
        "metric_name": config.metric,
        "metric_value": state.best_metric,
        "metric_direction": config.direction,
        "best_commit": state.best_commit,
        "experiment_count": state.experiment_count,
        "total_cost_usd": state.cost_spent_usd,
        "exported_at": datetime.now(UTC).isoformat(),
    }
    metadata_path = artifacts_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")

    return artifacts_dir
