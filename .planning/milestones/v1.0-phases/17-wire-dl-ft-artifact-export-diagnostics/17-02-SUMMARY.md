---
phase: 17-wire-dl-ft-artifact-export-diagnostics
plan: 02
subsystem: templates
tags: [jinja2, pytorch, predictions, diagnostics, artifact-preservation]

requires:
  - phase: 16-wire-template-runtime-artifacts
    provides: Tabular predictions.csv pattern to replicate for DL/FT
provides:
  - DL template predictions.csv write from best model on val set
  - FT template predictions.csv write for loss/perplexity metrics
  - DL artifact preservation rule in CLAUDE.md protocol
  - FT artifact preservation rule in CLAUDE.md protocol
affects: [diagnostics-engine, artifact-export]

tech-stack:
  added: []
  patterns: [predictions.csv write in train templates, artifact preservation domain rules]

key-files:
  created: []
  modified:
    - src/mlforge/templates/dl_train.py.j2
    - src/mlforge/templates/ft_train.py.j2
    - src/mlforge/deeplearning/__init__.py
    - src/mlforge/finetuning/__init__.py
    - tests/mlforge/test_templates.py

key-decisions:
  - "DL predictions from best_model.pt state dict reload, not last epoch weights"
  - "FT predictions guarded to loss/perplexity only (ROUGE produces text, not numeric)"
  - "FT y_true=0.0 placeholder since loss is self-referential"

patterns-established:
  - "All domains write predictions.csv before JSON output for diagnostics engine"
  - "All domain plugins include artifact preservation rule in template_context"

requirements-completed: [DL-04, FT-04, INTL-03]

duration: 2min
completed: 2026-03-21
---

# Phase 17 Plan 02: DL/FT Artifact Export and Diagnostics Summary

**Predictions.csv writes added to DL and FT train templates with artifact preservation rules in CLAUDE.md protocol context**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-21T01:47:28Z
- **Completed:** 2026-03-21T01:49:18Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- DL template writes predictions.csv from best model checkpoint on val set with .cpu().numpy() for GPU safety
- FT template writes predictions.csv for loss/perplexity metrics with per-sample loss values
- DL/FT CLAUDE.md protocol rules protect predictions.csv and model artifacts from agent removal
- 9 new tests covering template rendering and artifact preservation rules

## Task Commits

Each task was committed atomically:

1. **Task 1: Add predictions.csv writes to DL and FT templates** - `bc6f611` (feat)
2. **Task 2: Add artifact preservation rules to DL/FT template_context** - `1818116` (feat)

_Note: TDD tasks have RED+GREEN in single commits (test + implementation)_

## Files Created/Modified
- `src/mlforge/templates/dl_train.py.j2` - Added predictions.csv write after training loop with best_model.pt reload
- `src/mlforge/templates/ft_train.py.j2` - Added predictions.csv write guarded to loss/perplexity metrics
- `src/mlforge/deeplearning/__init__.py` - Added artifact preservation domain rule for predictions.csv and best_model.pt
- `src/mlforge/finetuning/__init__.py` - Added artifact preservation domain rule for predictions.csv and best_adapter
- `tests/mlforge/test_templates.py` - 9 new tests for DL/FT predictions and artifact rules

## Decisions Made
- DL predictions use best_model.pt state dict reload (not last epoch) for accurate diagnostics
- FT predictions guarded to loss/perplexity only -- ROUGE produces text, not numeric values suitable for diagnostics engine
- FT uses y_true=0.0 placeholder since loss is self-referential (no ground truth comparison)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three domains (tabular, DL, FT) now write predictions.csv for diagnostics engine
- All three domains have artifact preservation rules in CLAUDE.md protocol
- Ready for diagnostics engine integration testing

---
*Phase: 17-wire-dl-ft-artifact-export-diagnostics*
*Completed: 2026-03-21*
