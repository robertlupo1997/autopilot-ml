"""Frozen forecasting infrastructure module.

THIS FILE IS FROZEN. Do not modify during experiments.

Provides leakage-free temporal evaluation, forecasting metrics, and naive baselines
for time-series ML. All test-fold indices are strictly after all train-fold indices
— guaranteed by sklearn.model_selection.TimeSeriesSplit.

Dollar-scale contract (TVAL-02)
--------------------------------
``walk_forward_evaluate`` receives raw y values in their original unit (e.g., dollars).
The ``model_fn`` callable is responsible for returning predictions **in the same unit as
y_true**. If the agent applies a log-transform internally, it must inverse-transform
before returning predictions. This module does NOT apply any inverse transform.

MAPE convention (FMET-01)
--------------------------
``compute_metric("mape", ...)`` returns sklearn ``mean_absolute_percentage_error``,
which uses the **decimal** convention: 0.05 means 5%, NOT 5.0. Use thresholds like
``if mape < 0.10`` (meaning "beat 10% MAPE").

Exports
-------
- METRIC_MAP : dict[str, tuple[str, str]]
- compute_metric(metric_name, y_true, y_pred) -> float
- walk_forward_evaluate(model_fn, X, y, metric, n_splits, gap) -> list[float]
- get_forecasting_baselines(y, n_splits, gap, period) -> dict[str, float]
"""

from __future__ import annotations

import math
import warnings
from typing import Callable

import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    root_mean_squared_error,
)
from sklearn.model_selection import TimeSeriesSplit


# ---------------------------------------------------------------------------
# METRIC_MAP
# ---------------------------------------------------------------------------

METRIC_MAP: dict[str, tuple[str, str]] = {
    "mape": ("mape", "minimize"),
    "mae": ("mae", "minimize"),
    "rmse": ("rmse", "minimize"),
    "directional_accuracy": ("directional_accuracy", "maximize"),
}
"""Mapping of metric name -> (canonical_name, direction).

``direction`` is either ``"minimize"`` (lower is better, e.g. MAPE) or
``"maximize"`` (higher is better, e.g. directional accuracy).
"""


# ---------------------------------------------------------------------------
# compute_metric
# ---------------------------------------------------------------------------


