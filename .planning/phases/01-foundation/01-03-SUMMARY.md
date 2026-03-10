---
phase: 01-foundation
plan: 03
subsystem: modeling
tags: [scikit-learn, subprocess, signal, template, cross-validation, experiment-runner]

# Dependency graph
requires:
  - "01-01: prepare.py frozen data pipeline (load_data, build_preprocessor, evaluate, validate_metric)"
  - "01-02: ExperimentLogger for run.log pattern"
provides:
  - "train_template.py mutable experiment script with structured output and time budget"
  - "ExperimentRunner class for subprocess execution, metric extraction, and run.log capture"
  - "ExperimentResult dataclass for structured experiment outcomes"
affects: [02-core-loop]

# Tech tracking
tech-stack:
  added: []
  patterns: ["signal.SIGALRM for per-script timeout", "subprocess.run with hard kill timeout at 2x budget", "structured output parsing via regex", "sibling-import pattern for experiment directories"]

key-files:
  created:
    - src/automl/train_template.py
    - src/automl/runner.py
    - tests/test_train.py
    - tests/test_runner.py
  modified: []

key-decisions:
  - "train_template.py uses 'from prepare import' (sibling import) not package import -- experiment dirs are standalone"
  - "ExperimentRunner accepts python_cmd parameter for testability (sys.executable in tests, uv run python in prod)"
  - "Two-layer timeout: signal.SIGALRM in template for graceful TimeoutError + subprocess hard kill at 2x budget"

patterns-established:
  - "Structured output protocol: print('---') separator followed by key: value lines parseable by grep/regex"
  - "ExperimentRunner._extract_field() regex pattern for parsing train.py output"
  - "Experiment directory pattern: copy template + prepare.py + data.csv into isolated directory"

requirements-completed: [MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05]

# Metrics
duration: 3min
completed: 2026-03-10
---

# Phase 1 Plan 3: Train Template and Experiment Runner Summary

**Mutable train_template.py with LogisticRegression baseline, structured grep-parseable output, signal-based timeout, and ExperimentRunner subprocess executor with metric extraction and run.log capture**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-10T13:21:51Z
- **Completed:** 2026-03-10T13:24:33Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Mutable train_template.py that runs as standalone script, imports from prepare.py, and prints structured metric output
- ExperimentRunner executes train.py via subprocess, captures stdout/stderr to run.log, extracts metric via regex
- Comprehensive error handling: crash detection (non-zero exit), timeout enforcement (2x budget hard kill), missing metric parsing
- 13 new tests (6 train template + 7 runner), full suite 46/46 passing with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Train template tests** - `b764dfb` (test)
2. **Task 1 GREEN: Train template implementation** - `b78eb7d` (feat)
3. **Task 2 RED: Runner tests** - `f5116b9` (test)
4. **Task 2 GREEN: Runner implementation** - `817d957` (feat)

_Both tasks followed TDD: tests written first (RED), then implementation (GREEN)._

## Files Created/Modified
- `src/automl/train_template.py` - Mutable experiment script (49 lines): baseline LogisticRegression, structured output, signal.alarm timeout
- `src/automl/runner.py` - ExperimentRunner class (152 lines): subprocess execution, regex metric extraction, run.log capture, crash/timeout handling
- `tests/test_train.py` - 6 tests: file existence, prepare import, execution, structured output, metric extraction, timeout enforcement
- `tests/test_runner.py` - 7 tests: run experiment, log capture, log overwrite, metric extraction, missing metric, crash, timeout

## Decisions Made
- train_template.py uses sibling imports (`from prepare import`) not package imports -- experiment directories are standalone, not Python packages
- ExperimentRunner accepts `python_cmd` parameter defaulting to `["uv", "run", "python"]` but overridable to `[sys.executable]` in tests for environment isolation
- Two-layer timeout strategy: signal.SIGALRM inside the template for graceful TimeoutError, plus subprocess hard kill at 2x budget as safety net

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 1 Foundation is now complete: prepare.py (Plan 01) + git_ops.py + experiment_logger.py (Plan 02) + train_template.py + runner.py (Plan 03)
- All components are tested and ready for Phase 2 Core Loop integration
- ExperimentRunner + GitManager + ExperimentLogger compose into the autonomous experiment loop

## Self-Check: PASSED

All 4 files verified present. All 4 commits verified in git log.

---
*Phase: 01-foundation*
*Completed: 2026-03-10*
