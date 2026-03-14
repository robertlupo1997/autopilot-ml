---
phase: 09-resume-capability
plan: "02"
subsystem: cli-and-templates
tags: [resume, cli, argparse, claude-md, protocol, tdd]
dependency_graph:
  requires:
    - phase: 09-01
      provides: checkpoint-module
  provides: [resume-cli-flag, session-resume-protocol]
  affects: [runner, multi-agent-swarm]
tech_stack:
  added: []
  patterns: [argparse-store-true-flag, claude-md-protocol-section]
key_files:
  created: []
  modified:
    - src/automl/cli.py
    - src/automl/templates/claude.md.tmpl
    - tests/test_cli.py
    - tests/test_templates.py
key_decisions:
  - "--resume flag is informational for v1: the actual resume behavior comes from CLAUDE.md Session Resume Check section, not Python enforcement at invocation time"
  - "Session Resume Check inserted before Phase 1 so agent reads checkpoint on every startup, regardless of --resume flag"
  - "loop_phase=draft triggers Phase 1 restart (safe, results in results.tsv); loop_phase=iteration skips to Phase 2"
  - "Checkpoint written AFTER keep/revert decision is final to avoid stale best_commit in checkpoint"
requirements-completed:
  - RES-03
  - RES-04
duration: 3min
completed: "2026-03-14"
---

# Phase 09 Plan 02: CLI --resume Flag and CLAUDE.md Resume Protocol Summary

**argparse --resume flag and Session Resume Check protocol section in claude.md.tmpl, enabling checkpoint-based session resumption for autonomous ML agents.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-14T04:27:00Z
- **Completed:** 2026-03-14T04:30:03Z
- **Tasks:** 1 (TDD: 2 commits -- test RED + feat GREEN)
- **Files modified:** 4

## Accomplishments

- Added `--resume` (store_true, default False) to `cli.py` argparse parser with full docstring
- Added `## Session Resume Check` section to `claude.md.tmpl` before Phase 1, instructing agent to check `checkpoint.json` on every startup
- Resume Protocol distinguishes `loop_phase=draft` (restart Phase 1) vs `loop_phase=iteration` (skip to Phase 2)
- Resume Protocol instructs agent to update `checkpoint.json` after every keep/revert using `automl.checkpoint.save_checkpoint`
- 12 new tests (4 CLI, 9 template) all passing; full suite 171 tests green

## Task Commits

Each task was committed atomically (TDD pattern: RED then GREEN):

1. **RED: Failing tests for --resume flag and Session Resume Check** - `8532f5c` (test)
2. **GREEN: Implementation of --resume and Session Resume Check** - `aefb30b` (feat)

## Files Created/Modified

- `src/automl/cli.py` - Added `--resume` argparse flag after `--time-budget`
- `src/automl/templates/claude.md.tmpl` - Added `## Session Resume Check` section before Phase 1
- `tests/test_cli.py` - Added `TestCliResumeFlag` class (4 tests)
- `tests/test_templates.py` - Added `TestClaudeMdResumeSection` class (9 tests)

## Decisions Made

1. **--resume is informational in v1** -- The flag communicates user intent and serves as a hook point for Phase 10 (swarm manager can pass --resume when restarting agents). The actual resume behavior is enforced by the CLAUDE.md protocol, not by Python code at invocation time.
2. **Session Resume Check fires unconditionally** -- The CLAUDE.md section checks for `checkpoint.json` on every startup. This means even without `--resume`, the agent will restore state if a checkpoint exists. This is intentional: checkpoint.json presence is the signal.
3. **Draft phase restart on resume** -- If `loop_phase=draft`, the safest behavior is restarting Phase 1 entirely. Prior draft results are in results.tsv, so re-evaluation is harmless and avoids complex mid-draft resumption logic.
4. **Checkpoint timing** -- The protocol explicitly states: write checkpoint AFTER keep/revert decision is final. Keep path: after `git commit`. Revert path: after `git reset --hard HEAD~1`. This prevents stale `best_commit` values in the checkpoint.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 9 (Resume Capability) is now complete: checkpoint.py module (Plan 01) + --resume CLI flag + CLAUDE.md protocol (Plan 02)
- Phase 10 (Multi-Agent Swarm) can build on the checkpoint infrastructure and --resume flag for swarm agent restart logic
- No blockers

---
*Phase: 09-resume-capability*
*Completed: 2026-03-14*
