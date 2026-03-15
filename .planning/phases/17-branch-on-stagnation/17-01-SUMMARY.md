---
phase: 17-branch-on-stagnation
plan: "01"
subsystem: templates
tags: [stagnation, branching, experiments, protocol, claude-md]

# Dependency graph
requires:
  - phase: 16-template-and-protocol-updates
    provides: v3.0 protocol steps (journal read, diff review, hypothesis commits) in both templates
provides:
  - Best Result section in experiments.md.tmpl with commit hash, score, model family, iteration fields
  - Branch-on-stagnation protocol in claude.md.tmpl (classification)
  - Branch-on-stagnation protocol in claude_forecast.md.tmpl (forecasting)
  - 6 structural tests covering EXPL-01, EXPL-02, EXPL-03 requirements
affects: [18-e2e-validation, future-experiments, agent-loop-behavior]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Branch-on-stagnation: after 3 consecutive reverts, agent checkouts best-ever commit on explore-{family} branch"
    - "Best Result section in experiments.md as agent-maintained anchor for backtracking"
    - "Exploration branches share the same results.tsv for unified experiment history"

key-files:
  created: []
  modified:
    - src/automl/templates/experiments.md.tmpl
    - src/automl/templates/claude.md.tmpl
    - src/automl/templates/claude_forecast.md.tmpl
    - tests/test_scaffold.py
    - tests/test_templates.py
    - tests/test_train_template_forecast.py

key-decisions:
  - "Stagnation threshold reduced from 5 to 3 consecutive reverts — earlier recovery is more efficient"
  - "Branch from best-ever commit rather than continuing from degraded state — captures tree-search backtracking value without MCTS complexity"
  - "Exploration branches share results.tsv — unified experiment history across branches"
  - "Best Result section uses agent-maintained placeholders — no new template substitution variables needed"

patterns-established:
  - "Best Result pattern: KEEP step writes commit hash to experiments.md; stagnation step reads it back"
  - "explore-{family} branch naming: consistent prefix enables identification of exploration vs main iterations"

requirements-completed: [EXPL-01, EXPL-02, EXPL-03]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 17 Plan 01: Branch-on-Stagnation Summary

**Best-commit tracking in experiments.md and git checkout -b explore-{family} {best_commit} protocol replacing blind strategy-switch in both CLAUDE.md templates**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T19:04:33Z
- **Completed:** 2026-03-15T19:06:52Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `## Best Result` section to experiments.md.tmpl between Dataset Context and What Works, with commit hash, score, model family, and iteration fields
- Updated KEEP step in both templates to instruct agent to run `git rev-parse HEAD` and record result in Best Result section
- Replaced "5 consecutive reverts" stagnation with "3 consecutive reverts" branch-on-stagnation: `git checkout -b explore-{family} {best_commit}` from best-ever commit
- Added 6 structural tests (3 per template): EXPL-01 (best-commit tracking), EXPL-02+03 (exploration branch creation and backtracking)
- Full test suite: 379 passed, 0 failures, 0 regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Best Result section to experiments.md.tmpl** - `6bc5b97` (feat)
2. **Task 2: Update both CLAUDE.md templates with branch-on-stagnation protocol** - `4a024a5` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/automl/templates/experiments.md.tmpl` - Added `## Best Result` section with 4 agent-maintained fields
- `src/automl/templates/claude.md.tmpl` - KEEP step now updates Best Result; stagnation changed to 3-revert branch protocol
- `src/automl/templates/claude_forecast.md.tmpl` - Same changes as classification template, MAPE-specific language
- `tests/test_scaffold.py` - Added `test_best_result_section_exists` to TestRenderExperimentsMd
- `tests/test_templates.py` - Added 3 structural tests: best-result tracking, stagnation branch trigger, best-commit usage
- `tests/test_train_template_forecast.py` - Added same 3 structural tests for forecast template

## Decisions Made

- Stagnation threshold reduced from 5 to 3 consecutive reverts: faster recovery matches branch-on-stagnation semantics (agent has a known-good commit to return to, so waiting 5 reverts is wasteful)
- Best Result section uses no new template substitution placeholders: agent fills it dynamically during iteration, keeping `render_experiments_md()` signature unchanged
- Exploration branches share the same `results.tsv`: unified experiment history enables comparison across all branches without data loss

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All EXPL requirements (EXPL-01, EXPL-02, EXPL-03) satisfied
- Both templates now have complete v3.0 protocol: journal read, diff review, hypothesis commits, journal update, best-commit tracking, exploration branching
- Ready for Phase 18 E2E validation of the complete v3.0 agent loop

---
*Phase: 17-branch-on-stagnation*
*Completed: 2026-03-15*
