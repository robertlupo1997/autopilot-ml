---
phase: 16-template-and-protocol-updates
plan: "01"
subsystem: ml-experiment-template
tags: [diagnose, forecasting, train_template_forecast, claude_forecast, experiment_journal]

# Dependency graph
requires:
  - phase: 15-diagnosis-and-journal-infrastructure
    provides: diagnose() function in forecast.py and experiments.md scaffold
provides:
  - train_template_forecast.py imports and calls diagnose() after final evaluation
  - diagnostic_output printed as structured JSON for structured parsing
  - claude_forecast.md.tmpl rule 11 instructing agent to record Error Patterns in experiments.md
affects: [17-exploration-and-stagnation, any future forecasting experiment runs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Diagnostic pass pattern: second walk_forward_evaluate with _collecting_model_fn wrapper to gather y_true/y_pred for diagnose()"
    - "diagnostic_output: prefix for structured parsing alongside metric_value: and json_output:"
    - "Protocol rule in template instructs agent to read diagnostic_output from run.log and record in experiments.md ## Error Patterns section"

key-files:
  created: []
  modified:
    - src/automl/train_template_forecast.py
    - src/automl/templates/claude_forecast.md.tmpl
    - tests/test_train_template_forecast.py

key-decisions:
  - "Collect predictions via second walk_forward_evaluate pass with _collecting_model_fn wrapper rather than modifying the Optuna objective — keeps mutable zone 1 clean"
  - "Use pd.date_range('2000-01-01', ..., freq='QS') as synthetic dates for diagnose() since actual dates are not available at template level"
  - "diagnostic_output: printed after json_output: in structured output block — agents grep both in step 6"

patterns-established:
  - "Diagnostic pass: second walk-forward evaluation after Optuna study to collect predictions for diagnose()"
  - "Structured output prefix diagnostic_output: enables grep-based extraction alongside existing metric lines"

requirements-completed: [DIAG-02, DIAG-03]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 16 Plan 01: Template and Protocol Updates Summary

**diagnose() integrated into train_template_forecast.py with diagnostic_output: structured JSON, and claude_forecast.md.tmpl rule 11 directing agent to record Error Patterns in experiments.md**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T18:49:19Z
- **Completed:** 2026-03-15T18:51:01Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `diagnose` to the frozen import line in train_template_forecast.py
- Added diagnostic pass using `_collecting_model_fn` wrapper and a second `walk_forward_evaluate` call to collect y_true/y_pred for `diagnose()`
- Printed `diagnostic_output: {json}` as structured output line after `json_output:`
- Added `experiments.md` to Files section of claude_forecast.md.tmpl with section descriptions
- Updated step 6 grep pattern to include `diagnostic_output:` alongside metric lines
- Added rule 11 instructing the agent to read `diagnostic_output:` from run.log and record findings in `## Error Patterns` section of experiments.md
- 3 new structural tests; all 52 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for diagnose() integration** - `c8e4fc7` (test)
2. **Task 1 (GREEN): Add diagnose() to train_template_forecast.py** - `2db22da` (feat)
3. **Task 2: Add DIAG-03 rule to claude_forecast.md.tmpl** - `c912352` (feat)

_Note: Task 1 followed TDD — RED commit then GREEN commit._

## Files Created/Modified

- `src/automl/train_template_forecast.py` - Added diagnose import, diagnostic collection pass, and diagnostic_output print
- `src/automl/templates/claude_forecast.md.tmpl` - Added experiments.md to Files, updated step 6 grep, added rule 11
- `tests/test_train_template_forecast.py` - Added test_imports_diagnose, test_diagnose_called_after_evaluation, test_diagnostic_output_printed, test_diag_rule_record_error_patterns

## Decisions Made

- Collect predictions via a second `walk_forward_evaluate` pass with `_collecting_model_fn` wrapper rather than modifying the Optuna objective — keeps mutable zone 1 clean and the pattern is agent-readable.
- Use synthetic `pd.date_range("2000-01-01", ..., freq="QS")` dates for `diagnose()` since actual date index is not available at template level; agents running real experiments will substitute their actual DatetimeIndex.
- Print `diagnostic_output:` after `json_output:` to maintain grep-able structured output consistency.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- DIAG-02 and DIAG-03 requirements fulfilled
- Phase 17 (Exploration and Stagnation) can proceed; it depends on EXPL-01 (best-commit tracking) which has not yet been built
- train_template_forecast.py now produces full diagnostic output for informed agent iteration

---
*Phase: 16-template-and-protocol-updates*
*Completed: 2026-03-15*
