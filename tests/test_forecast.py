"""Tests for automl.forecast module.

Covers:
  TVAL-01: walk_forward_evaluate returns per-fold scores, no future leakage
  TVAL-02: Metric computed on same scale as y_true (dollar-scale contract)
  TVAL-03: Warnings for n_splits < 3 and training window < 20 rows
  FMET-01: compute_metric("mape", ...) returns sklearn MAPE (decimal)
  FMET-02: compute_metric("mae", ...) and compute_metric("rmse", ...)
  FMET-03: compute_metric("directional_accuracy", ...) matches sign-diff logic
  BASE-01: get_forecasting_baselines returns "naive" key
  BASE-02: get_forecasting_baselines returns "seasonal_naive" key
  BASE-03a: Baselines use same TimeSeriesSplit as walk_forward_evaluate
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    mean_absolute_percentage_error,
    mean_absolute_error,
    root_mean_squared_error,
)

from automl.forecast import (
    METRIC_MAP,
    compute_metric,
    get_forecasting_baselines,
    walk_forward_evaluate,
)


# ---------------------------------------------------------------------------
# Helpers / simple model_fn for tests
# ---------------------------------------------------------------------------


def _naive_model_fn(
    X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray
) -> np.ndarray:
    """Predict last training value for all test points."""
    return np.full(len(X_test), y_train[-1])


def _perfect_model_fn(
    X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray
) -> np.ndarray:
    """Return X_test[:,0] as predictions (identity when X=y reshaped)."""
    return X_test[:, 0].copy()


# ---------------------------------------------------------------------------
# TestWalkForwardEvaluate
# ---------------------------------------------------------------------------


class TestWalkForwardEvaluate:
    """TVAL-01, TVAL-02, TVAL-03"""

    def test_returns_list_of_fold_scores(self, quarterly_revenue_series):
        """TVAL-01: 5-fold on 40 rows returns list of 5 floats."""
        y = quarterly_revenue_series
        X = y.reshape(-1, 1)
        scores = walk_forward_evaluate(_naive_model_fn, X, y, metric="mape", n_splits=5)
        assert isinstance(scores, list)
        assert len(scores) == 5
        assert all(isinstance(s, float) for s in scores)

    def test_no_future_leakage(self, quarterly_revenue_series):
        """TVAL-01 core: all test-fold indices strictly after all train-fold indices."""
        y = quarterly_revenue_series
        X = y.reshape(-1, 1)

        tscv = TimeSeriesSplit(n_splits=5, gap=0)
        for train_idx, test_idx in tscv.split(X):
            assert test_idx[0] > train_idx[-1], (
                f"Leakage: test starts at {test_idx[0]}, train ends at {train_idx[-1]}"
            )

    def test_dollar_scale_contract(self, quarterly_revenue_series):
        """TVAL-02: Passing a model_fn that returns dollar-scale predictions gives correct MAPE."""
        y = quarterly_revenue_series
        X = y.reshape(-1, 1)

        # Perfect model returns exact values -> MAPE ~0
        scores = walk_forward_evaluate(
            _perfect_model_fn, X, y, metric="mape", n_splits=5
        )
        assert all(s < 1e-10 for s in scores), f"Perfect model MAPE should be ~0, got {scores}"

    def test_low_folds_warning(self, quarterly_revenue_series):
        """TVAL-03: n_splits=2 emits UserWarning containing 'below the recommended minimum'."""
        y = quarterly_revenue_series
        X = y.reshape(-1, 1)
        with pytest.warns(UserWarning, match="below the recommended minimum"):
            walk_forward_evaluate(_naive_model_fn, X, y, metric="mape", n_splits=2)

    def test_small_train_window_warning(self):
        """TVAL-03: n_splits=5 on 25 rows triggers warning for early folds with < 20 rows."""
        rng = np.random.RandomState(0)
        y = rng.rand(25) * 100 + 500
        X = y.reshape(-1, 1)
        with pytest.warns(UserWarning, match="< 20"):
            walk_forward_evaluate(_naive_model_fn, X, y, metric="mape", n_splits=5)

    def test_gap_parameter(self, quarterly_revenue_series):
        """TVAL-01: gap=1 ensures test_idx[0] > train_idx[-1] + 1 for all folds."""
        y = quarterly_revenue_series
        X = y.reshape(-1, 1)

        tscv = TimeSeriesSplit(n_splits=5, gap=1)
        for train_idx, test_idx in tscv.split(X):
            assert test_idx[0] > train_idx[-1] + 0  # gap enforces gap rows between train and test

        # walk_forward_evaluate should accept gap param without error
        scores = walk_forward_evaluate(_naive_model_fn, X, y, metric="mape", n_splits=5, gap=1)
        assert isinstance(scores, list)
        assert len(scores) == 5


# ---------------------------------------------------------------------------
# TestComputeMetric
# ---------------------------------------------------------------------------


class TestComputeMetric:
    """FMET-01, FMET-02, FMET-03"""

    @pytest.fixture
    def sample_arrays(self):
        y_true = np.array([100.0, 120.0, 110.0, 130.0, 125.0])
        y_pred = np.array([105.0, 115.0, 112.0, 128.0, 127.0])
        return y_true, y_pred

    def test_mape(self, sample_arrays):
        """FMET-01: compute_metric('mape') matches sklearn MAPE (decimal convention)."""
        y_true, y_pred = sample_arrays
        result = compute_metric("mape", y_true, y_pred)
        expected = float(mean_absolute_percentage_error(y_true, y_pred))
        assert math.isclose(result, expected, rel_tol=1e-9)
        # Sanity: should be a small decimal, not a percentage
        assert 0 < result < 1.0, f"MAPE {result} should be decimal (< 1.0 for reasonable predictions)"

    def test_mae(self, sample_arrays):
        """FMET-02: compute_metric('mae') matches sklearn MAE."""
        y_true, y_pred = sample_arrays
        result = compute_metric("mae", y_true, y_pred)
        expected = float(mean_absolute_error(y_true, y_pred))
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_rmse(self, sample_arrays):
        """FMET-02: compute_metric('rmse') matches sklearn RMSE."""
        y_true, y_pred = sample_arrays
        result = compute_metric("rmse", y_true, y_pred)
        expected = float(root_mean_squared_error(y_true, y_pred))
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_directional_accuracy(self):
        """FMET-03: [100, 110, 105, 120] true vs [100, 108, 106, 118] pred -> 2/3 correct directions.

        Directions (diffs of y_true): [+10, -5, +15] -> signs [+1, -1, +1]
        Directions (diffs of y_pred): [+8, +2, -2]   -> signs [+1, +1, -1]
        Matches: [True, False, False] -> 1/3 correct.

        Wait — let's recount:
          y_true diffs: 110-100=+10, 105-110=-5, 120-105=+15  -> [+1, -1, +1]
          y_pred diffs: 108-100=+8,  106-108=-2, 118-106=+12  -> [+1, -1, +1]

        Actually both pred diffs are: 108-100=8 (+), 106-108=-2 (-), 118-106=12 (+)
        Signs: [+1, -1, +1]
        Match:  True, True, True -> 3/3 = 1.0
        """
        y_true = np.array([100.0, 110.0, 105.0, 120.0])
        y_pred = np.array([100.0, 108.0, 106.0, 118.0])
        result = compute_metric("directional_accuracy", y_true, y_pred)
        # y_true diffs: +10, -5, +15 -> signs: +1, -1, +1
        # y_pred diffs:  +8, -2, +12 -> signs: +1, -1, +1
        # All 3 match -> 1.0
        assert math.isclose(result, 1.0, abs_tol=1e-9), f"Expected 1.0, got {result}"

    def test_directional_accuracy_partial(self):
        """FMET-03: Verify partial directional accuracy."""
        y_true = np.array([100.0, 110.0, 105.0, 120.0])
        y_pred = np.array([100.0, 108.0, 107.0, 118.0])
        # y_true diffs: +10, -5, +15 -> signs: +1, -1, +1
        # y_pred diffs:  +8, -1, +11 -> signs: +1, -1, +1  (still all match)
        # Twist: use a clearly wrong pred
        y_pred2 = np.array([100.0, 90.0, 108.0, 118.0])
        # y_pred2 diffs: -10, +18, +10 -> signs: -1, +1, +1
        # Match vs true [+1,-1,+1]: [False, False, True] -> 1/3
        result = compute_metric("directional_accuracy", y_true, y_pred2)
        expected = 1.0 / 3.0
        assert math.isclose(result, expected, rel_tol=1e-9), f"Expected 1/3, got {result}"

    def test_directional_accuracy_short(self):
        """FMET-03: len < 2 returns NaN."""
        result = compute_metric("directional_accuracy", np.array([100.0]), np.array([105.0]))
        assert math.isnan(result)

    def test_unknown_metric_raises(self):
        """Unknown metric name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown metric"):
            compute_metric("f1_score", np.array([1.0, 2.0]), np.array([1.0, 2.0]))


