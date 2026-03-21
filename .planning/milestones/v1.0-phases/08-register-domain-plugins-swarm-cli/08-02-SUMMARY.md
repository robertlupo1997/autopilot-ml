---
phase: 08-register-domain-plugins-swarm-cli
plan: 02
subsystem: cli
tags: [argparse, swarm, verifier, cli]

# Dependency graph
requires:
  - phase: 05-domain-plugins-swarm
    provides: SwarmManager, SwarmScoreboard, verify_best_result
  - phase: 08-register-domain-plugins-swarm-cli plan 01
    provides: Plugin registry wiring in CLI
provides:
  - "--swarm and --n-agents CLI flags for swarm mode"
  - "verify_best_result() wired into SwarmManager.run() return dict"
  - "Validation: --swarm+--resume conflict, --n-agents without --swarm warning"
affects: [e2e-validation, swarm]

# Tech tracking
tech-stack:
  added: []
  patterns: [lazy import for swarm in CLI, lazy verifier import in run()]

key-files:
  created: []
  modified:
    - src/mlforge/cli.py
    - src/mlforge/swarm/__init__.py
    - tests/mlforge/test_cli.py
    - tests/mlforge/test_swarm.py

key-decisions:
  - "Lazy import of SwarmManager inside if-args.swarm block to avoid heavy imports when not using swarm"
  - "Lazy import of verify_best_result inside SwarmManager.run() try block to avoid circular imports"
  - "Patch mlforge.swarm.SwarmManager (not mlforge.cli.SwarmManager) in tests because of lazy import"

patterns-established:
  - "Lazy import pattern: domain-specific imports inside conditional branches"

requirements-completed: [SWARM-01, SWARM-02, SWARM-03, SWARM-04]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 08 Plan 02: Swarm CLI and Verifier Wiring Summary

**--swarm/--n-agents CLI flags routing to SwarmManager with verify_best_result() wired into run() return dict**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T11:22:24Z
- **Completed:** 2026-03-20T11:26:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- CLI accepts --swarm flag and routes to SwarmManager (setup/run/teardown lifecycle) instead of RunEngine
- CLI accepts --n-agents to control parallel agent count, with warning when used without --swarm
- --swarm+--resume conflict is rejected with error code 1
- SwarmManager.run() calls verify_best_result() and includes "verification" key in return dict
- 458 tests passing, no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add swarm CLI and verifier wiring tests (RED)** - `d717fdb` (test)
2. **Task 2: Add swarm CLI path and wire verifier (GREEN)** - `d6764e1` (feat)

_TDD: Task 1 wrote failing tests, Task 2 made them pass._

## Files Created/Modified
- `src/mlforge/cli.py` - Added --swarm, --n-agents flags and SwarmManager code path
- `src/mlforge/swarm/__init__.py` - Added verify_best_result() call in run() with verification in return dict
- `tests/mlforge/test_cli.py` - 5 new tests for swarm CLI flags
- `tests/mlforge/test_swarm.py` - 2 new tests for verifier wiring in run()

## Decisions Made
- Lazy import of SwarmManager inside `if args.swarm` block to keep CLI lightweight when not using swarm
- Lazy import of verify_best_result inside run() try/except to avoid circular imports and gracefully handle failures
- Tests patch `mlforge.swarm.SwarmManager` rather than `mlforge.cli.SwarmManager` because the import is lazy

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Swarm mode fully reachable from CLI
- All Phase 5 swarm components (SwarmManager, SwarmScoreboard, verify_best_result) now integrated
- Ready for e2e validation testing

---
*Phase: 08-register-domain-plugins-swarm-cli*
*Completed: 2026-03-20*
