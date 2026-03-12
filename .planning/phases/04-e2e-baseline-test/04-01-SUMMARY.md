---
phase: 04-e2e-baseline-test
plan: 01
subsystem: testing
tags: [e2e, autonomous-loop, iris, claude-code, headless, baseline]

# Dependency graph
requires:
  - phase: 03-cli-and-integration
    provides: uv run automl CLI that scaffolds experiment directories
  - phase: 02-core-loop
    provides: keep/revert cycle, draft generation, results.tsv logging, CLAUDE.md protocol
provides:
  - iris.csv fixture for reproducible baseline testing
  - run-baseline-test.sh script for invoking the autonomous loop outside Claude Code
  - FINDINGS.md with empirical data on what works and what needs improvement
  - 5-item issue list with severity ratings and target phases (5, 6, 7)
affects: [05-hooks-and-scaffolding, 06-structured-output, 07-e2e-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Observational phase pattern: run first, analyze, then fix -- no premature optimization"
    - "Human-in-the-loop checkpoint for claude -p invocation (cannot nest CC sessions)"

key-files:
  created:
    - tests/fixtures/iris.csv
    - scripts/run-baseline-test.sh
    - .planning/phases/04-e2e-baseline-test/FINDINGS.md
  modified: []

key-decisions:
  - "CLAUDE.md instructions alone (without hooks) were sufficient to enforce frozen file compliance in this run"
  - "stop_reason=tool_use (mid-action interrupt) is a known limitation of max_turns -- Phase 5 should add graceful shutdown"
  - "30-turn cap insufficient to exercise stagnation threshold -- Phase 7 should use 50+ turns"
  - "iris dataset near-ceiling (0.98 accuracy) -- Phase 7 should use a noisier dataset to force genuine stagnation"

patterns-established:
  - "Baseline test pattern: scaffold -> git init -> claude -p -> capture results.tsv + git log + frozen file check"
  - "Diagnostic checklist covers: draft diversity, keep/revert correctness, metric parsing, frozen file, context, crashes, stagnation, permissions"

requirements-completed: [E2E-BASELINE-01, E2E-BASELINE-02, E2E-BASELINE-03]

# Metrics
duration: ~15min (Task 1 prior session + Task 2 human run + Task 3 analysis)
completed: 2026-03-11
---

# Phase 4 Plan 01: E2E Baseline Test Summary

**Iris dataset autonomous loop ran 9 experiments (5 diverse drafts + 4 SVC iterations), reached 0.980 accuracy with correct keep/revert behavior, no permission denials, and clean frozen-file compliance — identifying 3 issues for Phase 5 and informing Phase 7 test design.**

## Performance

- **Duration:** ~15 min total (Task 1 prior session, Task 2 user-executed, Task 3 analysis)
- **Started:** 2026-03-10 (Task 1)
- **Completed:** 2026-03-11 (Task 3)
- **Tasks:** 3 (Task 1: fixture + script, Task 2: human run checkpoint, Task 3: FINDINGS.md)
- **Files modified:** 3 created

## Accomplishments

- Created reproducible iris.csv fixture (150 rows, 4 features, integer species target) and run-baseline-test.sh script with full diagnostics
- Captured empirical evidence that the autonomous loop's core mechanics (draft diversity, keep/revert, metric parsing, frozen file compliance, context management) all work correctly
- Produced structured FINDINGS.md with 5 categorized issues mapped to target fix phases (5, 6, 7) and actionable recommendations for each

## Task Commits

Each task was committed atomically:

1. **Task 1: Create iris dataset fixture and baseline test run script** - `c36cfd0` (feat) — prior session
2. **Task 2: Run the baseline test outside Claude Code** - checkpoint resolved, no commit (human action)
3. **Task 3: Analyze results and populate FINDINGS.md** - `67f9e79` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `tests/fixtures/iris.csv` - 150-row iris dataset with sepal/petal features and integer species target
- `scripts/run-baseline-test.sh` - Self-contained E2E test script: scaffold + git init + claude -p headless invocation + diagnostics
- `.planning/phases/04-e2e-baseline-test/FINDINGS.md` - Structured findings with checklist results, 5 issues table, and phase-by-phase recommendations

## Decisions Made

- CLAUDE.md-only compliance worked: prepare.py was never touched without any hook enforcement — this validates that the instructions are sufficient for cooperative behavior, but hooks are still needed as a safety net for adversarial edge cases
- stop_reason=tool_use (not end_turn) is the key finding: agent hit max_turns while executing a Bash call, meaning results.tsv may be partially written at termination — Phase 5 should address graceful shutdown
- 30-turn budget on iris was sufficient to confirm core mechanics but insufficient to exercise stagnation (5 consecutive reverts). Phase 7 design requires 50+ turns and a harder dataset
- The SVC family outperformed LogisticRegression (best draft) during iteration — the agent's autonomous pivot was correct and demonstrates the keep/revert cycle is working as intended

## Deviations from Plan

None - plan executed exactly as written. Task 2 was a checkpoint:human-action resolved by the user providing complete run data.

## Issues Encountered

- run-baseline-test.sh diagnostic parser grabbed metric_std column instead of metric_value when displaying the best metric summary — this is a display-only bug in the shell script, not a loop bug. Logged in FINDINGS.md issue #2 for Phase 5 fix.
- venv warning (VIRTUAL_ENV path mismatch) appeared in run.log on every uv invocation — cosmetic noise, logged in FINDINGS.md issue #3 for Phase 5 fix.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 5 (Hooks + Scaffolding):** Ready. Key targets: graceful shutdown on max_turns, fix run-baseline-test.sh metric parsing, suppress venv warning, design hooks as safety net (not disruptive hard-fail)
- **Phase 6 (Structured Output):** Current parsing works; priority is structured stop_reason/num_turns extraction and agent reasoning capture during keep/revert decisions
- **Phase 7 (Validation Test):** Design with 50+ turns and a noisier dataset to exercise stagnation; target stop_reason=end_turn; verify frozen file compliance with an active hook

---
*Phase: 04-e2e-baseline-test*
*Completed: 2026-03-11*
