---
phase: 02-core-loop
plan: 01
subsystem: loop-orchestration
tags: [dataclass, decision-logic, stagnation, crash-detection, git-revert]

requires:
  - phase: 01-foundation
    provides: GitManager with commit/revert, ExperimentResult dataclass
provides:
  - LoopState dataclass for tracking iteration state
  - should_keep() keep/revert decision function
  - is_stagnating() consecutive revert detection
  - is_crash_stuck() consecutive crash detection
  - suggest_strategy_shift() diversification helper
  - GitManager.revert_last_commit() for undoing committed experiments
affects: [02-02-PLAN, 02-03-PLAN, CLAUDE.md loop protocol]

tech-stack:
  added: []
  patterns: [dataclass-with-defaults, pure-function-helpers, threshold-based-detection]

key-files:
  created:
    - src/automl/loop_helpers.py
    - tests/test_loop_helpers.py
  modified:
    - src/automl/git_ops.py
    - tests/test_git.py

key-decisions:
  - "Strict greater-than for should_keep: equal scores are NOT improvements"
  - "Configurable thresholds via LoopState fields (stagnation=5, crash=3)"
  - "Strategy cycling: when all categories tried, restart from first"

patterns-established:
  - "Pure function helpers: decision logic in standalone functions taking LoopState"
  - "TDD for all loop logic: RED commit, GREEN commit pattern"

requirements-completed: [LOOP-01, LOOP-04, LOOP-05, LOOP-06, LOOP-07, LOOP-08]

duration: 2min
completed: 2026-03-10
---

# Phase 02 Plan 01: Loop Helpers Summary

**Keep/revert decision logic, stagnation/crash detection, and strategy shift suggestions via pure functions on LoopState dataclass**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-10T19:17:54Z
- **Completed:** 2026-03-10T19:20:06Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- LoopState dataclass with all iteration tracking fields (scores, counters, thresholds)
- should_keep(), is_stagnating(), is_crash_stuck(), suggest_strategy_shift() pure functions
- GitManager.revert_last_commit() for undoing committed experiments (HEAD~1)
- 26 total tests (17 loop helpers + 9 git) all passing, zero regressions in full suite (69 tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Loop helpers with TDD**
   - `ae60cd3` (test) - RED: failing tests for all loop helper functions
   - `ee5e2bf` (feat) - GREEN: implement loop_helpers.py, all 17 tests pass
2. **Task 2: Add revert_last_commit to GitManager**
   - `bd55821` (test) - RED: failing test for revert_last_commit
   - `b216ed7` (feat) - GREEN: implement revert_last_commit, all 9 git tests pass

## Files Created/Modified
- `src/automl/loop_helpers.py` - LoopState dataclass + decision functions (should_keep, is_stagnating, is_crash_stuck, suggest_strategy_shift)
- `tests/test_loop_helpers.py` - 17 tests covering all behaviors and edge cases
- `src/automl/git_ops.py` - Added revert_last_commit() method to GitManager
- `tests/test_git.py` - Added TestRevertLastCommit class (1 integration test)

## Decisions Made
- Strict greater-than for should_keep: equal scores are NOT improvements (avoids wasted iterations on no-progress changes)
- Configurable thresholds stored on LoopState itself (stagnation_threshold=5, crash_threshold=3) so they can be tuned per-run
- Strategy cycling: when all 5 categories tried, restart from first (infinite exploration)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Loop helpers ready for Plan 02 (draft generation) and Plan 03 (main loop orchestrator)
- All decision functions are pure and stateless -- agent manages LoopState mutations
- revert_last_commit enables the commit-then-run-then-maybe-revert pattern

---
*Phase: 02-core-loop*
*Completed: 2026-03-10*
