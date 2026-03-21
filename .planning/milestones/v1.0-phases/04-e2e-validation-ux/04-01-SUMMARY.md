---
phase: 04-e2e-validation-ux
plan: 01
subsystem: cli
tags: [profiler, auto-detection, classification, regression, pandas, argparse]

requires:
  - phase: 03-scaffold-cli-run-engine
    provides: CLI entry point, scaffold_experiment, Config dataclass
provides:
  - DatasetProfile dataclass with auto-detection of task type and metric
  - profile_dataset() function for dataset profiling
  - _detect_date_columns() for temporal pattern detection
  - Simple mode CLI (auto-detect from dataset + goal)
  - Expert mode CLI (--custom-claude-md, --custom-frozen, --custom-mutable)
affects: [04-02-PLAN, phase 5 domain plugins]

tech-stack:
  added: []
  patterns: [simple-vs-expert-mode, auto-detection-from-data, target-column-extraction-from-goal]

key-files:
  created: [src/mlforge/profiler.py, tests/mlforge/test_profiler.py]
  modified: [src/mlforge/cli.py, src/mlforge/config.py, src/mlforge/scaffold.py, tests/mlforge/test_cli.py]

key-decisions:
  - "Binary classification uses accuracy, multi-class uses f1_weighted, regression uses r2"
  - "Numeric target with <=20 unique values treated as classification"
  - "Date detection samples head(20) with >80% parse threshold using pd.to_datetime mixed format"
  - "Target column extracted from goal via 'predict X' regex pattern with last-word fallback"
  - "Simple mode falls back silently to defaults if profiling fails"

patterns-established:
  - "Simple/expert mode split: no --metric means auto-detect, --metric means expert"
  - "Profiler as standalone module reusable by other entry points"

requirements-completed: [UX-01, UX-02, UX-04, TABL-03]

duration: 3min
completed: 2026-03-20
---

# Phase 4 Plan 01: Dataset Profiler + Simple/Expert Mode Summary

**DatasetProfile auto-detection module with simple mode (zero-config from dataset+goal) and expert mode (custom CLAUDE.md, frozen, mutable files) integrated into CLI and scaffold**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T01:15:57Z
- **Completed:** 2026-03-20T01:19:47Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- DatasetProfile dataclass and profile_dataset() auto-detect classification vs regression, select metric, find date columns, and report data characteristics
- CLI simple mode requires only dataset + goal -- auto-detects everything via profiling
- CLI expert mode accepts --custom-claude-md, --custom-frozen, --custom-mutable for full control
- Scaffold respects custom CLAUDE.md (copies instead of rendering) and custom frozen/mutable lists
- 27 new tests (20 profiler + 7 CLI) added; all 310 existing tests continue to pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create profiler module (TDD RED)** - `a54b964` (test)
2. **Task 1: Create profiler module (TDD GREEN)** - `eb616a1` (feat)
3. **Task 2: Add simple/expert mode to CLI, Config, scaffold** - `353d6ea` (feat)

_Note: Task 1 used TDD flow with separate RED and GREEN commits_

## Files Created/Modified
- `src/mlforge/profiler.py` - DatasetProfile dataclass, profile_dataset(), _detect_date_columns()
- `src/mlforge/cli.py` - Simple/expert mode flags, profiler integration, _extract_target_column()
- `src/mlforge/config.py` - custom_claude_md_path, custom_frozen, custom_mutable fields
- `src/mlforge/scaffold.py` - Custom CLAUDE.md copy, custom frozen/mutable list handling
- `tests/mlforge/test_profiler.py` - 20 tests for profiler auto-detection
- `tests/mlforge/test_cli.py` - 7 new tests for expert/simple mode

## Decisions Made
- Binary classification uses accuracy, multi-class uses f1_weighted, regression uses r2 -- all maximize direction
- Numeric target with <=20 unique values is treated as classification (categorical-like)
- Date detection: samples first 20 rows, requires >80% successful parse to classify as date column
- Target column extracted from goal string via "predict X" regex with last-word fallback
- Simple mode profiling failure falls back silently to default metric (accuracy) rather than crashing
- Custom frozen/mutable replace plugin defaults entirely (not merge)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Profiler and simple/expert mode ready for E2E validation
- 04-02 (artifact export + run retrospective) can proceed
- Date column detection wires into plugin_settings for temporal leakage prevention

## Self-Check: PASSED

All 7 files verified present. All 3 commits verified in git log.

---
*Phase: 04-e2e-validation-ux*
*Completed: 2026-03-20*
