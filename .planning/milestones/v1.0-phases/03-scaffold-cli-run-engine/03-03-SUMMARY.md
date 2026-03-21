---
phase: 03-scaffold-cli-run-engine
plan: 03
subsystem: engine
tags: [subprocess, claude-p, experiment-loop, keep-revert, cost-tracking]

requires:
  - phase: 03-scaffold-cli-run-engine
    provides: "scaffold_experiment, ResourceGuardrails, CostTracker, DeviationHandler, LiveProgress, GitManager, checkpoint"
provides:
  - "RunEngine: full experiment loop spawning claude -p sessions with keep/revert/retry/stop routing"
  - "CLI wiring: mlforge <dataset> <goal> scaffolds and runs, --resume loads from checkpoint"
affects: [04-e2e-validation]

tech-stack:
  added: [subprocess]
  patterns: [subprocess-spawn-per-experiment, deviation-routing-loop, sigint-graceful-shutdown]

key-files:
  created:
    - src/mlforge/engine.py
  modified:
    - src/mlforge/cli.py
    - tests/mlforge/test_engine.py
    - tests/mlforge/test_cli.py

key-decisions:
  - "RunEngine._process_result extracts metric_value from nested JSON result string"
  - "Retry on OOM recursively calls _process_result(_run_one_experiment(oom_hint=True))"
  - "SIGINT handler sets _stop_requested flag checked alongside guardrails in loop"
  - "CLI resume checks for checkpoint existence and fails with error if none found"

patterns-established:
  - "Subprocess-per-experiment: fresh claude -p session per iteration, no state leakage"
  - "Full CLI flow: parse args -> scaffold -> git branch -> engine.run() -> summary"
  - "Resume pattern: --resume loads SessionState from checkpoint, skips scaffold/git init"

requirements-completed: [CORE-02, GUARD-03]

duration: 4min
completed: 2026-03-20
---

# Phase 03 Plan 03: Run Engine + CLI Wiring Summary

**RunEngine orchestrating claude -p subprocess spawning with keep/revert deviation routing, cost tracking, checkpoint persistence, and complete CLI scaffold-to-engine flow**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T00:47:10Z
- **Completed:** 2026-03-20T00:51:01Z
- **Tasks:** 2 (Task 1 TDD, Task 2 standard)
- **Files modified:** 4

## Accomplishments
- RunEngine.run() loop spawns claude -p per experiment, saves checkpoint before each iteration, routes results through DeviationHandler, and stops on guardrail trip or SIGINT
- _run_one_experiment handles subprocess crash (non-zero exit), timeout, and JSON decode errors with appropriate status returns
- _process_result routes keep/revert/retry/stop, tracks cost via CostTracker, updates SessionState metrics
- CLI wires complete flow: parse args -> scaffold -> git branch -> RunEngine.run() -> print summary
- --resume loads SessionState from checkpoint, skips scaffold and git init

## Task Commits

Each task was committed atomically:

1. **Task 1: RunEngine experiment loop** (TDD)
   - `2c2ba46` (test) - failing tests for RunEngine
   - `9ae887c` (feat) - RunEngine implementation with 23 tests passing
2. **Task 2: Wire CLI to scaffold + engine**
   - `cf463d2` (feat) - CLI wiring with resume, 48 CLI+engine tests passing

## Files Created/Modified
- `src/mlforge/engine.py` - RunEngine class with run(), _run_one_experiment(), _process_result(), _build_prompt(), SIGINT handling
- `src/mlforge/cli.py` - Updated to wire scaffold -> git init -> engine -> summary, with --resume support
- `tests/mlforge/test_engine.py` - 23 tests for engine init, subprocess, result processing, loop, prompt, signals
- `tests/mlforge/test_cli.py` - 25 tests for CLI arg parsing, validation, scaffold/engine wiring, resume

## Decisions Made
- RunEngine._process_result extracts metric_value from nested JSON result string (claude -p wraps inner result in an outer JSON envelope)
- Retry on OOM recursively calls _process_result with fresh _run_one_experiment(oom_hint=True) -- simple, avoids loop state complexity
- SIGINT handler sets a _stop_requested flag rather than raising -- lets the finally block save checkpoint cleanly
- CLI resume returns error code 1 with message if no checkpoint found (not silent failure)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 03 is now complete: scaffold, guardrails, and engine are all wired through CLI
- Ready for Phase 04 (E2E validation) -- `mlforge data.csv "predict price"` is the full entry point
- 269 tests passing across the full mlforge test suite

## Self-Check: PASSED

All files verified present. All commit hashes found in git log.

---
*Phase: 03-scaffold-cli-run-engine*
*Completed: 2026-03-20*
