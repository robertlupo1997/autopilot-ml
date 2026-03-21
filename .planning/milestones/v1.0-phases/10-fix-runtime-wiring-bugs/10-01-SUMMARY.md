---
phase: 10-fix-runtime-wiring-bugs
plan: 01
subsystem: engine, cli, swarm
tags: [bugfix, integration, baselines, cli-flags, subprocess]

# Dependency graph
requires:
  - phase: 01-core-engine
    provides: RunEngine, Config, CLI framework
  - phase: 05-domain-plugins-swarm
    provides: SwarmManager._build_agent_command()
provides:
  - Fixed _compute_baselines() that calls prepare.load_data()+split_data()
  - --enable-drafts CLI flag wired to config.enable_drafts
  - Clean swarm agent command without invalid --cwd flag
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [importlib dynamic module loading with function calls instead of module-level vars]

key-files:
  created: []
  modified:
    - src/mlforge/engine.py
    - src/mlforge/cli.py
    - src/mlforge/swarm/__init__.py
    - tests/mlforge/test_engine.py
    - tests/mlforge/test_cli.py
    - tests/mlforge/test_swarm.py

key-decisions:
  - "Use plugin_settings csv_path/target_column to feed prepare.load_data()+split_data() in _compute_baselines()"

patterns-established: []

requirements-completed: [INTL-01, INTL-02, INTL-05, SWARM-01]

# Metrics
duration: 2min
completed: 2026-03-20
---

# Phase 10 Plan 01: Fix Runtime Wiring Bugs Summary

**Fixed three integration bugs: dead baseline gate via load_data()/split_data() calls, --enable-drafts CLI wiring, and removed invalid --cwd from swarm agent command**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-20T14:14:01Z
- **Completed:** 2026-03-20T14:16:13Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- _compute_baselines() now calls mod.load_data() + mod.split_data() instead of reading nonexistent module-level X_train/y_train
- --enable-drafts CLI flag added and wired to config.enable_drafts = True
- Removed invalid --cwd from _build_agent_command() (subprocess.Popen already uses cwd= kwarg)
- All 468 mlforge tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Update tests for all three bug fixes (RED)** - `20fad63` (test)
2. **Task 2: Fix all three production bugs (GREEN)** - `d63d5e1` (fix)

## Files Created/Modified
- `src/mlforge/engine.py` - Fixed _compute_baselines() to use load_data()/split_data() function calls
- `src/mlforge/cli.py` - Added --enable-drafts argparse argument and config wiring
- `src/mlforge/swarm/__init__.py` - Removed --cwd from agent command list
- `tests/mlforge/test_engine.py` - Updated baseline test to use function-based prepare.py with CSV
- `tests/mlforge/test_cli.py` - Added TestEnableDraftsFlag class with 2 tests
- `tests/mlforge/test_swarm.py` - Fixed assertion to verify --cwd NOT in command

## Decisions Made
- Use plugin_settings csv_path/target_column to feed prepare.load_data()+split_data() in _compute_baselines()

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in tests/test_cli.py::test_cli_valid_args (old automl package, not mlforge) -- out of scope, not caused by our changes

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All four pending requirements (INTL-01, INTL-02, INTL-05, SWARM-01) are now satisfied
- v1.0 milestone gap closure complete

---
*Phase: 10-fix-runtime-wiring-bugs*
*Completed: 2026-03-20*
