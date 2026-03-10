---
phase: 02-core-loop
plan: 03
subsystem: templates
tags: [markdown, templates, loop-protocol, program-md, claude-md]

# Dependency graph
requires:
  - phase: 02-01
    provides: loop_helpers.py (should_keep, is_stagnating, crash detection, strategy shift)
  - phase: 02-02
    provides: drafts.py (ALGORITHM_FAMILIES, generate_draft_train_py, select_best_draft)
provides:
  - program.md.tmpl template with dataset-specific placeholders and domain expertise section
  - claude.md.tmpl static loop protocol with NEVER STOP, multi-draft, keep/revert, stagnation, crash recovery
  - render_program_md() and render_claude_md() functions in templates/__init__.py
affects: [03-cli, orchestrator, experiment-scaffolding]

# Tech tracking
tech-stack:
  added: []
  patterns: [string-format-template-rendering, static-protocol-document]

key-files:
  created:
    - src/automl/templates/__init__.py
    - src/automl/templates/program.md.tmpl
    - src/automl/templates/claude.md.tmpl
    - tests/test_templates.py
  modified: []

key-decisions:
  - "CLAUDE.md template is static (no placeholders) -- rendered by simply reading the file"
  - "program.md uses Python str.format() for placeholder substitution"
  - "CLAUDE.md references automl.drafts API (ALGORITHM_FAMILIES, generate_draft_train_py, select_best_draft) by name"

patterns-established:
  - "Template rendering: .tmpl files in src/automl/templates/, render functions in __init__.py"
  - "Static vs dynamic templates: CLAUDE.md is static protocol, program.md has dataset-specific substitution"

requirements-completed: [CTX-01, CTX-02, CTX-03, LOOP-02, LOOP-03]

# Metrics
duration: 2min
completed: 2026-03-10
---

# Phase 2 Plan 3: Templates Summary

**program.md and CLAUDE.md templates encoding the complete autonomous experiment loop protocol with domain context injection**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-10T19:33:05Z
- **Completed:** 2026-03-10T19:35:27Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 4

## Accomplishments
- program.md.tmpl with 6 placeholders (dataset_name, goal_description, metric_name, direction, data_summary, baselines) and human-editable Domain Expertise section
- claude.md.tmpl with complete loop protocol: NEVER STOP, multi-draft initialization (Phase 1), iterative improvement loop (Phase 2), keep/revert logic, stagnation detection (5 consecutive reverts), crash recovery (3 attempts), run.log redirection, grep metric extraction
- render_program_md() and render_claude_md() functions for experiment scaffolding
- 20 template-specific tests, 94 total tests green

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing template tests** - `b78c2af` (test)
2. **Task 1 GREEN: Templates + render functions** - `0652c07` (feat)

## Files Created/Modified
- `src/automl/templates/__init__.py` - render_program_md() and render_claude_md() functions
- `src/automl/templates/program.md.tmpl` - Dataset context template with placeholders
- `src/automl/templates/claude.md.tmpl` - Complete autonomous loop protocol document
- `tests/test_templates.py` - 20 tests covering structure, content, and rendering

## Decisions Made
- CLAUDE.md is a static document (no placeholders) -- render_claude_md() simply reads and returns the file
- program.md uses Python str.format() for clean placeholder substitution with defaults for data_summary and baselines
- CLAUDE.md references automl.drafts API functions by name (ALGORITHM_FAMILIES, generate_draft_train_py, select_best_draft) to guide the agent

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Phase 2 plans (01, 02, 03) complete
- Templates ready for CLI scaffolding in Phase 3
- Full autonomous loop protocol encoded: loop_helpers.py + drafts.py + templates

---
*Phase: 02-core-loop*
*Completed: 2026-03-10*
