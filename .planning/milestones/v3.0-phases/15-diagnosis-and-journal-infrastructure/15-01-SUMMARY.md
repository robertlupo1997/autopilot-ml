---
phase: 15-diagnosis-and-journal-infrastructure
plan: "01"
subsystem: forecasting
tags: [numpy, pandas, pearson-correlation, error-analysis, time-series, diagnostics]

# Dependency graph
requires:
  - phase: 14-e2e-validation
    provides: forecast.py frozen infrastructure (walk_forward_evaluate, get_forecasting_baselines)
provides:
  - diagnose(y_true, y_pred, dates) -> dict with worst_periods, bias, error_growth_correlation, seasonal_pattern
  - Structured actionable error analysis for the agent loop
affects:
  - phase 16: DIAG-02 will call diagnose() from the agent loop to guide next-experiment decisions
  - any experiment template that wants to report richer diagnostics beyond MAPE

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD red-green for frozen infrastructure additions (test first, implement second)"
    - "NaN sentinel for degenerate statistical cases (zero-variance Pearson r)"
    - "pd.DatetimeIndex normalisation for accepting both numpy datetime64 and DatetimeIndex"

key-files:
  created: []
  modified:
    - src/automl/forecast.py
    - tests/test_forecast.py

key-decisions:
  - "Return NaN (not 0.0) for error_growth_correlation when abs(error) has zero variance — preserves downstream distinguishability between 'no correlation' and 'incalculable'"
  - "Use np.corrcoef with explicit std guard instead of scipy.stats.pearsonr — keeps scipy out of deps"
  - "Normalise all date inputs to pd.DatetimeIndex inside diagnose() so callers can pass either numpy datetime64 or DatetimeIndex arrays"

patterns-established:
  - "Frozen infrastructure additions follow TDD: write failing test commit first, then implementation commit"
  - "diagnose() is purely diagnostic — it does not raise on edge cases, returns NaN/empty-dict gracefully"

requirements-completed: [DIAG-01]

# Metrics
duration: 3min
completed: "2026-03-15"
---

# Phase 15 Plan 01: Diagnosis and Journal Infrastructure Summary

**diagnose(y_true, y_pred, dates) added to forecast.py — returns worst_periods, directional bias, Pearson error-growth correlation, and seasonal (Q1-Q4) error pattern for agent-guided next-experiment decisions**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-15T18:32:41Z
- **Completed:** 2026-03-15T18:35:29Z
- **Tasks:** 1 (TDD: RED commit + GREEN commit)
- **Files modified:** 2

## Accomplishments

- `diagnose()` function added to `src/automl/forecast.py` after `get_forecasting_baselines()`
- 17 new test cases covering all 4 output keys, edge cases (top_n > data length, constant error, neutral bias), and numpy datetime64 input
- 360 total tests pass (0 regressions on existing 343-test suite)
- Module docstring Exports section updated to include `diagnose`

## Task Commits

1. **RED: failing tests for diagnose()** - `443e789` (test)
2. **GREEN: implement diagnose() in forecast.py** - `e58b0bf` (feat)

## Files Created/Modified

- `src/automl/forecast.py` - Added `diagnose()` function (137 lines), added `import pandas as pd` and `Union` from typing, updated Exports docstring
- `tests/test_forecast.py` - Added `TestDiagnose` class (17 tests covering DIAG-01), added `diagnose` import, added `import pandas as pd`

## Decisions Made

- Used `np.corrcoef` with explicit `std == 0` guard instead of `scipy.stats.pearsonr` — avoids adding scipy as a dependency; identical numerical result for well-behaved inputs.
- Return `NaN` (not `0.0`) for `error_growth_correlation` when the absolute error has zero variance (e.g., constant-offset predictions). Downstream consumers can distinguish "truly uncorrelated" from "incalculable".
- Normalise `dates` to `pd.DatetimeIndex` inside the function — callers may pass numpy `datetime64` arrays (as conftest does) without any conversion ceremony.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `diagnose()` is exported from `automl.forecast` and ready for Phase 16 (DIAG-02) to call from the agent loop.
- The function contract (4-key dict with typed values) is stable and documented; Phase 16 can import and call it directly.
- No blockers.

---
*Phase: 15-diagnosis-and-journal-infrastructure*
*Completed: 2026-03-15*
