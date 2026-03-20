"""Artifact export -- packages the best model with metadata after a session.

Copies the best model file to an ``artifacts/`` directory alongside a
``metadata.json`` sidecar containing metric info, commit hash, cost, and
timestamp.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from mlforge.config import Config
from mlforge.state import SessionState


def export_artifact(
    experiment_dir: Path, state: SessionState, config: Config
) -> Path | None:
    """Export the best model artifact with metadata sidecar.

    Looks for ``best_model.joblib`` in *experiment_dir*. If found, copies it
    to ``artifacts/`` and writes ``metadata.json`` alongside it.

    Args:
        experiment_dir: Path to the experiment directory.
        state: Current session state (provides metric value, commit hash, etc.).
        config: Session configuration (provides metric name and direction).

    Returns:
        Path to the ``artifacts/`` directory, or ``None`` if no model found.
    """
    model_path = experiment_dir / "best_model.joblib"
    if not model_path.exists():
        return None

    artifacts_dir = experiment_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    # Copy model (not move) to preserve the original
    shutil.copy2(model_path, artifacts_dir / "best_model.joblib")

    # Write metadata sidecar
    metadata = {
        "metric_name": config.metric,
        "metric_value": state.best_metric,
        "metric_direction": config.direction,
        "best_commit": state.best_commit,
        "experiment_count": state.experiment_count,
        "total_cost_usd": state.cost_spent_usd,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path = artifacts_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")

    return artifacts_dir
