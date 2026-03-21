---
phase: 07-e2e-validation-test
plan: 01
subsystem: testing
tags: [e2e, validation, claude-p, headless, permissions, settings-json]

# Dependency graph
requires:
  - phase: 04-e2e-baseline-test
    provides: Phase 4 FINDINGS.md baseline data and run methodology (run-baseline-test.sh pattern)
  - phase: 05-hooks-and-enhanced-scaffolding
    provides: settings.json generation in scaffold.py, hook enforcement logic
  - phase: 06-structured-output-and-metrics-parsing
    provides: json_output line in run.log, parse_run_result.py
provides:
  - FINDINGS.md documenting settings.json permissions are too restrictive for headless claude -p
  - noisy.csv fixture (300 rows, 10% label noise) for future re-validation
  - run-validation-test.sh harness with automated assertions (stop_reason, frozen file, permission_denials)
  - v1.0 certification assessment: BLOCKED pending scaffold permissions fix
affects:
  - scaffold.py (needs permissions.allow broadening for headless mode)
  - Any future phase that validates end-to-end headless operation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Automated assertion shell script pattern: parse_run_result.py + grep checks after claude -p run"
    - "Noisy dataset fixture pattern: flip_y=0.10 in sklearn make_classification forces stagnation"

key-files:
  created:
    - tests/fixtures/noisy.csv
    - scripts/run-validation-test.sh
    - .planning/phases/07-e2e-validation-test/FINDINGS.md
  modified: []

key-decisions:
  - "Phase 7 correctly removed --allowedTools to test settings.json governance — revealing that settings.json permissions are insufficient for headless mode (critical finding)"
  - "v1.0 certification BLOCKED: scaffold.py must generate broader permissions.allow rules before headless autonomous operation is possible"
  - "stop_reason=end_turn is a technical pass but misleading when 0 experiments ran — the agent gave up due to permission denials, not graceful completion"
  - "The underlying loop logic (Phase 2-4) is correct; the bug is purely in Phase 5 settings.json generation"

patterns-established:
  - "Validation harness pattern: scaffold → git init → claude -p (no --allowedTools) → assert stop_reason + permission_denials + frozen files"
  - "Permission audit pattern: run without --allowedTools, count denials, fix settings.json, re-run"

requirements-completed: [VAL-01, VAL-02, VAL-03, VAL-04, VAL-05, VAL-06, VAL-07]

# Metrics
duration: 15min
completed: 2026-03-12
---

# Phase 7 Plan 01: E2E Validation Test Summary

**Discovered that headless `claude -p` without `--allowedTools` is blocked by 8 permission denials from too-narrow settings.json — v1.0 requires scaffold.py to generate broader permissions.allow rules**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-13T00:55:00Z
- **Completed:** 2026-03-13T01:11:27Z
- **Tasks:** 3 (Task 1: auto, Task 2: checkpoint:human-action, Task 3: auto)
- **Files modified:** 3

## Accomplishments

- Created noisy.csv fixture (300 rows, 10% label noise) designed to force stagnation in a future clean run
- Created run-validation-test.sh with automated assertions (stop_reason, frozen file compliance, permission_denials, json_output)
- Discovered and documented the critical root cause: scaffold.py settings.json permissions are too narrow for headless `claude -p` mode — 8 denials prevented all loop execution
- Wrote comprehensive FINDINGS.md with Phase 4 comparison, root cause analysis, proposed fix, and v1.0 certification assessment

## Task Commits

Each task was committed atomically:

1. **Task 1: Generate noisy dataset fixture and write validation test harness** - `9c19458` (feat)
2. **Task 2: Run the validation test outside Claude Code** - N/A (checkpoint:human-action — user ran test)
3. **Task 3: Analyze results and populate FINDINGS.md** - `8a32e8d` (docs)

## Files Created/Modified

- `tests/fixtures/noisy.csv` - 300-row binary classification dataset with 10% label noise (~0.88-0.90 accuracy ceiling)
- `scripts/run-validation-test.sh` - End-to-end validation harness: scaffold + git init + claude -p (no --allowedTools) + automated assertions
- `.planning/phases/07-e2e-validation-test/FINDINGS.md` - Full validation findings: run summary, Phase 5-6 validation results, Phase 4 comparison, root cause, fix proposal, v1.0 certification

## Decisions Made

- Phase 7 intentionally removed `--allowedTools` flag (present in Phase 4) to test settings.json governance — this was the correct design decision and correctly revealed the permissions bug
- v1.0 certification is BLOCKED: the loop cannot run unattended because settings.json is too restrictive. This is a single-fix blocker in `src/automl/scaffold.py`
- The loop logic itself (keep/revert, stagnation, crash recovery) was proven correct in Phase 4 and remains unchanged — the bug is purely in Phase 5's settings.json generation

## Deviations from Plan

None - plan executed exactly as written. The test outcome (failure due to permissions) was the intended finding — Phase 7 existed to discover exactly this kind of issue.

## Issues Encountered

**Critical finding:** settings.json generated by scaffold.py does not grant Bash or Write permissions needed for headless operation. In interactive mode users approve prompts; in headless `claude -p` there is no user. The agent received 8 permission denials (6 Bash for package checks, 2 Write for results.tsv) and halted with 0 experiments run.

**Proposed fix** (in scaffold.py): Broaden permissions.allow to include:
- `Bash(uv run python *)` — run experiments
- `Bash(git *)` — commit/reset operations
- `Write(results.tsv)`, `Write(run.log)` — loop output files
- Keep deny rules for `Edit(prepare.py)` and `Write(prepare.py)`

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The immediate next step is to fix `src/automl/scaffold.py` to generate correct permissions and re-run `./scripts/run-validation-test.sh` to validate the fix. This is NOT a new phase — it is a bug fix within the v1.0 milestone.

**Blocker for v1.0:** scaffold.py must generate settings.json with permissions sufficient for fully unattended `claude -p` operation.

---
*Phase: 07-e2e-validation-test*
*Completed: 2026-03-12*
