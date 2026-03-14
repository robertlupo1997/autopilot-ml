"""Frozen data pipeline for AutoML.

This module provides all data operations that remain constant across experiments:
loading, splitting, preprocessing, evaluation, baselines, data summary, and metric
validation. These functions are imported by train.py and must not be modified by
the autonomous agent during experimentation.

PIPE-01: load_data
PIPE-02: split_data
PIPE-03: evaluate
PIPE-04: get_baselines
PIPE-05: build_preprocessor
PIPE-06: get_data_summary
PIPE-07: validate_metric
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder


# ---------------------------------------------------------------------------
# PIPE-07: Metric mapping
# ---------------------------------------------------------------------------

# Maps user-facing metric names -> (sklearn scoring string, direction).
# All directions are "maximize" because sklearn negates error metrics.
METRIC_MAP: dict[str, tuple[str, str]] = {
    "accuracy": ("accuracy", "maximize"),
    "auc": ("roc_auc", "maximize"),
    "roc_auc": ("roc_auc", "maximize"),
    "f1": ("f1", "maximize"),
    "f1_weighted": ("f1_weighted", "maximize"),
    "precision": ("precision", "maximize"),
    "recall": ("recall", "maximize"),
    "log_loss": ("neg_log_loss", "maximize"),
    "rmse": ("neg_root_mean_squared_error", "maximize"),
    "mae": ("neg_mean_absolute_error", "maximize"),
    "r2": ("r2", "maximize"),
    "mse": ("neg_mean_squared_error", "maximize"),
}

_CLASSIFICATION_METRICS = {
    "accuracy", "auc", "roc_auc", "f1", "f1_weighted",
    "precision", "recall", "log_loss",
}
_REGRESSION_METRICS = {"rmse", "mae", "r2", "mse"}


def validate_metric(metric_name: str, task: str) -> tuple[str, str]:
    """Validate metric exists and is compatible with task type.

    Parameters
    ----------
    metric_name : str
        User-facing metric name (e.g. "auc", "rmse").
    task : str
        Either "classification" or "regression".

    Returns
    -------
    tuple[str, str]
        (sklearn_scoring_string, direction)

    Raises
    ------
    ValueError
        If metric is unknown or incompatible with task.
    """
    if metric_name not in METRIC_MAP:
        raise ValueError(
            f"Unknown metric '{metric_name}'. "
            f"Valid metrics: {sorted(METRIC_MAP.keys())}"
        )

    if task == "classification" and metric_name in _REGRESSION_METRICS:
        raise ValueError(
            f"Metric '{metric_name}' is not compatible with classification tasks. "
            f"Use one of: {sorted(_CLASSIFICATION_METRICS)}"
        )
    if task == "regression" and metric_name in _CLASSIFICATION_METRICS:
        raise ValueError(
            f"Metric '{metric_name}' is not compatible with regression tasks. "
            f"Use one of: {sorted(_REGRESSION_METRICS)}"
        )

    return METRIC_MAP[metric_name]


# ---------------------------------------------------------------------------
# PIPE-01: Load data
# ---------------------------------------------------------------------------

def load_data(
    csv_path: str | Path,
    target_column: str,
    date_col: str | None = None,
) -> tuple[pd.DataFrame, pd.Series, str]:
    """Read a CSV and return features, target, and inferred task type.

    Parameters
    ----------
    csv_path : str or Path
        Path to the CSV file.
    target_column : str
        Name of the target column.
    date_col : str or None
        Optional name of a date column to parse as datetime and set as the
        DataFrame index (sorted ascending). When provided the returned X has a
        DatetimeIndex and the date column is excluded from features.
        Default is None (backwards-compatible behaviour: RangeIndex).

    Returns
    -------
    tuple[DataFrame, Series, str]
        (X, y, task) where task is "classification" or "regression".
    """
    if date_col is not None:
        df = pd.read_csv(csv_path, parse_dates=[date_col])
        df = df.set_index(date_col).sort_index()
    else:
        df = pd.read_csv(csv_path)

    y = df[target_column]
    X = df.drop(columns=[target_column])

    # Infer task type
    if y.dtype == object or isinstance(y.dtype, pd.CategoricalDtype):
        task = "classification"
    elif pd.api.types.is_integer_dtype(y) and y.nunique() <= 20:
        task = "classification"
    else:
        task = "regression"

    return X, y, task


# ---------------------------------------------------------------------------
# PIPE-08: Temporal split (forecasting)
# ---------------------------------------------------------------------------

def temporal_split(
    X: pd.DataFrame,
    y: pd.Series,
    holdout_fraction: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split time-ordered data into train and holdout sets without shuffling.

    Data must be pre-sorted in ascending time order (e.g. by calling
    load_data with date_col). The last ``holdout_fraction`` of rows become the
    holdout set. No shuffle is performed, preserving temporal order.

    Invariant: X_train.index[-1] < X_holdout.index[0]

    Parameters
    ----------
    X : DataFrame
        Feature matrix sorted in ascending time order.
    y : Series
        Target vector aligned with X.
    holdout_fraction : float
        Fraction of rows reserved for holdout (default 0.15).

    Returns
    -------
    tuple
        (X_train, X_holdout, y_train, y_holdout)
    """
    split_idx = math.floor(len(X) * (1 - holdout_fraction))
    return (
        X.iloc[:split_idx],
        X.iloc[split_idx:],
        y.iloc[:split_idx],
        y.iloc[split_idx:],
    )


