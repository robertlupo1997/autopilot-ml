---
phase: 15-fix-ft-simple-mode-metric-mapping
plan: 01
subsystem: scaffold
tags: [finetuning, metric-mapping, simple-mode, scaffold, domain-defaults]

# Dependency graph
requires:
  - phase: 12-wire-plugin-validation-task-mapping
    provides: validate_config gate and _map_task_for_domain in scaffold.py
provides:
  - FT domain entry in _TASK_TYPE_MAP (classification/regression -> sft)
  - Metric/direction override for invalid FT metrics (accuracy -> loss/minimize)
  - Default model_name for FT simple mode (meta-llama/Llama-3.2-1B)
affects: [16-wire-template-runtime-artifacts]

# Tech tracking
tech-stack:
  added: []
  patterns: [domain-specific metric defaults, lazy plugin import for validation]

key-files:
  created: []
  modified:
    - src/mlforge/scaffold.py
    - tests/mlforge/test_scaffold.py

key-decisions:
  - "Lazy import FineTuningPlugin._VALID_METRICS inside _map_task_for_domain to avoid import-time dependency"
  - "Override metric only when current metric is NOT in plugin's _VALID_METRICS (preserves expert mode)"
  - "Updated test_rejects_ft_without_model_name to test_ft_without_model_name_gets_default since auto-default now applies"

patterns-established:
  - "_METRIC_DEFAULTS dict pattern for domain-specific metric/direction overrides"
  - "_MODEL_NAME_DEFAULTS dict pattern for domain-specific required field defaults"

requirements-completed: [FT-04, UX-01]

# Metrics
duration: 2min
completed: 2026-03-20
---

# Phase 15 Plan 01: Fix FT Simple Mode Metric Mapping Summary

**FT simple mode metric override from accuracy to loss/minimize with default model_name and sft task mapping in scaffold.py**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-20T23:29:42Z
- **Completed:** 2026-03-20T23:32:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- FT simple mode (`--domain finetuning`) now reaches scaffold without ValueError
- Invalid profiler metric (accuracy) auto-overridden to loss with direction minimize
- Expert mode FT metrics (perplexity, rouge1, etc.) preserved when explicitly set
- Default model_name (meta-llama/Llama-3.2-1B) auto-set for FT simple mode
- FT task types mapped: classification/regression -> sft

## Task Commits

Each task was committed atomically:

1. **Task 1: Add FT metric override tests + implement _map_task_for_domain extension** - `a60134b` (feat)
2. **Task 2: Full test suite regression check** - no commit (verification-only task, 502 mlforge tests passed)

## Files Created/Modified
- `src/mlforge/scaffold.py` - Added finetuning to _TASK_TYPE_MAP, _METRIC_DEFAULTS, _MODEL_NAME_DEFAULTS; extended _map_task_for_domain with metric/direction override and model_name default logic
- `tests/mlforge/test_scaffold.py` - Added 6 new tests (metric override, expert preservation, direction, default model_name, task mapping, E2E scaffold); updated 1 existing test

## Decisions Made
- Lazy import FineTuningPlugin._VALID_METRICS inside _map_task_for_domain conditional to avoid import-time dependency on finetuning module
- Override metric only when current metric is NOT in plugin's _VALID_METRICS set -- preserves expert mode explicit metrics like perplexity
- Updated test_rejects_ft_without_model_name to test_ft_without_model_name_gets_default because auto-default model_name now prevents the ValueError

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing test_ft_task_no_mapping expectations**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Existing test expected FT classification task to NOT be remapped, but new _TASK_TYPE_MAP entry maps it to sft
- **Fix:** Renamed to test_ft_task_mapped_to_sft and updated assertion to expect "sft"
- **Files modified:** tests/mlforge/test_scaffold.py
- **Verification:** All scaffold tests pass
- **Committed in:** a60134b

**2. [Rule 1 - Bug] Updated test_rejects_ft_without_model_name**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Test expected ValueError when model_name missing, but new auto-default sets model_name for FT domain
- **Fix:** Renamed to test_ft_without_model_name_gets_default, now asserts scaffold succeeds and model_name is set
- **Files modified:** tests/mlforge/test_scaffold.py
- **Verification:** All scaffold tests pass
- **Committed in:** a60134b

---

**Total deviations:** 2 auto-fixed (2 bugs - existing test expectations invalidated by new feature)
**Impact on plan:** Both auto-fixes necessary for test correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- FT simple mode path fully operational through scaffold
- Phase 16 (Wire Template Runtime Artifacts) can proceed -- predictions.csv and best_model.joblib wiring
- All 502 mlforge tests pass

---
*Phase: 15-fix-ft-simple-mode-metric-mapping*
*Completed: 2026-03-20*
