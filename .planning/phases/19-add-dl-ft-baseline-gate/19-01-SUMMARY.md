---
phase: 19-add-dl-ft-baseline-gate
plan: 01
subsystem: engine
tags: [baselines, deeplearning, finetuning, sklearn, cross-entropy]

# Dependency graph
requires:
  - phase: 07-intelligence-wiring
    provides: baseline gate enforcement in _process_result
provides:
  - DL baseline computation (random + most_frequent via DummyClassifier)
  - FT baseline computation (theoretical loss/perplexity from vocab size)
  - Engine domain dispatch for baseline computation
  - Label extraction from image directory structure
affects: [20-add-dl-ft-stagnation-branching]

# Tech tracking
tech-stack:
  added: []
  patterns: [domain-dispatch in _compute_baselines, lazy imports for domain-specific modules, theoretical baselines for language models]

key-files:
  created:
    - src/mlforge/deeplearning/baselines.py
    - src/mlforge/finetuning/baselines.py
    - tests/mlforge/test_dl_baselines.py
    - tests/mlforge/test_ft_baselines.py
  modified:
    - src/mlforge/engine.py
    - tests/mlforge/test_engine.py

key-decisions:
  - "Refactored _compute_baselines into domain-dispatch with separate helper methods per domain"
  - "DL label extraction scans directory structure (class folders with files) for image classification"
  - "FT baselines are purely theoretical (no model required) using log(vocab_size) for loss"

patterns-established:
  - "Domain dispatch: _compute_baselines delegates to _compute_{domain}_baselines helper"
  - "Theoretical baselines: FT uses math.log(vocab_size) without loading any model"
  - "Label extraction: directory-as-class-label pattern for image datasets"

requirements-completed: [INTL-01, INTL-02]

# Metrics
duration: 3min
completed: 2026-03-21
---

# Phase 19 Plan 01: Add DL/FT Baseline Gate Summary

**DL baselines via DummyClassifier + theoretical cross-entropy, FT baselines via log(vocab_size), engine domain dispatch for all three domains**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-21T02:51:27Z
- **Completed:** 2026-03-21T02:54:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- DL baseline module computes random and most_frequent scores for classification, theoretical cross-entropy for loss
- FT baseline module computes theoretical loss and perplexity bounds from vocabulary size
- Engine dispatches to correct baseline module by domain, gracefully returns None for unknown domains or missing data
- 24 new tests (12 DL baselines, 8 FT baselines, 4 engine dispatch), all 555 mlforge tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create DL and FT baseline modules with tests**
   - `52a111d` (test) - Failing tests for DL/FT baselines
   - `0db448d` (feat) - Implement DL and FT baseline modules
2. **Task 2: Wire engine dispatch and update existing tests**
   - `e3f2a15` (feat) - Engine dispatch for DL/FT baseline computation

_Note: TDD tasks have multiple commits (test then feat)_

## Files Created/Modified
- `src/mlforge/deeplearning/baselines.py` - DL baseline computation (DummyClassifier for classification, theoretical for loss)
- `src/mlforge/finetuning/baselines.py` - FT baseline computation (theoretical bounds from vocab size)
- `src/mlforge/engine.py` - Domain dispatch in _compute_baselines, _load_dl_labels helper
- `tests/mlforge/test_dl_baselines.py` - 12 tests for DL baselines (classification + loss)
- `tests/mlforge/test_ft_baselines.py` - 8 tests for FT baselines (loss + perplexity + custom vocab)
- `tests/mlforge/test_engine.py` - 4 new engine dispatch tests, renamed unknown domain test

## Decisions Made
- Refactored monolithic _compute_baselines into domain-dispatch with _compute_tabular_baselines, _compute_dl_baselines, _compute_ft_baselines helper methods
- DL label extraction scans subdirectories as class folders, counts files per folder to build label array
- FT baselines are purely theoretical (no model loading required) -- random_guess = log(vocab_size)
- Renamed test_baselines_skipped_for_non_tabular to test_baselines_skipped_for_unknown_domain for clarity

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Baseline gate now enforced for all three domains (tabular, deeplearning, finetuning)
- passes_baseline_gate works unchanged with DL/FT baseline format
- Ready for Phase 20 (stagnation branching for DL/FT)

---
*Phase: 19-add-dl-ft-baseline-gate*
*Completed: 2026-03-21*
