---
phase: 09-wire-simple-mode-task-propagation
plan: 01
subsystem: cli
tags: [jinja2, profiler, tabular, template-rendering, simple-mode]

# Dependency graph
requires:
  - phase: 04-e2e-validation-ux
    provides: Dataset profiler and simple/expert mode CLI
provides:
  - Task type propagation from profiler through CLI to plugin_settings
  - Task-conditional Jinja2 template rendering (classification vs regression models)
  - Date column temporal awareness in rendered train.py
affects: [02-tabular-plugin, 07-wire-intelligence]

# Tech tracking
tech-stack:
  added: []
  patterns: [task-conditional Jinja2 blocks, profiler-to-template data flow]

key-files:
  created: []
  modified:
    - src/mlforge/cli.py
    - src/mlforge/tabular/__init__.py
    - src/mlforge/templates/tabular_train.py.j2
    - tests/mlforge/test_cli.py
    - tests/mlforge/test_tabular.py

key-decisions:
  - "Default task is classification when plugin_settings has no task key"
  - "csv_path stored as filename only (dataset_path.name) not full path"

patterns-established:
  - "Task-conditional Jinja2 blocks for model selection in templates"

requirements-completed: [UX-01, TABL-03]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 9 Plan 01: Wire Simple Mode Task Propagation Summary

**Task type flows from profiler through CLI to Jinja2 template, rendering correct models (classifiers vs regressors) and task-aware evaluate() calls**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T11:40:03Z
- **Completed:** 2026-03-20T11:43:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Simple mode now propagates task, csv_path, and target_column to plugin_settings
- Template renders classification models (RandomForestClassifier, LogisticRegression) for classification tasks
- Template renders regression models (RandomForestRegressor, Ridge) for regression tasks
- evaluate() call uses correct task type instead of hardcoded "regression"
- Date column presence triggers temporal_split awareness comment
- Full suite green: 466 tests, 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests** - `2f31dd0` (test)
2. **Task 1 (GREEN): Wire propagation + task-aware template** - `b8f8d20` (feat)
3. **Task 2: Full suite regression check** - no commit (verification-only, all 466 tests pass)

## Files Created/Modified
- `src/mlforge/cli.py` - Added task, csv_path, target_column propagation in simple mode block
- `src/mlforge/tabular/__init__.py` - Added task and date_column to template.render() call
- `src/mlforge/templates/tabular_train.py.j2` - Task-conditional model selection, evaluate task variable, temporal comment
- `tests/mlforge/test_cli.py` - 3 new tests for plugin_settings propagation
- `tests/mlforge/test_tabular.py` - 5 new tests for task-aware scaffold rendering

## Decisions Made
- Default task is classification when plugin_settings has no task key (matches existing template_context default)
- csv_path stored as filename only (dataset_path.name) not full path, since train.py runs relative to experiment dir

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Task propagation complete, simple mode now generates correct train.py for both task types
- Phase 2 (tabular plugin intelligence) can build on correct task-aware scaffolding

---
*Phase: 09-wire-simple-mode-task-propagation*
*Completed: 2026-03-20*