# ---------------------------------------------------------------------------
# PIPE-02: Split data
# ---------------------------------------------------------------------------

def split_data(
    X: pd.DataFrame,
    y: pd.Series,
    task: str,
    holdout_fraction: float = 0.15,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split data into working and holdout sets.

    Parameters
    ----------
    X : DataFrame
        Feature matrix.
    y : Series
        Target vector.
    task : str
        "classification" or "regression".
    holdout_fraction : float
        Fraction of data reserved for holdout (default 0.15).
    random_state : int
        Random seed for reproducibility.

    Returns
    -------
    tuple
        (X_work, X_holdout, y_work, y_holdout)
    """
    stratify = y if task == "classification" else None
    X_work, X_holdout, y_work, y_holdout = train_test_split(
        X, y,
        test_size=holdout_fraction,
        random_state=random_state,
        stratify=stratify,
    )
    return X_work, X_holdout, y_work, y_holdout


# ---------------------------------------------------------------------------
# PIPE-05: Build preprocessor
# ---------------------------------------------------------------------------

def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    """Build and fit a ColumnTransformer for numeric and categorical columns.

    Numeric columns: median imputation.
    Categorical columns: most-frequent imputation + ordinal encoding.

    Parameters
    ----------
    X : DataFrame
        Feature matrix to fit the preprocessor on.

    Returns
    -------
    ColumnTransformer
        A fitted transformer ready to call .transform().
    """
    numeric_cols = X.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = X.select_dtypes(include=["object", "category", "str"]).columns.tolist()

    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
    ])

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OrdinalEncoder(
            handle_unknown="use_encoded_value",
            unknown_value=-1,
        )),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_cols),
            ("cat", categorical_pipeline, categorical_cols),
        ],
        remainder="drop",
    )

    preprocessor.fit(X)
    return preprocessor


# ---------------------------------------------------------------------------
# PIPE-03: Evaluate
# ---------------------------------------------------------------------------

def evaluate(
    model: Any,
    X: np.ndarray | pd.DataFrame,
    y: pd.Series,
    metric: str,
    task: str,
    cv: int = 5,
) -> tuple[float, float]:
    """Cross-validate a model and return mean and std of scores.

    Parameters
    ----------
    model : estimator
        A scikit-learn compatible estimator (unfitted).
    X : array-like
        Preprocessed feature matrix.
    y : Series
        Target vector.
    metric : str
        sklearn scoring string (e.g. "accuracy", "neg_root_mean_squared_error").
    task : str
        "classification" or "regression".
    cv : int
        Number of cross-validation folds.

    Returns
    -------
    tuple[float, float]
        (mean_score, std_score)
    """
    if task == "classification":
        cv_splitter = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
    else:
        cv_splitter = KFold(n_splits=cv, shuffle=True, random_state=42)

    scores = cross_val_score(model, X, y, scoring=metric, cv=cv_splitter)
    return float(scores.mean()), float(scores.std())


# ---------------------------------------------------------------------------
# PIPE-04: Get baselines
# ---------------------------------------------------------------------------

def get_baselines(
    X: np.ndarray | pd.DataFrame,
    y: pd.Series,
    metric: str,
    task: str,
) -> dict[str, dict[str, float]]:
    """Compute dummy baseline scores for comparison.

    Parameters
    ----------
    X : array-like
        Preprocessed feature matrix.
    y : Series
        Target vector.
    metric : str
        sklearn scoring string.
    task : str
        "classification" or "regression".

    Returns
    -------
    dict
        {strategy_name: {"score": float, "std": float}}
    """
    baselines: dict[str, dict[str, float]] = {}

    if task == "classification":
        strategies = {
            "most_frequent": DummyClassifier(strategy="most_frequent"),
            "stratified": DummyClassifier(strategy="stratified", random_state=42),
        }
    else:
        strategies = {
            "mean": DummyRegressor(strategy="mean"),
            "median": DummyRegressor(strategy="median"),
        }

    for name, dummy in strategies.items():
        mean, std = evaluate(dummy, X, y, metric, task)
        baselines[name] = {"score": mean, "std": std}

    return baselines


# ---------------------------------------------------------------------------
# PIPE-06: Get data summary
# ---------------------------------------------------------------------------

def get_data_summary(
    X: pd.DataFrame,
    y: pd.Series,
    task: str,
) -> dict[str, Any]:
    """Return a summary of the dataset.

    Parameters
    ----------
    X : DataFrame
        Feature matrix.
    y : Series
        Target vector.
    task : str
        "classification" or "regression".

    Returns
    -------
    dict
        Keys: shape, dtypes, missing, target_distribution.
    """
    if task == "classification":
        target_dist = y.value_counts().to_dict()
    else:
        target_dist = {
            "mean": float(y.mean()),
            "std": float(y.std()),
            "min": float(y.min()),
            "max": float(y.max()),
        }

    return {
        "shape": tuple(X.shape),
        "dtypes": X.dtypes.value_counts().to_dict(),
        "missing": int(X.isna().sum().sum()),
        "target_distribution": target_dist,
    }
