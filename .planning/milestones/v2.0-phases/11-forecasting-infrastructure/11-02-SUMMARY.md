---
phase: 11-forecasting-infrastructure
plan: "02"
subsystem: data-pipeline
tags: [pandas, datetime, temporal-split, time-series, prepare, backwards-compatible]

# Dependency graph
requires:
  - phase: 11-01
    provides: forecast.py frozen module with walk_forward_evaluate and MAPE

provides:
  - load_data extended with optional date_col parameter (DatetimeIndex, sorted)
  - temporal_split function for time-ordered train/holdout splitting without shuffle
  - sample_forecast_csv pytest fixture (40-row quarterly revenue CSV)

affects:
  - Phase 12 (train_template_forecast.py will call load_data with date_col and temporal_split)
  - Any future forecasting pipeline that needs time-ordered data loading and splitting

# Tech tracking
tech-stack:
  added: [math (stdlib)]
  patterns:
    - Backwards-compatible extension via optional parameter (date_col=None default)
    - TDD: RED commit before GREEN implementation
    - temporal_split uses math.floor for deterministic split boundary

key-files:
  created: []
  modified:
    - src/automl/prepare.py
    - tests/test_prepare.py
    - tests/conftest.py

key-decisions:
  - "date_col defaults to None to preserve exact backwards compatibility with PIPE-01 through PIPE-07"
  - "temporal_split uses math.floor (not round or ceil) to match plan specification for 40-row/0.15 -> 34/6 split"
  - "Task inference in load_data unchanged when date_col provided: continuous float revenue correctly infers as regression"

patterns-established:
  - "Extend frozen modules via optional parameter with None default — callers unaffected unless they opt in"
  - "temporal_split doc states pre-sort requirement: caller must ensure ascending time order before calling"

requirements-completed: []

# Metrics
duration: 4min
completed: 2026-03-14
---

# Phase 11 Plan 02: Forecasting Infrastructure — prepare.py Extensions Summary

**Backwards-compatible load_data date_col extension and temporal_split function added to prepare.py for time-ordered CSV loading and no-shuffle train/holdout splitting**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-14T21:46:00Z
- **Completed:** 2026-03-14T21:47:05Z
- **Tasks:** 1 (TDD: 2 commits — test RED + feat GREEN)
- **Files modified:** 3

## Accomplishments

- Extended `load_data` with `date_col: str | None = None` parameter — parses dates, sets DatetimeIndex, sorts ascending; None preserves existing behaviour exactly
- Added `temporal_split(X, y, holdout_fraction=0.15)` — math.floor split returning (X_train, X_holdout, y_train, y_holdout) in time order with no shuffle
- Added `sample_forecast_csv` fixture to conftest.py — 40-row quarterly revenue CSV (Q1 2015 to Q4 2024) with trend and seasonality
- 9 new tests across TestLoadDataForecast and TestTemporalSplit; all 280 tests in the full suite pass

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing tests** - `18f665c` (test)
2. **Task 1 GREEN: Implement load_data date_col + temporal_split** - `c2bc680` (feat)

_Note: TDD task split into RED (test) and GREEN (implementation) commits_

## Files Created/Modified

- `src/automl/prepare.py` — Extended with `import math`, `date_col` parameter on `load_data`, and new `temporal_split` function
- `tests/test_prepare.py` — Added `TestLoadDataForecast` (5 tests) and `TestTemporalSplit` (4 tests); added `temporal_split` to imports
- `tests/conftest.py` — Added `sample_forecast_csv` fixture (40-row quarterly revenue CSV)

## Decisions Made

- `date_col` defaults to `None` to preserve exact backwards compatibility with all PIPE-01 through PIPE-07 callers
- `math.floor` used for split boundary to match plan spec: 40 rows * (1 - 0.15) = 34.0 -> floor -> 34 train, 6 holdout
- Task inference code unchanged when `date_col` is provided — continuous float revenue naturally infers as "regression"

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `load_data(csv, target, date_col="date")` and `temporal_split(X, y)` are importable from `automl.prepare`
- Phase 12 (train_template_forecast.py) can now call these functions to load and split time-ordered CSVs
- All 280 existing tests pass — no regressions in classification/regression pipeline

---
*Phase: 11-forecasting-infrastructure*
*Completed: 2026-03-14*
