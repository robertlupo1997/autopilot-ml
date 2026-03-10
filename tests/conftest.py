"""Shared test fixtures for AutoML test suite."""

import numpy as np
import pandas as pd
import pytest
from pathlib import Path


@pytest.fixture
def sample_classification_csv(tmp_path: Path) -> Path:
    """Generate a classification CSV with 200 rows, 5 numeric + 2 categorical columns, binary target."""
    rng = np.random.RandomState(42)

    df = pd.DataFrame({
        "feat_num1": rng.randn(200),
        "feat_num2": rng.randn(200),
        "feat_num3": rng.randn(200),
        "feat_num4": rng.randn(200),
        "feat_num5": rng.randn(200),
        "feat_cat1": rng.choice(["A", "B", "C"], size=200),
        "feat_cat2": rng.choice(["X", "Y"], size=200),
        "target": rng.choice([0, 1], size=200),
    })

    csv_path = tmp_path / "data.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_regression_csv(tmp_path: Path) -> Path:
    """Generate a regression CSV with 200 rows, numeric target."""
    rng = np.random.RandomState(42)

    df = pd.DataFrame({
        "feat_num1": rng.randn(200),
        "feat_num2": rng.randn(200),
        "feat_num3": rng.randn(200),
        "feat_num4": rng.randn(200),
        "feat_num5": rng.randn(200),
        "feat_cat1": rng.choice(["A", "B", "C"], size=200),
        "feat_cat2": rng.choice(["X", "Y"], size=200),
        "target": rng.randn(200) * 10 + 50,
    })

    csv_path = tmp_path / "data.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_csv_with_missing(tmp_path: Path) -> Path:
    """Generate a classification CSV with ~10% missing values in numeric and categorical columns."""
    rng = np.random.RandomState(42)

    df = pd.DataFrame({
        "feat_num1": rng.randn(200),
        "feat_num2": rng.randn(200),
        "feat_num3": rng.randn(200),
        "feat_num4": rng.randn(200),
        "feat_num5": rng.randn(200),
        "feat_cat1": rng.choice(["A", "B", "C"], size=200),
        "feat_cat2": rng.choice(["X", "Y"], size=200),
        "target": rng.choice([0, 1], size=200),
    })

    # Inject ~10% missing values into feature columns (not target)
    feature_cols = [c for c in df.columns if c != "target"]
    for col in feature_cols:
        mask = rng.random(200) < 0.10
        df.loc[mask, col] = np.nan

    csv_path = tmp_path / "data.csv"
    df.to_csv(csv_path, index=False)
    return csv_path