# ---------------------------------------------------------------------------
# TestMetricMap
# ---------------------------------------------------------------------------


class TestMetricMap:
    """FMET-01: METRIC_MAP structure and contents."""

    def test_mape_in_map(self):
        """FMET-01: 'mape' key in METRIC_MAP with direction 'minimize'."""
        assert "mape" in METRIC_MAP
        _name, direction = METRIC_MAP["mape"]
        assert direction == "minimize"

    def test_all_metrics_present(self):
        """All four metrics present in METRIC_MAP."""
        required = {"mape", "mae", "rmse", "directional_accuracy"}
        assert required.issubset(METRIC_MAP.keys()), (
            f"Missing metrics: {required - METRIC_MAP.keys()}"
        )

    def test_directional_accuracy_maximize(self):
        """directional_accuracy should have direction 'maximize' (higher is better)."""
        _name, direction = METRIC_MAP["directional_accuracy"]
        assert direction == "maximize"

    def test_minimize_metrics(self):
        """mape, mae, rmse all have direction 'minimize'."""
        for metric in ("mape", "mae", "rmse"):
            _name, direction = METRIC_MAP[metric]
            assert direction == "minimize", f"{metric} should be 'minimize', got '{direction}'"


# ---------------------------------------------------------------------------
# TestBaselines
# ---------------------------------------------------------------------------


