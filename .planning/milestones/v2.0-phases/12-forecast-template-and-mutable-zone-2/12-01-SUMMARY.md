---
phase: 12-forecast-template-and-mutable-zone-2
plan: "01"
subsystem: forecasting
tags: [optuna, sklearn, pandas, walk_forward_evaluate, lag-features, TDD]

# Dependency graph
requires:
  - phase: 11-forecasting-infrastructure
    provides: walk_forward_evaluate, get_forecasting_baselines, compute_metric from frozen forecast.py
  - phase: 11-forecasting-infrastructure
    provides: load_data with date_col, temporal_split from prepare.py

provides:
  - train_template_forecast.py with engineer_features (shift-first lag/rolling features) and Optuna objective calling walk_forward_evaluate
  - claude_forecast.md.tmpl with 10 numbered agent protocol rules (dual-baseline gate, feature cap, trial budget, MAPE direction, no-custom-CV)
  - 17 structural inspection tests covering all plan requirements

affects:
  - 12-02-scaffold-patches (adds forecast.py to deny list, optuna to pyproject)
  - 13-forecast-cli (wires train_template_forecast.py into scaffold)
  - 14-e2e-forecast-validation (runs the template end-to-end)

# Tech tracking
tech-stack:
  added: [optuna (already installed, now used in template), pandas.Series.shift for lag features]
  patterns:
    - shift-first pattern: .shift(1).rolling(N).mean() for leakage-free rolling features
    - engineer_features called inside model_fn closure (per-fold feature computation)
    - Optuna objective calls frozen walk_forward_evaluate (never custom CV loop)
    - N_TRIALS = min(50, 2 * len(y_raw)) trial budget cap
    - Dual-baseline gate enforced via CLAUDE.md protocol rule (not code)

key-files:
  created:
    - src/automl/train_template_forecast.py
    - src/automl/templates/claude_forecast.md.tmpl
    - tests/test_train_template_forecast.py
  modified: []

key-decisions:
  - "engineer_features called inside model_fn (not pre-computed) — each CV fold gets fresh features from its own training data only"
  - "Dual-baseline gate (beats both naive and seasonal_naive) enforced in CLAUDE.md as agent protocol rule, not in code — loop_helpers.should_keep() unchanged"
  - "Template uses local imports (from forecast import ...) not from automl.forecast — matches experiment directory layout where scaffold copies forecast.py"
  - "MAPE direction rule explicitly documented: keep if new_mape < best_mape, NOT should_keep() which assumes higher=better"

patterns-established:
  - "Shift-first pattern: lag/rolling features always use .shift(1) before .rolling() to prevent look-ahead leakage"
  - "Optuna objective pattern: model_fn closure with trial hyperparameters, then walk_forward_evaluate call — no custom CV"

requirements-completed: [BASE-03b, FEAT-01, FEAT-02, FEAT-03, OPTA-01, OPTA-02, OPTA-03]

# Metrics
duration: 12min
completed: 2026-03-14
---

# Phase 12 Plan 01: Forecast Template and Mutable Zone 2 Summary

**Leakage-free forecasting experiment template with Optuna hyperparameter search calling frozen walk_forward_evaluate, shift-first lag/rolling features, and 10-rule agent protocol CLAUDE.md**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-14T23:17:44Z
- **Completed:** 2026-03-14T23:29:00Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments

- Created `train_template_forecast.py` with `engineer_features` using lag_1, lag_4, yoy_growth, rolling_mean_4q (all shift-first), Optuna objective calling `walk_forward_evaluate`, dual-baseline output, and identical structured output block as `train_template.py`
- Created `claude_forecast.md.tmpl` with 10 numbered rules enforcing shift-first, 15-feature cap, min(50, 2*n_rows) trial budget, dual-baseline gate, MAPE-is-lower-better direction, no-custom-CV, and frozen file protection
- 17 structural inspection tests cover all 7 plan requirements (BASE-03b, FEAT-01..03, OPTA-01..03) — all pass, no regressions (301 total tests)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Structural tests (failing)** - `daccdcd` (test)
2. **Task 1 GREEN: train_template_forecast.py + claude_forecast.md.tmpl** - `4ae8ecf` (feat)

**Plan metadata:** TBD (docs: complete plan)

_Note: TDD task produced two commits (test RED, feat GREEN)_

## Files Created/Modified

- `src/automl/train_template_forecast.py` — Forecast mutable template: engineer_features with 4 starter features, Optuna objective calling walk_forward_evaluate, dual-baseline comparison, structured output
- `src/automl/templates/claude_forecast.md.tmpl` — Forecast-specific CLAUDE.md agent protocol with 10 numbered rules
- `tests/test_train_template_forecast.py` — 17 structural text-inspection tests for both artifacts

## Decisions Made

- Engineer features computed inside `model_fn` closure per CV fold (not pre-computed on full dataset) — the only safe pattern per 12-RESEARCH.md Pitfall 3
- MAPE direction rule made explicit in CLAUDE.md: "keep if new_mape < best_mape" — `should_keep()` not used for MAPE (assumes higher=better)
- Local imports (`from forecast import`) used, not `from automl.forecast` — matches standalone experiment directory layout
- Dual-baseline gate documented as agent protocol rule only — no code enforcement needed since `loop_helpers.should_keep()` cannot be changed

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `train_template_forecast.py` and `claude_forecast.md.tmpl` are ready for use
- Phase 12 Plan 02 (scaffold patches) can now add `forecast.py` to deny list and `optuna` to pyproject.toml template
- Phase 13 (forecast CLI) can wire `train_template_forecast.py` into `scaffold_experiment()` for `--date-column` runs

## Self-Check: PASSED

All files confirmed on disk and all commits confirmed in git history:
- FOUND: src/automl/train_template_forecast.py
- FOUND: src/automl/templates/claude_forecast.md.tmpl
- FOUND: tests/test_train_template_forecast.py
- FOUND: .planning/phases/12-forecast-template-and-mutable-zone-2/12-01-SUMMARY.md
- FOUND commit: daccdcd (test RED)
- FOUND commit: 4ae8ecf (feat GREEN)

---
*Phase: 12-forecast-template-and-mutable-zone-2*
*Completed: 2026-03-14*
