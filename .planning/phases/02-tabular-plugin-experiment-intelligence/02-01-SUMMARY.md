---
phase: 02-tabular-plugin-experiment-intelligence
plan: 01
subsystem: ml-plugin
tags: [sklearn, xgboost, lightgbm, optuna, pandas, tabular, baselines, preprocessing]

requires:
  - phase: 01-core-engine
    provides: DomainPlugin Protocol, Config dataclass, template rendering (get_template_env)
provides:
  - TabularPlugin class implementing DomainPlugin Protocol
  - Frozen prepare.py data pipeline (load, split, preprocess, evaluate, temporal utils)
  - Baseline computation with DummyClassifier/DummyRegressor
  - Dual-baseline gate for keep/revert decisions
  - Jinja2 train.py template with Optuna + multi-family support
affects: [02-02, 02-03, 03-scaffold-cli, 04-e2e-validation]

tech-stack:
  added: [scikit-learn, pandas, numpy, xgboost, lightgbm, optuna, pyarrow]
  patterns: [domain-plugin-implementation, frozen-module-copy, dual-baseline-gate, guarded-ml-imports]

key-files:
  created:
    - src/mlforge/tabular/__init__.py
    - src/mlforge/tabular/prepare.py
    - src/mlforge/tabular/baselines.py
    - src/mlforge/templates/tabular_train.py.j2
    - tests/mlforge/test_tabular.py
    - tests/mlforge/test_baselines.py
  modified:
    - pyproject.toml

key-decisions:
  - "ML deps (sklearn, xgboost, lightgbm, optuna, pyarrow) added as required dependencies -- acceptable for an ML tool"
  - "prepare.py copied via Path.read_text from source module to target dir -- simple, no import-time ML dep issues"
  - "Baseline gate uses strict inequality (must beat, not tie) for both maximize and minimize directions"

patterns-established:
  - "Domain plugin scaffold pattern: copy frozen .py from source, render mutable .py from Jinja2 template"
  - "Dual-baseline gate: metric must strictly beat ALL baselines before keep"
  - "Walk-forward temporal_split: expanding window, train always before test"

requirements-completed: [TABL-01, TABL-02, TABL-03, TABL-04, TABL-05, INTL-01, INTL-02]

duration: 3min
completed: 2026-03-19
---

# Phase 2 Plan 1: TabularPlugin + Prepare + Baselines Summary

**TabularPlugin with frozen prepare.py (CSV/Parquet, sklearn preprocessing, temporal validation), dual-baseline gate, and Optuna train.py template**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T00:06:15Z
- **Completed:** 2026-03-20T00:09:30Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 7

## Accomplishments
- TabularPlugin satisfies DomainPlugin Protocol via isinstance check, with scaffold/template_context/validate_config
- Frozen prepare.py handles CSV/Parquet loading, train/test splitting, sklearn ColumnTransformer preprocessing, cross-validation evaluation, walk-forward temporal splits, and leakage detection
- Baseline module computes naive/domain-specific scores via DummyClassifier/DummyRegressor with dual-baseline gate enforcing strict improvement
- Train.py Jinja2 template renders valid Python with Optuna study, sklearn/XGBoost/LightGBM imports
- 54 new tests (all pass), 146 total tests (zero regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `a921e12` (test)
2. **Task 1 GREEN: Implementation** - `9bce424` (feat)

## Files Created/Modified
- `src/mlforge/tabular/__init__.py` - TabularPlugin class implementing DomainPlugin Protocol
- `src/mlforge/tabular/prepare.py` - Frozen data pipeline: load_data, split_data, build_preprocessor, evaluate, get_data_summary, temporal_split, validate_no_leakage
- `src/mlforge/tabular/baselines.py` - compute_baselines (DummyClassifier/DummyRegressor) and passes_baseline_gate
- `src/mlforge/templates/tabular_train.py.j2` - Mutable train.py template with Optuna + multi-family support
- `tests/mlforge/test_tabular.py` - 42 tests for plugin protocol, scaffold, template_context, validate_config, prepare.py functions
- `tests/mlforge/test_baselines.py` - 12 tests for baseline computation and dual-baseline gate
- `pyproject.toml` - Added ML dependencies (scikit-learn, pandas, numpy, xgboost, lightgbm, optuna, pyarrow)

## Decisions Made
- ML dependencies added as required (not optional) -- this is an ML tool, users need them
- prepare.py copied via Path.read_text from source module to target directory -- simple and avoids import-time ML dependency issues for core mlforge
- Baseline gate uses strict inequality (must beat, not tie) for both maximize and minimize directions
- validate_no_leakage checks column names containing target name and >0.99 correlation as leakage indicators

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- TabularPlugin ready for integration with diagnostics engine, multi-draft, and branch-on-stagnation (02-02)
- Baseline computation ready for structured results tracking (02-03)
- Plugin can be registered via register_plugin(TabularPlugin()) from Phase 1 infrastructure

---
*Phase: 02-tabular-plugin-experiment-intelligence*
*Completed: 2026-03-19*
