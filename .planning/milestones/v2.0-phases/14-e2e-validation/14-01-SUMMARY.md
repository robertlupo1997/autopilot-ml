---
phase: 14-e2e-validation
plan: 01
subsystem: testing
tags: [e2e-validation, forecasting, optuna, ridge, mape, walk-forward, frozen-files]

# Dependency graph
requires:
  - phase: 11-forecasting-infra
    provides: forecast.py (walk_forward_evaluate, seasonal_naive baseline)
  - phase: 12-forecasting-template
    provides: train.py template with Optuna tuning and dual-baseline gate
  - phase: 13-scaffold-cli
    provides: --date-column flag and forecasting scaffold mode in automl CLI
provides:
  - End-to-end validation of v2.0 forecasting loop on synthetic quarterly revenue data
  - FINDINGS.md with actual run results: EVAL-01 PASSED, EVAL-02 PASSED
  - tests/fixtures/quarterly_revenue.csv (40-quarter deterministic dataset, seed=42)
  - scripts/run-forecast-validation-test.sh (forecasting E2E validation harness)
  - tests/test_phase14_validation.py (smoke tests for fixture and harness)
affects: [v2.0-release, future-validation-phases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Validation harness pattern: scaffold → git init → claude -p → parse_run_result.py → assert EVAL criteria"
    - "FINDINGS.md pattern: run summary table, per-criterion assessment with [x]/[ ], issues table"
    - "results.tsv as authoritative best MAPE source (last json_output may reflect reverted experiment)"

key-files:
  created:
    - tests/fixtures/quarterly_revenue.csv
    - scripts/run-forecast-validation-test.sh
    - tests/test_phase14_validation.py
    - .planning/phases/14-e2e-validation/FINDINGS.md
  modified: []

key-decisions:
  - "stop_reason=tool_use is a known limitation (same as Phase 7) — agent hits max-turns wall mid-action; all deliverables are written before interruption, so this does not affect validation outcome"
  - "Best kept MAPE sourced from results.tsv (0.029063), not last json_output (0.059386) — last json_output reflects the most recent experiment which may be a reverted one"
  - "beats_seasonal_naive assertion uses the baselines field in json_output, not metric_value, so the reverted-experiment discrepancy does not cause a false failure"

patterns-established:
  - "Validation harness scripts document the json_output-vs-results.tsv MAPE discrepancy as a known limitation"
  - "Frozen file compliance verified via git diff HEAD for each frozen file (prepare.py, forecast.py)"

requirements-completed: [EVAL-01, EVAL-02]

# Metrics
duration: ~20min (Task 1 ~10min, Task 2 ~5-10min agent run, Task 3 ~5min)
completed: 2026-03-14
---

# Phase 14 Plan 01: E2E Forecasting Validation Summary

**v2.0 forecasting loop validated end-to-end: Ridge MAPE 0.029 beats seasonal naive 0.061 on 40-quarter synthetic revenue data, 7 experiments run, frozen files intact, 0 permission denials**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-14 (Task 1)
- **Completed:** 2026-03-14 (Task 3)
- **Tasks:** 3 (Tasks 1 and 3 auto; Task 2 human-action)
- **Files modified:** 4

## Accomplishments

- Synthesized a deterministic 40-quarter revenue dataset (seed=42) with trend, quarterly seasonality, and noise
- Built a complete forecasting E2E validation harness (scripts/run-forecast-validation-test.sh) with scaffold, claude -p invocation, frozen-file checks, and EVAL-01/EVAL-02 assertions
- Ran the full autonomous forecasting loop (51 turns, $1.90): agent explored 4 draft models and 3 iterations, keeping best Ridge model at MAPE 0.029063
- EVAL-01 PASSED: best MAPE 0.029063 < seasonal naive 0.060806 (52% improvement)
- EVAL-02 PASSED: 7 experiments completed, 2 keep decisions (draft-keep + keep)
- Frozen file compliance PASSED: both prepare.py and forecast.py unchanged after 51 agent turns

## Task Commits

Each task was committed atomically:

1. **Task 1: Generate dataset, harness script, smoke tests** - `bc22a1e` (feat)
2. **Task 2: Run validation script** - N/A (human-action, no commit)
3. **Task 3: Populate FINDINGS.md from run results** - `310fb87` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `tests/fixtures/quarterly_revenue.csv` — 40-quarter synthetic revenue with trend + seasonality, seed=42
- `scripts/run-forecast-validation-test.sh` — E2E validation harness for forecasting loop with EVAL-01/EVAL-02 assertions
- `tests/test_phase14_validation.py` — Smoke tests for fixture (6 tests) and harness script (9 tests)
- `.planning/phases/14-e2e-validation/FINDINGS.md` — Documented results: run summary, EVAL assessments, issues table

## Decisions Made

- Best kept MAPE sourced from results.tsv, not last json_output — the last json_output reflects the most recent experiment which may be reverted; results.tsv holds the authoritative walk-forward MAPE per kept model.
- stop_reason=tool_use treated as known limitation (documented in Phase 7 as well) — agent hits max-turns wall mid-action; all deliverables written before interruption, validation outcome unaffected.
- beats_seasonal_naive assertion uses the baselines field in json_output rather than metric_value, preventing false failure from the reverted-experiment discrepancy.

## Deviations from Plan

None — plan executed exactly as written. Task 3 used actual run data provided by user after human-action Task 2.

## Issues Encountered

1. **stop_reason=tool_use** — Agent interrupted at turn 51 mid-action rather than completing gracefully. Known limitation from Phase 7. All deliverables (results.tsv, run.log, git commits in experiment dir) were present and correct; no impact on validation outcome. No fix attempted — documented in FINDINGS.md Issue #1.

2. **json_output MAPE discrepancy** — Last json_output shows metric_value=0.059386 (from reverted iter 7) while results.tsv shows best kept MAPE of 0.029063 (iter 6 keep). The harness script already accounts for this by using beats_seasonal_naive from json_output baselines field rather than raw metric_value. Documented in FINDINGS.md Issue #2. No code change required.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- v2.0 milestone is now fully validated across all phases (11-14)
- The forecasting loop (forecast.py, train_template_forecast.py, scaffold --date-column, CLAUDE.md protocol) works end-to-end
- Known open item: graceful shutdown (stop_reason=tool_use) — the agent exits at max-turns boundary rather than completing a clean end_turn; this is a cosmetic issue that does not affect experiment integrity
- Ready for v2.0 release documentation or next milestone planning

---
*Phase: 14-e2e-validation*
*Completed: 2026-03-14*
