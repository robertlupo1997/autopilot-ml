---
phase: 06-fix-engine-subprocess-flags
plan: 01
subsystem: engine
tags: [subprocess, claude-cli, flags, system-prompt]

# Dependency graph
requires:
  - phase: 03-scaffold-cli-run-engine
    provides: RunEngine with subprocess invocation
provides:
  - Fixed _run_one_experiment with valid claude CLI flags
  - Inline CLAUDE.md content via --append-system-prompt
  - Graceful handling of missing CLAUDE.md
affects: [07-wire-intelligence, 08-register-plugins, 09-wire-simple-mode]

# Tech tracking
tech-stack:
  added: []
  patterns: [inline-system-prompt, graceful-file-degradation]

key-files:
  created: []
  modified:
    - src/mlforge/engine.py
    - tests/mlforge/test_engine.py

key-decisions:
  - "Read CLAUDE.md via Path.read_text() inline rather than passing file path to CLI"
  - "Omit --append-system-prompt entirely when CLAUDE.md missing (graceful skip, no empty string)"
  - "Keep max_turns_per_experiment in Config for forward compatibility, just stop passing to CLI"

patterns-established:
  - "Inline system prompt: always read file content and pass via --append-system-prompt, never --append-system-prompt-file"

requirements-completed: [CORE-02, CORE-03, INTL-07, GUARD-03]

# Metrics
duration: 2min
completed: 2026-03-20
---

# Phase 6 Plan 01: Fix Engine Subprocess Flags Summary

**Replaced invalid --append-system-prompt-file and --max-turns flags with --append-system-prompt inline content, unblocking all experiment execution**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-20T03:07:43Z
- **Completed:** 2026-03-20T03:09:18Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Removed --max-turns flag (not valid claude CLI flag) from subprocess command
- Replaced --append-system-prompt-file with --append-system-prompt using inline CLAUDE.md content
- Added graceful degradation when CLAUDE.md is missing (omits flag instead of crashing)
- 4 new tests verify corrected flag structure, 421 total tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add tests for corrected CLI flag structure** - `be3b4c7` (test) - TDD RED phase
2. **Task 2: Fix invalid CLI flags in engine.py** - `0ee624b` (feat) - TDD GREEN phase

## Files Created/Modified
- `src/mlforge/engine.py` - Fixed _run_one_experiment to use --append-system-prompt with inline content, removed --max-turns
- `tests/mlforge/test_engine.py` - Added TestCommandFlags class with 4 tests verifying flag correctness

## Decisions Made
- Read CLAUDE.md via Path.read_text() inline rather than passing file path to CLI -- aligns with valid claude CLI flags
- Omit --append-system-prompt entirely when CLAUDE.md missing -- cleaner than passing empty string
- Keep max_turns_per_experiment in Config for forward compatibility -- just stop passing to CLI

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Engine subprocess flags are now valid -- experiments can actually run
- Phase 7 (Wire Intelligence Subsystem) can proceed to connect intelligence modules to the engine loop
- Phase 8 (Register Domain Plugins) can proceed to register DL/FT plugins
- Phase 9 (Wire Simple Mode) can proceed to propagate task type

---
*Phase: 06-fix-engine-subprocess-flags*
*Completed: 2026-03-20*
