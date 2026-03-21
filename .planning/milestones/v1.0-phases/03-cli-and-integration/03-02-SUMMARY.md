---
phase: 03-cli-and-integration
plan: 02
subsystem: cli
tags: [argparse, cli, entry-point, e2e-testing]

requires:
  - phase: 03-01
    provides: scaffold_experiment function to wrap with CLI
provides:
  - CLI entry point (automl command) for scaffolding experiments
  - End-to-end validation of scaffold-to-train pipeline
affects: []

tech-stack:
  added: [argparse]
  patterns: [cli-wraps-library, structured-output-parsing]

key-files:
  created:
    - src/automl/cli.py
    - tests/test_cli.py
    - tests/test_e2e.py
  modified:
    - pyproject.toml

key-decisions:
  - "main(argv) accepts list for testability, empty list triggers usage+error (not argparse default)"
  - "E2e tests use sys.executable directly instead of uv run (avoids venv creation overhead)"

patterns-established:
  - "CLI returns int exit codes (0 success, 1 error) for clean sys.exit integration"
  - "E2e tests validate structured output format with regex parsing"

requirements-completed: [CLI-02, CLI-04]

duration: 4min
completed: 2026-03-10
---

# Phase 3 Plan 2: CLI Entry Point Summary

**Argparse CLI wrapping scaffold_experiment with 3 positional + 3 optional args, registered as `automl` entry point, validated end-to-end**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T23:17:59Z
- **Completed:** 2026-03-10T23:21:32Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- CLI entry point `automl` accepts data_path, target_column, metric (positional) and --goal, --output-dir, --time-budget (optional)
- Entry point registered in pyproject.toml [project.scripts] as `automl = "automl.cli:main"`
- End-to-end test proves scaffold -> train.py pipeline produces valid structured metric output
- Full test suite: 111 tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CLI module, entry point, and tests** - `470168e` (feat)
2. **Task 2: End-to-end test -- scaffold and run train.py** - `88b7ee3` (test)

_Note: TDD tasks had GREEN on first run since scaffold_experiment was already proven in Plan 01_

## Files Created/Modified
- `src/automl/cli.py` - CLI entry point with argparse, wraps scaffold_experiment
- `pyproject.toml` - Added [project.scripts] entry point and pytest slow mark
- `tests/test_cli.py` - 6 tests covering help, missing args, valid args, optional flags, bad csv, bad metric
- `tests/test_e2e.py` - 2 e2e tests validating scaffold+train pipeline produces parseable metrics

## Decisions Made
- main(argv) accepts list for testability; empty list returns usage+error code 1 (avoids argparse printing to stderr on its own)
- E2e tests use sys.executable directly instead of `uv run` subprocess to avoid venv creation overhead in tests
- Registered pytest `slow` mark in pyproject.toml to suppress warnings

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Config] Registered pytest slow marker**
- **Found during:** Task 2
- **Issue:** @pytest.mark.slow was used but not registered, causing PytestUnknownMarkWarning
- **Fix:** Added markers config to pyproject.toml [tool.pytest.ini_options]
- **Files modified:** pyproject.toml
- **Verification:** Full suite runs without warnings
- **Committed in:** 88b7ee3 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing config)
**Impact on plan:** Minor config addition for clean test output. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All v1.0 milestone plans complete (8/8)
- Framework is fully functional: user runs `automl data.csv target_col metric` and gets a ready-to-run experiment
- Claude Code can autonomously iterate inside scaffolded experiment directories

---
*Phase: 03-cli-and-integration*
*Completed: 2026-03-10*
