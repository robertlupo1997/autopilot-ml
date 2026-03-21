---
phase: 21-fix-engine-cli-integration-wiring
plan: 01
subsystem: engine
tags: [integration, diagnostics, drafts, guardrails, cli]

requires:
  - phase: 20-wire-domain-aware-engine-drafts
    provides: get_families_for_domain domain dispatch for draft phase
provides:
  - "sft in _CLASSIFICATION_TASKS for FT diagnostics routing"
  - "_DOMAIN_DEFAULT_TASK dict for domain-aware task fallback"
  - "max_turns system prompt injection in _run_one_experiment"
  - "Unconditional dataset_path in CLI plugin_settings"
affects: [22-fix-engine-cli-integration-wiring]

tech-stack:
  added: []
  patterns: [domain-default-task-dict, protocol-first-guardrails]

key-files:
  created: []
  modified:
    - src/mlforge/engine.py
    - src/mlforge/cli.py
    - tests/mlforge/test_engine.py
    - tests/mlforge/test_cli.py

key-decisions:
  - "max_turns injected as system prompt text, not CLI flag (protocol-first philosophy)"
  - "_DOMAIN_DEFAULT_TASK as module-level dict for reuse across _run_draft_phase and _run_diagnostics"
  - "dataset_path set before if/else branch so both simple and expert mode get it"

patterns-established:
  - "Domain-default-task pattern: module-level _DOMAIN_DEFAULT_TASK dict for domain-aware fallbacks"
  - "Protocol-first guardrails: turn limits as system prompt instructions, budget as CLI backstop"

requirements-completed: [DL-04, GUARD-05, INTL-04, FT-03, INTL-05, DL-01, INTL-01, CORE-08, GUARD-02]

duration: 3min
completed: 2026-03-21
---

# Phase 21 Plan 01: Fix Engine/CLI Integration Wiring Summary

**Four integration bug fixes: sft classification routing, domain-aware task fallback, max_turns system prompt injection, unconditional dataset_path**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-21T16:23:33Z
- **Completed:** 2026-03-21T16:26:33Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Fixed FT diagnostics routing by adding "sft" to _CLASSIFICATION_TASKS
- Added _DOMAIN_DEFAULT_TASK dict so DL draft phase uses image_classification (not hardcoded classification)
- Injected max_turns_per_experiment as system prompt instruction for protocol-first turn limiting
- Set dataset_path unconditionally in CLI so DL baseline gate finds dataset in both simple and expert mode

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for all four integration bugs** - `675dc4a` (test)
2. **Task 2: Apply all four integration fixes** - `23c856d` (feat)

## Files Created/Modified
- `src/mlforge/engine.py` - Added sft to _CLASSIFICATION_TASKS, _DOMAIN_DEFAULT_TASK dict, max_turns system prompt injection, domain-aware task fallback in _run_draft_phase and _run_diagnostics
- `src/mlforge/cli.py` - Set dataset_path unconditionally before simple/expert mode branch
- `tests/mlforge/test_engine.py` - 5 new tests for sft routing, DL draft fallback, max_turns prompt; 2 existing tests updated
- `tests/mlforge/test_cli.py` - 2 new tests for dataset_path in DL simple mode and expert mode

## Decisions Made
- max_turns injected as system prompt text, not CLI flag (consistent with protocol-first philosophy -- agent respects instruction, budget provides hard backstop)
- _DOMAIN_DEFAULT_TASK as module-level dict for reuse across _run_draft_phase and _run_diagnostics (DRY)
- dataset_path set before the if/else metric branch so both simple and expert mode get it

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing test for system prompt content**
- **Found during:** Task 2
- **Issue:** test_uses_append_system_prompt_with_inline_content used exact equality check that broke when max_turns appends to system prompt
- **Fix:** Changed assertion from `==` to `in` to allow appended content
- **Files modified:** tests/mlforge/test_engine.py
- **Committed in:** 23c856d (Task 2 commit)

**2. [Rule 1 - Bug] Updated existing test for missing CLAUDE.md behavior**
- **Found during:** Task 2
- **Issue:** test_no_append_system_prompt_when_claude_md_missing assumed no system prompt when CLAUDE.md absent, but max_turns now creates one
- **Fix:** Set max_turns_per_experiment=0 in test config to isolate the original behavior
- **Files modified:** tests/mlforge/test_engine.py
- **Committed in:** 23c856d (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs in existing tests)
**Impact on plan:** Both auto-fixes necessary for test correctness after new behavior. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All four integration gaps closed
- 578 tests passing, full suite green
- Ready for phase 22 (remaining integration wiring)

---
*Phase: 21-fix-engine-cli-integration-wiring*
*Completed: 2026-03-21*

## Self-Check: PASSED
