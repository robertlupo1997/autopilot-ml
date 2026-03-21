---
phase: 02-tabular-plugin-experiment-intelligence
plan: 02
subsystem: intelligence
tags: [diagnostics, multi-draft, stagnation, numpy, gitpython]

# Dependency graph
requires:
  - phase: 01-core-engine
    provides: SessionState, GitManager
provides:
  - Regression diagnostics (worst predictions, bias, feature-error correlations)
  - Classification diagnostics (misclassified samples, per-class accuracy, confused pairs)
  - Multi-draft algorithm families and selection logic
  - Branch-on-stagnation detection and branching
affects: [02-03, 03-scaffold-cli-run-engine, templates]

# Tech tracking
tech-stack:
  added: [numpy]
  patterns: [TDD red-green per module, dataclass for typed results]

key-files:
  created:
    - src/mlforge/intelligence/__init__.py
    - src/mlforge/intelligence/diagnostics.py
    - src/mlforge/intelligence/drafts.py
    - src/mlforge/intelligence/stagnation.py
    - tests/mlforge/test_diagnostics.py
    - tests/mlforge/test_drafts.py
    - tests/mlforge/test_stagnation.py
  modified: []

key-decisions:
  - "Correlate abs_error (not signed error) with features for actionable diagnostics"
  - "ALGORITHM_FAMILIES stores class names as strings (not imports) to avoid heavy deps at import time"
  - "trigger_stagnation_branch uses git.checkout + create_head for detached-HEAD-safe branching"

patterns-established:
  - "TDD per module: failing test commit, then implementation commit"
  - "Intelligence modules are pure functions + dataclasses, no side effects except stagnation branching"

requirements-completed: [INTL-03, INTL-04, INTL-05]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 2 Plan 2: Experiment Intelligence Summary

**Diagnostics engine with regression/classification error analysis, multi-draft selection across 5 algorithm families, and branch-on-stagnation from best-ever commit**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T00:06:15Z
- **Completed:** 2026-03-20T00:09:08Z
- **Tasks:** 2
- **Files created:** 7

## Accomplishments
- Diagnostics engine analyzes WHERE models fail: worst predictions, bias direction, feature-error correlations (regression) and misclassified samples, per-class accuracy, confused pairs (classification)
- Multi-draft system defines 5 algorithm families (linear, random_forest, xgboost, lightgbm, svm) with DraftResult dataclass and direction-aware selection
- Branch-on-stagnation detects consecutive reverts at configurable threshold and creates explore-{family} branch from best commit
- 28 new tests across 3 test files, all passing

## Task Commits

Each task was committed atomically (TDD: test then implementation):

1. **Task 1: Diagnostics engine** - `74f5c14` (test: RED) + `e11518e` (feat: GREEN)
2. **Task 2: Multi-draft + stagnation** - `28a7f08` (test: RED) + `378ef5e` (feat: GREEN)

## Files Created/Modified
- `src/mlforge/intelligence/__init__.py` - Package init for intelligence subsystem
- `src/mlforge/intelligence/diagnostics.py` - diagnose_regression and diagnose_classification functions
- `src/mlforge/intelligence/drafts.py` - ALGORITHM_FAMILIES dict, DraftResult dataclass, select_best_draft
- `src/mlforge/intelligence/stagnation.py` - check_stagnation and trigger_stagnation_branch
- `tests/mlforge/test_diagnostics.py` - 12 tests for regression and classification diagnostics
- `tests/mlforge/test_drafts.py` - 9 tests for algorithm families and draft selection
- `tests/mlforge/test_stagnation.py` - 7 tests for stagnation detection and branching

## Decisions Made
- Correlate abs_error (not signed error) with features -- absolute error is more actionable for feature engineering
- ALGORITHM_FAMILIES stores class names as strings to avoid importing sklearn/xgboost/lightgbm at module level
- trigger_stagnation_branch uses repo.git.checkout for detached HEAD then create_head for clean branch creation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test data for feature correlation test**
- **Found during:** Task 1 (Diagnostics engine)
- **Issue:** Test used signed error correlated with feature, but implementation correlates abs_error -- negative values lose correlation after abs()
- **Fix:** Changed test to use positive-only feature values so abs_error = error = feature
- **Files modified:** tests/mlforge/test_diagnostics.py
- **Verification:** Correlation test passes with >0.9 coefficient
- **Committed in:** e11518e (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test data)
**Impact on plan:** Minor test data correction. No scope creep.

## Issues Encountered
- Pre-existing test_tabular.py failure (from 02-01 plan) -- out of scope, not caused by this plan's changes

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Intelligence subsystem complete: diagnostics, drafts, and stagnation modules ready
- Plan 02-03 (diff-aware journal + structured results) can proceed
- Stagnation module integrates with GitManager and SessionState from Phase 1

---
*Phase: 02-tabular-plugin-experiment-intelligence*
*Completed: 2026-03-20*
