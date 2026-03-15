---
phase: 16-template-and-protocol-updates
plan: "02"
subsystem: ml-experiment-template
tags: [protocol, templates, journal, diff-aware, hypothesis, classification, forecasting]

# Dependency graph
requires:
  - phase: 16-template-and-protocol-updates
    plan: "01"
    provides: experiments.md in claude_forecast.md.tmpl Files section and DIAG-03 rule
provides:
  - claude.md.tmpl with full v3.0 protocol rules (KNOW-02, PROT-01, PROT-02)
  - claude_forecast.md.tmpl with full v3.0 protocol rules matching classification template
  - structural tests confirming all rules present in both templates
affects: [all future experiment runs, 17-exploration-and-stagnation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Journal read-before / write-after pattern: agent reads experiments.md at loop start and updates after keep/revert"
    - "Diff-aware iteration: git diff HEAD~1 -- train.py + git log --oneline -5 before each edit"
    - "Hypothesis commit messages: ## Hypothesis section in every commit during iteration loop"

key-files:
  created: []
  modified:
    - src/automl/templates/claude.md.tmpl
    - src/automl/templates/claude_forecast.md.tmpl
    - tests/test_templates.py
    - tests/test_train_template_forecast.py

key-decisions:
  - "Both templates carry identical v3.0 protocol steps (2=journal-read, 3=diff-review, 6=hypothesis-commit, 13/12=journal-update) — consistent agent behavior across task types"
  - "Journal update step placed after keep/revert decision so the agent writes confirmed outcome, not tentative result"
  - "Hypothesis example in forecast template uses forecast-specific language (MAPE, Q4, quarter dummies) to guide agent toward domain-relevant hypotheses"

patterns-established:
  - "Read-before / write-after journal discipline enforced via numbered steps in both templates"
  - "Hypothesis commit format gives structured test-and-learn cadence to the iteration loop"

requirements-completed: [KNOW-02, PROT-01, PROT-02, PROT-03]

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 16 Plan 02: Template and Protocol Updates Summary

**Both CLAUDE.md templates updated with v3.0 protocol rules: journal read/write (KNOW-02), diff-aware iteration (PROT-01), and hypothesis commit messages (PROT-02); 8 new structural tests confirm all rules present**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-15T18:52:49Z
- **Completed:** 2026-03-15T18:55:02Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `experiments.md` to the Files section of `claude.md.tmpl` with section descriptions
- Added step 2 (read experiments.md before iteration) to both templates — KNOW-02
- Added step 3 (git diff HEAD~1 + git log --oneline) to both templates — PROT-01
- Renumbered remaining Phase 2 steps in both templates accordingly
- Updated commit step to require `## Hypothesis` section in commit messages — PROT-02
- Added journal update step after keep/revert decision in both templates — KNOW-02
- Added 4 structural tests to `tests/test_templates.py` for classification template
- Added 4 structural tests to `tests/test_train_template_forecast.py` for forecast template
- All 110 tests pass (35 template tests, 56 forecast tests, 19 scaffold tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add v3.0 protocol rules to claude.md.tmpl** - `c9c3d76` (feat)
2. **Task 2: Add v3.0 protocol rules to claude_forecast.md.tmpl** - `7a9b6ac` (feat)

## Files Created/Modified

- `src/automl/templates/claude.md.tmpl` - Added experiments.md to Files, journal read step, diff-aware review step, renumbered Phase 2, hypothesis commit format, journal update step
- `src/automl/templates/claude_forecast.md.tmpl` - Same additions as classification; preserved all forecast-specific rules and 16-01 DIAG-03 additions
- `tests/test_templates.py` - Added test_journal_read_write_rule, test_diff_aware_rule, test_hypothesis_commit_rule, test_experiments_md_in_files_section
- `tests/test_train_template_forecast.py` - Added same 4 structural tests for forecast template

## Decisions Made

- Both templates carry identical v3.0 protocol steps to ensure consistent agent behavior across classification and forecasting task types.
- Journal update step placed after keep/revert decision (not after running) so agent writes confirmed outcome, not tentative result.
- Hypothesis example in forecast template uses domain-specific language (MAPE delta, Q4 seasonality) to guide the agent toward better-grounded hypotheses.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- KNOW-02, PROT-01, PROT-02, PROT-03 requirements fulfilled
- Both templates now enforce informed iteration: agents read knowledge, review diffs, write testable hypotheses, and record outcomes
- Phase 17 (Exploration and Stagnation) can proceed; depends on EXPL-01 (best-commit tracking)

---
*Phase: 16-template-and-protocol-updates*
*Completed: 2026-03-15*