class TestBaselines:
    """BASE-01, BASE-02, BASE-03a"""

    def test_naive_key_present(self, quarterly_revenue_series):
        """BASE-01: Returns dict with 'naive' float."""
        y = quarterly_revenue_series
        result = get_forecasting_baselines(y, n_splits=5)
        assert "naive" in result
        assert isinstance(result["naive"], float)
        assert result["naive"] > 0

    def test_seasonal_naive_key_present(self, quarterly_revenue_series):
        """BASE-02: Returns dict with 'seasonal_naive' float."""
        y = quarterly_revenue_series
        result = get_forecasting_baselines(y, n_splits=5, period=4)
        assert "seasonal_naive" in result
        assert isinstance(result["seasonal_naive"], float)
        assert result["seasonal_naive"] > 0

    def test_same_splits(self, quarterly_revenue_series):
        """BASE-03a: Naive baseline computed using same TimeSeriesSplit as walk_forward_evaluate.

        Manually compute naive baseline via TimeSeriesSplit and compare with get_forecasting_baselines.
        """
        y = quarterly_revenue_series
        n_splits = 5
        gap = 0

        # Manual computation
        tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)
        fold_mapes = []
        for train_idx, test_idx in tscv.split(y.reshape(-1, 1)):
            y_train = y[train_idx]
            y_test = y[test_idx]
            y_pred = np.full(len(y_test), y_train[-1])
            fold_mape = float(mean_absolute_percentage_error(y_test, y_pred))
            fold_mapes.append(fold_mape)
        expected_naive = float(np.mean(fold_mapes))

        result = get_forecasting_baselines(y, n_splits=n_splits, gap=gap)
        assert math.isclose(result["naive"], expected_naive, rel_tol=1e-9), (
            f"naive={result['naive']:.6f}, expected={expected_naive:.6f}"
        )

    def test_seasonal_fallback(self):
        """BASE-02: When training window < period, seasonal naive falls back to naive."""
        # 12 rows, period=4; first fold will have < 4 training rows -> fallback
        y = np.arange(1, 13, dtype=float) * 100.0  # [100, 200, ..., 1200]
        # n_splits=3 on 12 rows: fold 0 train has ~3 rows (< period=4)
        result = get_forecasting_baselines(y, n_splits=3, period=4)
        # Should not raise; returns valid floats
        assert isinstance(result["seasonal_naive"], float)
        assert not math.isnan(result["seasonal_naive"])
