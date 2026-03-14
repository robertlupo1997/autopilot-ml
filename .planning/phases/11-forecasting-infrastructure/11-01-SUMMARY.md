---
phase: 11-forecasting-infrastructure
plan: "01"
subsystem: forecast-infrastructure
tags: [forecast, time-series, walk-forward, metrics, baselines, tdd, frozen-module]
dependency_graph:
  requires: []
  provides:
    - automl.forecast.walk_forward_evaluate
    - automl.forecast.compute_metric
    - automl.forecast.METRIC_MAP
    - automl.forecast.get_forecasting_baselines
  affects:
    - src/automl/scaffold.py (guard-frozen.sh adds forecast.py to FROZEN_FILES)
    - tests/conftest.py (quarterly_revenue_series fixture added)
tech_stack:
  added: []
  patterns:
    - TDD (RED/GREEN protocol)
    - Walk-forward expanding-window CV via sklearn TimeSeriesSplit
    - Dollar-scale MAPE via sklearn mean_absolute_percentage_error (decimal convention)
    - Seasonal naive via index arithmetic on full series (no statsmodels)
    - UserWarning guards for n_splits < 3 and fold training window < 20 rows
    - Frozen module pattern (guard-frozen.sh hook protection)
key_files:
  created:
    - src/automl/forecast.py
    - tests/test_forecast.py
  modified:
    - tests/conftest.py
    - src/automl/scaffold.py
decisions:
  - "guard hook updated in plan 11-01 (not deferred to Phase 12) to protect forecast.py immediately after creation"
  - "seasonal naive uses index arithmetic on full y array (no statsmodels, no prophet)"
  - "model_fn dollar-scale contract documented in walk_forward_evaluate docstring (no auto-inverse-transform in infrastructure)"
  - "MAPE decimal convention documented: 0.05 = 5%, use thresholds like mape < 0.10"
metrics:
  duration: "3m 13s"
  completed_date: "2026-03-14"
  tasks_completed: 1
  tasks_planned: 1
  files_created: 2
  files_modified: 2
---

# Phase 11 Plan 01: Forecasting Infrastructure (forecast.py) Summary

**One-liner:** Frozen `forecast.py` module with walk-forward CV using `TimeSeriesSplit`, MAPE/MAE/RMSE/directional-accuracy metrics, and naive/seasonal-naive baselines — all protected by guard-frozen.sh.

## What Was Built

`src/automl/forecast.py` is the frozen temporal evaluation infrastructure that all Phase 12+ forecasting experiments depend on. It exports four public symbols:

- **`METRIC_MAP`** — maps metric names to `(canonical_name, direction)` tuples for mape/mae/rmse/directional_accuracy
- **`compute_metric(metric_name, y_true, y_pred)`** — delegates to sklearn metrics; directional accuracy via `np.sign(np.diff(...))` comparison; NaN for series < 2 points
- **`walk_forward_evaluate(model_fn, X, y, metric, n_splits, gap)`** — expanding-window CV via `TimeSeriesSplit`; UserWarning when `n_splits < 3` or fold train window < 20 rows; returns `list[float]` of per-fold scores
- **`get_forecasting_baselines(y, n_splits, gap, period)`** — naive (last-train-value) and seasonal-naive (`y[test_idx - period]` with fallback to naive) baselines on identical fold boundaries as `walk_forward_evaluate`

The guard-frozen.sh hook in `scaffold.py` now lists `FROZEN_FILES="prepare.py forecast.py"` so agents cannot modify the frozen infrastructure.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| RED  | Add quarterly_revenue_series fixture + 21 failing test functions | 9fd3eab | done |
| GREEN | Create forecast.py + update scaffold.py guard hook | 3e798a7 | done |

## Verification Results

```
uv run pytest tests/test_forecast.py -x -q
→ 21 passed, 7 warnings in 1.00s

uv run pytest -x -q
→ 271 passed, 7 warnings in 30.28s (no regressions)

python -c "from automl.forecast import walk_forward_evaluate, compute_metric, get_forecasting_baselines, METRIC_MAP; print('All exports available')"
→ All exports available

grep -q 'forecast.py' src/automl/scaffold.py && echo OK
→ OK (forecast.py in FROZEN_FILES)
```

## Requirements Covered

| Req ID | Status | Test |
|--------|--------|------|
| TVAL-01 | PASS | test_returns_list_of_fold_scores, test_no_future_leakage, test_gap_parameter |
| TVAL-02 | PASS | test_dollar_scale_contract |
| TVAL-03 | PASS | test_low_folds_warning, test_small_train_window_warning |
| FMET-01 | PASS | test_mape, test_mape_in_map, test_all_metrics_present |
| FMET-02 | PASS | test_mae, test_rmse, test_minimize_metrics |
| FMET-03 | PASS | test_directional_accuracy, test_directional_accuracy_partial, test_directional_accuracy_short |
| BASE-01 | PASS | test_naive_key_present |
| BASE-02 | PASS | test_seasonal_naive_key_present, test_seasonal_fallback |
| BASE-03a | PASS | test_same_splits |

## Deviations from Plan

None — plan executed exactly as written.

The 7 pytest warnings are expected UserWarnings from walk_forward_evaluate (small training windows on the 40-row fixture), confirming the warning guard is working correctly. They are not failures.

## Self-Check: PASSED

- `src/automl/forecast.py` — FOUND
- `tests/test_forecast.py` — FOUND
- `tests/conftest.py` (quarterly_revenue_series) — FOUND
- `src/automl/scaffold.py` (forecast.py in FROZEN_FILES) — FOUND
- Commit 9fd3eab (RED tests) — FOUND
- Commit 3e798a7 (GREEN impl) — FOUND
