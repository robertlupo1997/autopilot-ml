"""Experiment directory scaffolding.

Creates a complete experiment directory using the plugin system,
templates, and hook files.
"""

from __future__ import annotations

from pathlib import Path

from mlforge.config import Config


def scaffold_experiment(
    config: Config,
    dataset_path: Path,
    target_dir: Path,
    run_id: str,
) -> Path:
    """Create a complete experiment directory.

    This is a stub that will be fully implemented in Task 2.

    Args:
        config: Session configuration.
        dataset_path: Path to the dataset file.
        target_dir: Directory to create the experiment in.
        run_id: Unique identifier for this run.

    Returns:
        The target directory Path.

    Raises:
        FileNotFoundError: If dataset_path does not exist.
    """
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir
