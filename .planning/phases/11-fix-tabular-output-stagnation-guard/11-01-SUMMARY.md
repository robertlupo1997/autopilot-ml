---
phase: 11-fix-tabular-output-stagnation-guard
plan: 01
subsystem: engine
tags: [jinja2, json, stagnation, templates, tabular]

# Dependency graph
requires:
  - phase: 02-tabular-plugin
    provides: tabular_train.py.j2 template and stagnation.py
  - phase: 10-fix-runtime-wiring-bugs
    provides: engine wiring fixes
provides:
  - JSON metric output from tabular train.py template
  - Output Format protocol rule in CLAUDE.md template
  - None-safe stagnation branching (no crash on missing best_commit)
  - Engine guard on tried_families append
affects: [e2e-validation, tabular-plugin]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JSON metric output contract between train.py and engine"
    - "None-safe return for optional operations instead of raising"

key-files:
  created: []
  modified:
    - src/mlforge/templates/tabular_train.py.j2
    - src/mlforge/templates/base_claude.md.j2
    - src/mlforge/intelligence/stagnation.py
    - src/mlforge/engine.py
    - tests/mlforge/test_templates.py
    - tests/mlforge/test_stagnation.py
    - tests/mlforge/test_engine.py

key-decisions:
  - "Return None from trigger_stagnation_branch instead of raising ValueError for graceful degradation"
  - "Add Output Format section to base_claude.md.j2 (all domains) not just tabular-specific template"

patterns-established:
  - "JSON metric line contract: train.py prints json.dumps({metric_value: ...}) as last output line"
  - "None-guard pattern: caller checks return value before mutating state"

requirements-completed: [CORE-02, CORE-03, CORE-09, INTL-04]

# Metrics
duration: 4min
completed: 2026-03-20
---

# Phase 11 Plan 01: Fix Tabular Output and Stagnation Guard Summary

**Three P0/P1 wiring fixes: tabular JSON metric output, CLAUDE.md output format rule, and None-safe stagnation branching**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T21:35:35Z
- **Completed:** 2026-03-20T21:39:35Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Tabular train.py template now emits `json.dumps({"metric_value": ...})` instead of plain-text print, enabling engine metric parsing
- CLAUDE.md protocol template includes Output Format section instructing agents to emit JSON metric line
- `trigger_stagnation_branch()` returns None gracefully when best_commit is None instead of crashing
- Engine guards `tried_families.append` behind `if branch is not None` check
- All 473 tests pass with no regressions

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Fix tabular JSON output and CLAUDE.md output format rule**
   - `4985374` (test: failing tests for JSON output and output format)
   - `501017f` (feat: fix tabular JSON output and add output format rule)
2. **Task 2: Fix stagnation None guard and engine call site**
   - `af7bfb3` (test: failing tests for stagnation None guard)
   - `e85b606` (fix: stagnation None guard and engine tried_families protection)

## Files Created/Modified
- `src/mlforge/templates/tabular_train.py.j2` - Added `import json`, replaced print with `json.dumps` metric output
- `src/mlforge/templates/base_claude.md.j2` - Added Output Format section with metric_value instruction and revert warning
- `src/mlforge/intelligence/stagnation.py` - Changed ValueError to return None, updated return type to `str | None`
- `src/mlforge/engine.py` - Added `if branch is not None` guard before tried_families append
- `tests/mlforge/test_templates.py` - Added 4 new tests for JSON output and output format
- `tests/mlforge/test_stagnation.py` - Changed test_no_best_commit_raises to test_no_best_commit_returns_none
- `tests/mlforge/test_engine.py` - Added TestStagnationNoneGuard class with skip-branch test

## Decisions Made
- Return None from trigger_stagnation_branch instead of raising ValueError -- graceful degradation is better for autonomous overnight runs where crashing wastes the remaining budget
- Output Format section added to base_claude.md.j2 (all domains) rather than tabular-specific template -- all domains need this contract

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three P0/P1 wiring gaps are fixed
- Tabular E2E flow can now parse metric values from train.py output
- Stagnation branching is safe for sessions with no successful experiments
- Ready for E2E validation or additional gap-closure phases

---
*Phase: 11-fix-tabular-output-stagnation-guard*
*Completed: 2026-03-20*
