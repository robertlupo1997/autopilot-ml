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
def quarterly_revenue_series() -> np.ndarray:
    """40-row synthetic quarterly revenue series (dollars) with trend and seasonality.

    Generates: base=1000 + 50*quarter_index + 200*sin(quarter_index * pi/2) + noise
    Returned as np.ndarray of shape (40,) with positive dollar values.
    """
    rng = np.random.RandomState(7)
    quarters = np.arange(40)
    series = (
        1000.0
        + 50.0 * quarters
        + 200.0 * np.sin(quarters * np.pi / 2)
        + rng.randn(40) * 30.0
    )
    return series.astype(float)


@pytest.fixture
def sample_forecast_csv(tmp_path: Path) -> Path:
    """Generate a forecasting CSV with 40 rows of quarterly revenue data.

    Columns: date (Q1 2015 to Q4 2024), feature1 (numeric), feature2 (numeric),
    revenue (target, dollar values with trend).
    """
    rng = np.random.RandomState(7)
    dates = pd.date_range(start="2015-01-01", periods=40, freq="QS")
    quarters = np.arange(40)
    revenue = (
        1000.0
        + 50.0 * quarters
        + 200.0 * np.sin(quarters * np.pi / 2)
        + rng.randn(40) * 30.0
    )

    df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "feature1": rng.randn(40),
        "feature2": rng.randn(40) * 5 + 10,
        "revenue": revenue,
    })

    csv_path = tmp_path / "forecast_data.csv"
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
