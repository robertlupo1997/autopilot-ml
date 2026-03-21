---
phase: 12-wire-plugin-validation-task-mapping
plan: 01
subsystem: scaffold
tags: [validation, task-mapping, plugins, scaffold]

# Dependency graph
requires:
  - phase: 05-domain-plugins-swarm
    provides: validate_config() method on all 3 plugins (dead code until now)
provides:
  - validate_config() wired into scaffold_experiment() as pre-scaffold gate
  - _map_task_for_domain() translates profiler task types to domain-specific types
  - DL classification->image_classification and regression->custom mapping
affects: [e2e-validation, scaffold, deeplearning]

# Tech tracking
tech-stack:
  added: []
  patterns: [pre-scaffold validation gate, in-place config mutation for task mapping]

key-files:
  created: []
  modified:
    - src/mlforge/scaffold.py
    - tests/mlforge/test_scaffold.py

key-decisions:
  - "Task mapping mutates config in-place (established pattern from CLI override at line 164)"
  - "Mapping runs before validation so profiler outputs pass DL validation"
  - "Fixed existing test_scaffold_finetuning_domain to use valid FT config (metric+model_name)"

patterns-established:
  - "Pre-scaffold validation: all plugin configs validated before scaffold() call"
  - "_TASK_TYPE_MAP dict for extensible domain-specific task translation"

requirements-completed: [FT-04, DL-03, UX-01, TABL-01, DL-01, FT-01]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 12 Plan 01: Wire Plugin Validation + Task Type Mapping Summary

**validate_config() gate wired into scaffold_experiment() with _map_task_for_domain() translating profiler classification/regression to DL-native image_classification/custom**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T22:00:41Z
- **Completed:** 2026-03-20T22:04:14Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- validate_config() called on all 3 plugins before scaffold() -- closes GAP-4 (dead code)
- _map_task_for_domain() maps profiler task types to DL-native types -- closes GAP-5 (task mismatch)
- 10 new tests across TestScaffoldValidation and TestTaskTypeMapping classes
- 482 mlforge tests pass with 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for validation + mapping** - `5f3a725` (test)
2. **Task 1 (GREEN): Implement validation gate + task mapping** - `25e446f` (feat)
3. **Task 2: Full regression check** - no code changes needed (482/482 mlforge tests pass)

_Note: TDD task has two commits (test then feat)_

## Files Created/Modified
- `src/mlforge/scaffold.py` - Added _TASK_TYPE_MAP, _map_task_for_domain(), validate_config() call in scaffold_experiment()
- `tests/mlforge/test_scaffold.py` - Added TestScaffoldValidation (5 tests) and TestTaskTypeMapping (5 tests), fixed test_scaffold_finetuning_domain

## Decisions Made
- Task mapping mutates config in-place (established pattern from CLI override at line 164)
- Mapping runs before validation so profiler outputs like "classification" get translated to "image_classification" before DL validation
- Fixed existing test_scaffold_finetuning_domain to use valid FT config (metric="perplexity", model_name="test/model")

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_scaffold_finetuning_domain using invalid config**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Existing test used Config(domain="finetuning") with default metric="accuracy" (invalid for FT) and no model_name
- **Fix:** Changed to Config(domain="finetuning", metric="perplexity", plugin_settings={"model_name": "test/model"})
- **Files modified:** tests/mlforge/test_scaffold.py
- **Verification:** All 30 scaffold tests pass
- **Committed in:** 25e446f (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug in existing test)
**Impact on plan:** Essential fix -- test was passing by accident before validation was wired. No scope creep.

## Issues Encountered
- Pre-existing failure in tests/test_cli.py::test_cli_valid_args (old automl package, not mlforge) -- out of scope, logged to deferred-items.md

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plugin validation is now enforced at scaffold time for all 3 domains
- Task type mapping ensures profiler outputs work seamlessly with DL plugin
- Ready for phase 13 (E2E validation) or any remaining gap closure phases

---
*Phase: 12-wire-plugin-validation-task-mapping*
*Completed: 2026-03-20*
