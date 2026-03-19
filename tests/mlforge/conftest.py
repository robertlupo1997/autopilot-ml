"""Shared fixtures for mlforge tests."""

from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test file operations."""
    return tmp_path


@pytest.fixture
def sample_config_toml() -> str:
    """Return a valid mlforge.config.toml string for testing."""
    return """\
domain = "tabular"

[metric]
name = "rmse"
direction = "minimize"

[budget]
minutes = 120
experiments = 100

[files]
frozen = ["prepare.py", "evaluate.py"]
mutable = ["train.py", "features.py"]

[plugin]
model_families = ["sklearn", "xgboost"]
"""


@pytest.fixture
def sample_state():
    """Return a populated SessionState for testing."""
    from mlforge.state import SessionState

    return SessionState(
        experiment_count=5,
        best_metric=0.95,
        best_commit="abc1234",
        budget_remaining=45.0,
        consecutive_reverts=1,
        total_keeps=3,
        total_reverts=2,
        run_id="test-run-001",
    )
