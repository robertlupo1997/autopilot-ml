"""Dataset profiling and auto-detection for simple mode.

Analyzes a DataFrame to determine task type (classification/regression),
appropriate metric, date columns, and data characteristics. Used by the
CLI to auto-configure experiments when the user provides only dataset + goal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from mlforge.tabular.prepare import validate_no_leakage


@dataclass
class DatasetProfile:
    """Profile of a dataset for auto-configuration."""

    task: str  # "classification" or "regression"
    metric: str  # e.g. "accuracy", "f1_weighted", "r2"
    direction: str  # "maximize" or "minimize"
    n_rows: int
    n_features: int
    numeric_features: list[str] = field(default_factory=list)
    categorical_features: list[str] = field(default_factory=list)
    date_columns: list[str] = field(default_factory=list)
    target_stats: dict = field(default_factory=dict)
    missing_pct: float = 0.0
    leakage_warnings: list[str] = field(default_factory=list)


def _detect_date_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    """Detect which columns contain date/datetime values.

    Checks datetime64 dtype first. For object columns, samples the first
    20 non-null values and attempts pd.to_datetime parsing -- accepts if
    >80% of sampled values parse successfully.

    Args:
        df: The DataFrame to inspect.
        columns: Column names to check.

    Returns:
        List of column names that contain date values.
    """
    date_cols: list[str] = []
    for col in columns:
        if col not in df.columns:
            continue
        # datetime64 dtype is always a date column
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            date_cols.append(col)
            continue
        # For object columns, try parsing a sample
        if pd.api.types.is_string_dtype(df[col]):
            try:
                sample = df[col].dropna().head(20)
                if len(sample) == 0:
                    continue
                parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
                parse_rate = parsed.notna().sum() / len(sample)
                if parse_rate > 0.8:
                    date_cols.append(col)
            except Exception:
                continue
    return date_cols


def profile_dataset(df: pd.DataFrame, target_column: str) -> DatasetProfile:
    """Profile a dataset to auto-detect task type, metric, and characteristics.

    Args:
        df: The full DataFrame including target column.
        target_column: Name of the target/label column.

    Returns:
        DatasetProfile with auto-detected settings and data characteristics.
    """
    # Input validation
    if df.empty:
        raise ValueError("Dataset is empty (0 rows)")
    if target_column not in df.columns:
        raise ValueError(
            f"Target column '{target_column}' not found. "
            f"Available columns: {list(df.columns)}"
        )
    if df[target_column].isna().all():
        raise ValueError(f"Target column '{target_column}' is entirely NaN")

    n_rows = len(df)
    feature_cols = [c for c in df.columns if c != target_column]
    n_features = len(feature_cols)

    if n_features == 0:
        raise ValueError("Dataset has only one column; need at least a target and one feature")
    if df[feature_cols].isna().all(axis=None):
        raise ValueError("All feature columns are entirely NaN")

    # Feature type detection
    numeric_features: list[str] = []
    categorical_features: list[str] = []
    for col in feature_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_features.append(col)
        else:
            categorical_features.append(col)

    # Date column detection (check all non-numeric feature columns + datetime numerics)
    candidate_cols = [c for c in feature_cols if not pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_datetime64_any_dtype(df[c])]
    # Also check numeric columns that might be datetime64
    for c in feature_cols:
        if pd.api.types.is_datetime64_any_dtype(df[c]) and c not in candidate_cols:
            candidate_cols.append(c)
    date_columns = _detect_date_columns(df, candidate_cols)

    # Missing data percentage
    if n_rows > 0 and len(df.columns) > 0:
        total_cells = n_rows * len(df.columns)
        missing_cells = df.isna().sum().sum()
        missing_pct = (missing_cells / total_cells) * 100.0
    else:
        missing_pct = 0.0

    # Task detection
    target = df[target_column] if target_column in df.columns else pd.Series(dtype=float)
    is_numeric = pd.api.types.is_numeric_dtype(target)
    n_unique = target.nunique()

    if is_numeric and n_unique > 20:
        task = "regression"
    else:
        task = "classification"

    # Metric selection
    if task == "regression":
        metric = "r2"
        direction = "maximize"
        target_stats = {
            "type": "regression",
            "mean": float(target.mean()) if n_rows > 0 else 0.0,
            "std": float(target.std()) if n_rows > 0 else 0.0,
        }
    else:
        direction = "maximize"
        if n_unique <= 2:
            metric = "accuracy"
        else:
            metric = "f1_weighted"
        target_stats = {
            "type": "classification",
            "n_classes": n_unique,
            "distribution": target.value_counts().to_dict() if n_rows > 0 else {},
        }

    leakage_warnings = validate_no_leakage(df, target_column)

    return DatasetProfile(
        task=task,
        metric=metric,
        direction=direction,
        n_rows=n_rows,
        n_features=n_features,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        date_columns=date_columns,
        target_stats=target_stats,
        missing_pct=missing_pct,
        leakage_warnings=leakage_warnings,
    )
