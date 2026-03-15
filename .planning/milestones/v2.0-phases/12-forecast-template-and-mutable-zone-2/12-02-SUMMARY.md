---
phase: 12-forecast-template-and-mutable-zone-2
plan: "02"
subsystem: infra
tags: [scaffold, forecast, optuna, permissions, guard-hook, settings-json]

# Dependency graph
requires:
  - phase: 11-forecasting-infrastructure
    provides: forecast.py frozen module with walk_forward_evaluate and model_fn interface
  - phase: 12-forecast-template-and-mutable-zone-2
    provides: plan 12-01 guard hook already covers forecast.py in guard-frozen.sh
provides:
  - scaffold.py copies forecast.py byte-identical into experiment directory
  - settings.json deny list includes Edit/Write(forecast.py) defense-in-depth
  - experiment pyproject.toml includes optuna>=4.0 dependency
affects: [train_template_forecast, cli, e2e-tests]

# Tech tracking
tech-stack:
  added: [optuna>=4.0 as experiment dependency]
  patterns: [freeze-by-copy pattern extended to forecast.py alongside prepare.py]

key-files:
  created: []
  modified:
    - src/automl/scaffold.py
    - tests/test_scaffold.py

key-decisions:
  - "settings.json deny list extended to include Edit(forecast.py)/Write(forecast.py) for defense-in-depth alongside guard-frozen.sh hook"
  - "forecast.py copied byte-identical via inspect.getfile(_forecast_module) matching the established prepare.py pattern"
  - "optuna>=4.0 added to experiment pyproject.toml so Optuna is available in all experiment virtualenvs"

patterns-established:
  - "Freeze-by-copy: frozen modules copied via inspect.getfile() into experiment dir, deny-listed in settings.json, and blocked by guard-frozen.sh"

requirements-completed: [FEAT-04]

# Metrics
duration: 8min
completed: 2026-03-14
---

# Phase 12 Plan 02: Scaffold Forecast Freeze and Optuna Dependency Summary

**scaffold.py extended to copy forecast.py byte-identical, deny Edit/Write(forecast.py) in settings.json, and add optuna>=4.0 to experiment pyproject.toml**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-14T23:11:00Z
- **Completed:** 2026-03-14T23:19:45Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- Added `import automl.forecast as _forecast_module` and copy-on-scaffold to match prepare.py freeze pattern
- Extended settings.json deny list with `Edit(forecast.py)` and `Write(forecast.py)` for defense-in-depth
- Added `optuna>=4.0` to `_pyproject_content()` so every scaffolded experiment has Optuna available
- Added 4 new tests (deny list check, hook denial test, optuna dep check, forecast copy check) — all pass

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: add failing tests** - `5e21d6f` (test)
2. **Task 1 GREEN: patch scaffold.py** - `0cf457e` (feat)

**Plan metadata:** (docs commit — see below)

_Note: TDD task split into test commit (RED) and implementation commit (GREEN)_

## Files Created/Modified

- `src/automl/scaffold.py` - Added forecast module import, forecast.py copy step, deny list entries, optuna dependency
- `tests/test_scaffold.py` - Added 4 new tests; updated existing count assertion (8→9 items) and deny list exact-match assertion

## Decisions Made

- Extended existing freeze-by-copy pattern (`inspect.getfile`) to forecast.py — consistent with how prepare.py is frozen
- Updated `test_scaffold_settings_deny` exact-match assertion to include forecast.py entries (auto-fix Rule 1)
- Updated `test_scaffold_creates_all_files` item count from 8 to 9 (auto-fix Rule 1)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_scaffold_settings_deny exact match to include forecast.py**
- **Found during:** Task 1 GREEN (after patching deny list)
- **Issue:** Existing test used `assert deny == ["Edit(prepare.py)", "Write(prepare.py)"]` — exact match now fails with 4 entries
- **Fix:** Updated assertion to include all 4 deny entries in order
- **Files modified:** tests/test_scaffold.py
- **Verification:** All 27 scaffold tests pass
- **Committed in:** 5e21d6f (RED commit updated to reflect this)

**2. [Rule 1 - Bug] Updated test_scaffold_creates_all_files item count from 8 to 9**
- **Found during:** Task 1 GREEN (after adding forecast.py copy)
- **Issue:** Test asserted `len(list(out.iterdir())) == 8`; now 9 items (8 files + .claude/)
- **Fix:** Updated count to 9, added forecast.py to expected_files list
- **Files modified:** tests/test_scaffold.py
- **Verification:** All 27 scaffold tests pass
- **Committed in:** 5e21d6f (RED commit updated to reflect this)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — existing tests with hardcoded counts/exact-match lists that needed updating after new functionality was added)
**Impact on plan:** Both fixes necessary to keep the existing test suite consistent with the new behavior. No scope creep.

## Issues Encountered

- Pre-existing failure in `tests/test_train_template_forecast.py::TestClaudeForecastTemplate::test_dual_baseline_rule` — confirmed pre-existing (12-01 RED phase test for claude_forecast.md.tmpl not yet implemented). Not caused by this plan's changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- scaffold.py is fully ready for Phase 12 forecasting experiments
- Optuna available in all scaffolded experiment virtualenvs
- forecast.py freeze is enforced via three layers: guard-frozen.sh hook, settings.json deny list, and byte-identical copy pattern
- Next: 12-03 train_template_forecast.py and claude_forecast.md.tmpl (remaining 12-01 RED tests to go GREEN)

---
*Phase: 12-forecast-template-and-mutable-zone-2*
*Completed: 2026-03-14*
