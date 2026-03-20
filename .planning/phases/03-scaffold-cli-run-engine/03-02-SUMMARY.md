---
phase: 03-scaffold-cli-run-engine
plan: 02
subsystem: guardrails
tags: [rich, psutil, cost-tracking, deviation-handling, resource-limits]

requires:
  - phase: 01-core-engine
    provides: "SessionState, Config dataclasses with JSON persistence"
provides:
  - "ResourceGuardrails: hard stops on cost, time, experiments, disk"
  - "CostTracker: per-experiment cost accumulation with SessionState sync"
  - "DeviationHandler: keep/revert/retry/stop routing for experiment outcomes"
  - "LiveProgress: rich terminal display for overnight run visibility"
  - "Config budget fields: budget_usd, per_experiment_timeout_sec, per_experiment_budget_usd, max_turns_per_experiment, model"
  - "SessionState.cost_spent_usd: persistent cost tracking field"
affects: [03-scaffold-cli-run-engine, 04-e2e-validation]

tech-stack:
  added: [rich>=13.0, psutil>=6.0]
  patterns: [guardrail-before-each-iteration, cost-accumulator-in-state, deviation-routing]

key-files:
  created:
    - src/mlforge/guardrails.py
    - src/mlforge/progress.py
    - tests/mlforge/test_guardrails.py
    - tests/mlforge/test_progress.py
  modified:
    - src/mlforge/state.py
    - src/mlforge/config.py
    - pyproject.toml

key-decisions:
  - "ResourceGuardrails.should_stop delegates to stop_reason for DRY single-source-of-truth"
  - "CostTracker updates SessionState.cost_spent_usd directly for crash-safe persistence"
  - "DeviationHandler resets retry count on keep (not on revert) to prevent retry leak"
  - "min_free_disk_gb defaults to 1.0 GB as instance attribute (not Config field) for simplicity"

patterns-established:
  - "Guardrail-before-iteration: check should_stop before each experiment spawn"
  - "Cost-in-state: cost_spent_usd lives in SessionState for JSON persistence across crashes"
  - "Deviation routing: single handle() method returns action string for clean control flow"

requirements-completed: [GUARD-02, GUARD-04, GUARD-05, INTL-07, CORE-09]

duration: 3min
completed: 2026-03-20
---

# Phase 03 Plan 02: Guardrails + Cost Tracking + Live Progress Summary

**ResourceGuardrails with 4 hard stops (cost/time/experiments/disk), CostTracker with SessionState sync, DeviationHandler routing crash/OOM/timeout/divergence, and LiveProgress rich terminal display**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T00:40:24Z
- **Completed:** 2026-03-20T00:43:41Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- ResourceGuardrails enforces 4 independent hard stops: experiment count, cost cap, wall-clock time, and disk space
- CostTracker accumulates per-experiment costs and syncs to SessionState.cost_spent_usd for crash-safe persistence
- DeviationHandler routes experiment outcomes through OOM retry (max 2), crash/timeout revert, metric validation, and improvement check
- LiveProgress renders a rich Table with experiment count, best metric, cost, keeps/reverts, and status
- Config extended with budget_usd, per_experiment_timeout_sec, per_experiment_budget_usd, max_turns_per_experiment, model

## Task Commits

Each task was committed atomically:

1. **Task 1: ResourceGuardrails + CostTracker + DeviationHandler** - `3fed4d3` (test) + `ff46636` (feat)
2. **Task 2: LiveProgress terminal display** - `ed22c04` (test) + `f373a59` (feat)

_TDD tasks have separate test (RED) and implementation (GREEN) commits._

## Files Created/Modified
- `src/mlforge/guardrails.py` - ResourceGuardrails, CostTracker, DeviationHandler classes
- `src/mlforge/progress.py` - LiveProgress with rich.live.Live terminal display
- `src/mlforge/state.py` - Added cost_spent_usd field to SessionState
- `src/mlforge/config.py` - Added budget_usd, per_experiment_timeout_sec, per_experiment_budget_usd, max_turns_per_experiment, model fields
- `pyproject.toml` - Added rich>=13.0 and psutil>=6.0 dependencies
- `tests/mlforge/test_guardrails.py` - 30 tests for guardrails, cost tracker, deviation handler
- `tests/mlforge/test_progress.py` - 12 tests for LiveProgress rendering and lifecycle

## Decisions Made
- ResourceGuardrails.should_stop delegates to stop_reason (single source of truth, no duplicated condition logic)
- CostTracker updates SessionState.cost_spent_usd directly so cost persists across crashes via existing to_json
- DeviationHandler resets retry count on keep (not on revert) to prevent retry counter from leaking across unrelated failures
- min_free_disk_gb is an instance attribute (1.0 GB default) rather than a Config field -- keeps Config focused on user-facing settings

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing Config fields for guardrails**
- **Found during:** Task 1 (before writing tests)
- **Issue:** Config was missing budget_usd, per_experiment_timeout_sec, per_experiment_budget_usd, max_turns_per_experiment, and model fields that guardrails.py requires
- **Fix:** Added fields to Config dataclass and TOML loader
- **Files modified:** src/mlforge/config.py
- **Verification:** Existing config tests pass (26 tests), new guardrails tests use Config with budget_usd
- **Committed in:** ff46636 (Task 1 implementation commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Config fields were already specified in the plan's interface section; they just needed to be added to the actual dataclass. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Guardrails, cost tracking, deviation handling, and live progress are ready for the run engine (plan 03)
- The run engine can now check should_stop() before each iteration, track costs, route experiment outcomes, and display progress
- 240 tests passing across the full mlforge test suite

## Self-Check: PASSED

All 7 files verified present. All 4 commit hashes found in git log.

---
*Phase: 03-scaffold-cli-run-engine*
*Completed: 2026-03-20*
