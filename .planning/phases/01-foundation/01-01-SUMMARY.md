---
phase: 01-foundation
plan: 01
subsystem: data-pipeline
tags: [scikit-learn, pandas, numpy, xgboost, lightgbm, preprocessing, cross-validation, tdd]

# Dependency graph
requires: []
provides:
  - "prepare.py frozen data pipeline (load, split, preprocess, evaluate, baselines, summary, metrics)"
  - "pyproject.toml with all ML dependencies installed"
  - "Test fixtures for classification, regression, and missing-data CSVs"
  - "METRIC_MAP mapping user-facing names to sklearn scoring strings"
affects: [01-02, 01-03, 02-core-loop]

# Tech tracking
tech-stack:
  added: [scikit-learn, pandas, numpy, xgboost, lightgbm, pytest, hatchling, uv]
  patterns: [ColumnTransformer preprocessing, cross_val_score evaluation, TDD red-green]

key-files:
  created:
    - pyproject.toml
    - src/automl/__init__.py
    - src/automl/prepare.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_prepare.py
  modified: []

key-decisions:
  - "OrdinalEncoder for categoricals (not one-hot) to keep column count stable for tree models"
  - "build_preprocessor fits internally and returns fitted transformer for simplicity"
  - "All metric directions are maximize (sklearn negates error metrics)"
  - "Integer target with <=20 unique values auto-detected as classification"

patterns-established:
  - "TDD workflow: write failing tests first, then implement, then refactor"
  - "Frozen pipeline pattern: prepare.py functions are never modified by the agent"
  - "METRIC_MAP as single source of truth for metric name mapping"

requirements-completed: [PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PIPE-06, PIPE-07]

# Metrics
duration: 4min
completed: 2026-03-10
---

# Phase 1 Plan 1: Data Pipeline Summary

**Frozen prepare.py with 7 PIPE functions (load, split, preprocess, evaluate, baselines, summary, metrics) plus 17 passing tests via TDD**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T13:15:45Z
- **Completed:** 2026-03-10T13:19:22Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Complete frozen data pipeline in prepare.py with all 8 public exports
- 17 tests covering classification and regression paths for all PIPE-01 through PIPE-07 behaviors
- Project scaffolding with pyproject.toml, uv sync, and all ML dependencies installed
- Reusable test fixtures for classification, regression, and missing-data CSVs

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffolding** - `88b1bf3` (chore)
2. **Task 2 RED: Failing tests** - `cecc00e` (test)
3. **Task 2 GREEN: prepare.py implementation** - `c0bb69b` (feat)

## Files Created/Modified
- `pyproject.toml` - Project config with scikit-learn, pandas, numpy, xgboost, lightgbm
- `src/automl/__init__.py` - Package marker
- `src/automl/prepare.py` - Frozen data pipeline (360 lines, 7 functions + METRIC_MAP)
- `tests/__init__.py` - Test package marker
- `tests/conftest.py` - Shared fixtures: classification/regression/missing CSV generators
- `tests/test_prepare.py` - 17 test cases across 7 test classes

## Decisions Made
- Used OrdinalEncoder (not OneHotEncoder) for categoricals -- keeps column count stable for tree models
- build_preprocessor() fits internally and returns fitted transformer for API simplicity
- All METRIC_MAP directions are "maximize" since sklearn negates error metrics
- Integer targets with <=20 unique values auto-detected as classification

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pandas deprecation warnings**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** `pd.api.types.is_categorical_dtype()` deprecated in pandas 4; `select_dtypes(include=["object"])` deprecated for string columns
- **Fix:** Replaced with `isinstance(dtype, pd.CategoricalDtype)` and added "str" to select_dtypes include list
- **Files modified:** src/automl/prepare.py
- **Verification:** All 17 tests pass with zero warnings
- **Committed in:** c0bb69b (part of GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix for deprecation)
**Impact on plan:** Minor fix for forward compatibility. No scope creep.

## Issues Encountered
- uv uses `[dependency-groups]` not `[project.optional-dependencies]` for dev deps -- fixed during scaffolding

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- prepare.py is ready for import by train.py (Plan 03)
- All PIPE-* functions tested and working for both classification and regression
- Preprocessor handles missing values and categorical encoding without leakage

## Self-Check: PASSED

All 6 files verified present. All 3 commits verified in git log.

---
*Phase: 01-foundation*
*Completed: 2026-03-10*