def compute_metric(
    metric_name: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> float:
    """Compute a forecasting metric given true and predicted values.

    Parameters
    ----------
    metric_name : str
        One of: ``"mape"``, ``"mae"``, ``"rmse"``, ``"directional_accuracy"``.
    y_true : array-like
        Ground-truth values in dollar scale.
    y_pred : array-like
        Predicted values. MUST be in the same unit as ``y_true`` (dollar scale).
        Passing log-transformed predictions will give incorrect results.
    Returns
    -------
    float
        Metric value. For ``"mape"``, returned in decimal form (0.05 = 5%).
        For ``"directional_accuracy"``, returns NaN when len(y_true) < 2.

    Raises
    ------
    ValueError
        If ``metric_name`` is not one of the supported metrics.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    if metric_name == "mape":
        return float(mean_absolute_percentage_error(y_true, y_pred))
    elif metric_name == "mae":
        return float(mean_absolute_error(y_true, y_pred))
    elif metric_name == "rmse":
        return float(root_mean_squared_error(y_true, y_pred))
    elif metric_name == "directional_accuracy":
        if len(y_true) < 2:
            return float("nan")
        return float(np.mean(np.sign(np.diff(y_true)) == np.sign(np.diff(y_pred))))
    else:
        raise ValueError(
            f"Unknown metric: {metric_name!r}. Valid options: {sorted(METRIC_MAP)}"
        )


# ---------------------------------------------------------------------------
# walk_forward_evaluate
# ---------------------------------------------------------------------------


def walk_forward_evaluate(
    model_fn: Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray],
    X: np.ndarray,
    y: np.ndarray,
    metric: str = "mape",
    n_splits: int = 5,
    gap: int = 0,
) -> list[float]:
    """Evaluate a forecasting model using walk-forward (expanding window) CV.

    All test-fold indices are strictly greater than all train-fold indices —
    this is guaranteed by ``TimeSeriesSplit`` and verified empirically.

    Parameters
    ----------
    model_fn : Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]
        Function with signature ``model_fn(X_train, y_train, X_test) -> y_pred``.
        Must return predictions **in the same unit as y** (dollar scale).
        The function is responsible for any feature engineering; computing
        features before calling ``walk_forward_evaluate`` risks temporal leakage.
    X : np.ndarray
        Feature matrix, shape (n_samples, n_features). Must be temporally ordered
        (ascending by time index). Do NOT shuffle before calling this function.
    y : np.ndarray
        Target array in dollar scale, shape (n_samples,).
    metric : str
        Metric name. One of: ``"mape"``, ``"mae"``, ``"rmse"``,
        ``"directional_accuracy"``. Default: ``"mape"``.
    n_splits : int
        Number of walk-forward folds. Recommended minimum: 3.
        A ``UserWarning`` is issued when ``n_splits < 3``.
    gap : int
        Number of samples to skip between train end and test start.
        Useful when lag features use the most recent values.

    Returns
    -------
    list[float]
        Per-fold metric scores, length == n_splits.

    Warns
    -----
    UserWarning
        When ``n_splits < 3`` (below recommended minimum).
        When any fold's training window has fewer than 20 rows (results may be
        unreliable for small training windows).
    """
    X = np.asarray(X)
    y = np.asarray(y, dtype=float)

    if n_splits < 3:
        warnings.warn(
            f"walk_forward_evaluate: n_splits={n_splits} is below the recommended minimum of 3. "
            "Fewer folds reduce evaluation reliability.",
            UserWarning,
            stacklevel=2,
        )

    tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)
    scores: list[float] = []

    for fold_i, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train = X[train_idx]
        y_train = y[train_idx]
        X_test = X[test_idx]
        y_test = y[test_idx]

        if len(X_train) < 20:
            warnings.warn(
                f"Fold {fold_i}: training window has {len(X_train)} rows (< 20). "
                "Results may be unreliable.",
                UserWarning,
                stacklevel=2,
            )

        y_pred = model_fn(X_train, y_train, X_test)
        score = compute_metric(metric, y_test, y_pred)
        scores.append(score)

    return scores


# ---------------------------------------------------------------------------
# get_forecasting_baselines
# ---------------------------------------------------------------------------


def get_forecasting_baselines(
    y: np.ndarray,
    n_splits: int = 5,
    gap: int = 0,
    period: int = 4,
) -> dict[str, float]:
    """Compute naive and seasonal-naive MAPE baselines on walk-forward splits.

    Uses the same ``TimeSeriesSplit`` configuration as ``walk_forward_evaluate``
    to ensure baseline comparisons are on identical fold boundaries.

    Parameters
    ----------
    y : np.ndarray
        Target time series in dollar scale, shape (n_samples,).
        Must be temporally ordered (ascending by time index).
    n_splits : int
        Number of walk-forward folds. Must match the value used in
        ``walk_forward_evaluate`` for a fair comparison.
    gap : int
        Gap parameter for ``TimeSeriesSplit``. Must match ``walk_forward_evaluate``.
    period : int
        Seasonal period (e.g., 4 for quarterly, 12 for monthly).
        Used for seasonal naive lookback: ``y[test_idx[i] - period]``.

    Returns
    -------
    dict[str, float]
        ``{"naive": float, "seasonal_naive": float}`` where each value is the
        mean MAPE (decimal) across all folds.

    Notes
    -----
    **Naive forecast:** For each fold, predict ``y_train[-1]`` for all test points.

    **Seasonal naive forecast:** For each test point at global index ``i``,
    look up ``y[i - period]``. Falls back to ``y_train[-1]`` when
    ``i - period < train_idx[0]`` (insufficient history for the full seasonal
    lookback). If the entire training window has fewer rows than ``period``,
    all test points use the naive fallback for that fold.
    """
    y = np.asarray(y, dtype=float)
    X_dummy = y.reshape(-1, 1)  # TimeSeriesSplit needs a 2D array for .split()

    tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)

    naive_mapes: list[float] = []
    seasonal_mapes: list[float] = []

    for train_idx, test_idx in tscv.split(X_dummy):
        y_train = y[train_idx]
        y_test = y[test_idx]
        train_start = train_idx[0]

        # --- Naive baseline: predict last training value for all test points ---
        y_naive = np.full(len(y_test), y_train[-1])
        naive_mape = float(mean_absolute_percentage_error(y_test, y_naive))
        naive_mapes.append(naive_mape)

        # --- Seasonal naive baseline ---
        y_seasonal = np.empty(len(y_test))
        for local_i, global_i in enumerate(test_idx):
            lookback_idx = global_i - period
            if lookback_idx >= train_start:
                # Within training window: use the value from <period> steps ago
                y_seasonal[local_i] = y[lookback_idx]
            else:
                # Insufficient history: fall back to naive (last training value)
                y_seasonal[local_i] = y_train[-1]

        seasonal_mape = float(mean_absolute_percentage_error(y_test, y_seasonal))
        seasonal_mapes.append(seasonal_mape)

    return {
        "naive": float(np.mean(naive_mapes)),
        "seasonal_naive": float(np.mean(seasonal_mapes)),
    }
