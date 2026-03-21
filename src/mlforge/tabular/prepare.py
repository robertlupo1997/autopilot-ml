"""Frozen data pipeline for tabular ML.

Provides data loading, splitting, preprocessing, evaluation, and
temporal validation utilities. This module is copied as-is into the
experiment directory -- the agent MUST NOT modify it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def load_data(path: Path) -> pd.DataFrame:
    """Load data from CSV or Parquet file.

    Detects file format from suffix: .parquet/.pq uses read_parquet,
    everything else uses read_csv.

    Args:
        path: Path to the data file.

    Returns:
        Loaded DataFrame.
    """
    path = Path(path)
    if path.suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    return pd.read_csv(path)


def split_data(
    df: pd.DataFrame,
    target_column: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split data into train and test sets.

    Args:
        df: Input DataFrame with features and target.
        target_column: Name of the target column.
        test_size: Fraction of data reserved for testing.
        random_state: Random seed for reproducibility.

    Returns:
        Tuple of (X_train, X_test, y_train, y_test).
    """
    X = df.drop(columns=[target_column])
    y = df[target_column]
    return train_test_split(X, y, test_size=test_size, random_state=random_state)


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    """Build a ColumnTransformer for numeric and categorical columns.

    Numeric columns: SimpleImputer(median) + StandardScaler.
    Categorical columns: SimpleImputer(most_frequent) + OneHotEncoder.

    Args:
        X: Feature DataFrame (no target column).

    Returns:
        Configured ColumnTransformer (unfitted).
    """
    numeric_cols = X.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()

    transformers = []

    if numeric_cols:
        numeric_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])
        transformers.append(("numeric", numeric_pipeline, numeric_cols))

    if categorical_cols:
        categorical_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])
        transformers.append(("categorical", categorical_pipeline, categorical_cols))

    return ColumnTransformer(transformers=transformers, remainder="drop")


def evaluate(
    model: Any,
    X: pd.DataFrame,
    y: pd.Series | np.ndarray,
    scoring: str,
    task: str,
    cv_splits: int = 5,
) -> dict[str, float]:
    """Score a model using cross-validation.

    Uses StratifiedKFold for classification and KFold for regression.

    Args:
        model: A scikit-learn compatible estimator.
        X: Feature matrix.
        y: Target values.
        scoring: Sklearn scoring string (e.g., 'accuracy', 'r2').
        task: Either 'classification' or 'regression'.
        cv_splits: Number of cross-validation folds.

    Returns:
        Dict with 'mean' and 'std' of cross-validation scores.
    """
    if task == "classification":
        cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    else:
        cv = KFold(n_splits=cv_splits, shuffle=True, random_state=42)

    scores = cross_val_score(model, X, y, scoring=scoring, cv=cv)
    return {"mean": float(scores.mean()), "std": float(scores.std())}


def get_data_summary(df: pd.DataFrame, target_column: str) -> dict[str, Any]:
    """Return a summary of the dataset.

    Args:
        df: Full DataFrame including target.
        target_column: Name of the target column.

    Returns:
        Dict with shape, feature_types, and target_stats.
    """
    feature_cols = [c for c in df.columns if c != target_column]
    feature_types = {}
    for col in feature_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            feature_types[col] = "numeric"
        else:
            feature_types[col] = "categorical"

    target = df[target_column]
    if pd.api.types.is_numeric_dtype(target) and target.nunique() > 10:
        target_stats = {
            "type": "continuous",
            "mean": float(target.mean()),
            "std": float(target.std()),
            "min": float(target.min()),
            "max": float(target.max()),
        }
    else:
        target_stats = {
            "type": "categorical",
            "n_classes": int(target.nunique()),
            "distribution": target.value_counts().to_dict(),
        }

    return {
        "shape": tuple(df.shape),
        "feature_types": feature_types,
        "target_stats": target_stats,
    }




def validate_no_leakage(
    df: pd.DataFrame,
    target_column: str,
    date_column: str | None = None,
) -> list[str]:
    """Check for potential data leakage indicators.

    Looks for:
    - Columns whose name contains the target column name (e.g., target_encoded)
    - Columns with suspiciously high correlation to the target

    Args:
        df: Full DataFrame.
        target_column: Name of the target column.
        date_column: Optional temporal column name.

    Returns:
        List of warning strings. Empty if no leakage detected.
    """
    warnings = []

    # Check for target-derived column names
    for col in df.columns:
        if col == target_column:
            continue
        if target_column in col:
            warnings.append(
                f"Column '{col}' contains target name '{target_column}' -- potential leakage"
            )

    # Check for very high correlation with target (numeric only)
    if pd.api.types.is_numeric_dtype(df[target_column]):
        numeric_cols = df.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            if col == target_column:
                continue
            corr = df[col].corr(df[target_column])
            if abs(corr) > 0.99:
                warnings.append(
                    f"Column '{col}' has {corr:.3f} correlation with target -- potential leakage"
                )

    return warnings
