---
phase: 01-core-engine-plugin-infrastructure
plan: 03
subsystem: core
tags: [protocol, plugin, jinja2, hooks, guard-script, structural-subtyping]

# Dependency graph
requires:
  - phase: 01-core-engine-plugin-infrastructure
    plan: 01
    provides: Config dataclass with frozen_files, mutable_files, metric, direction
  - phase: 01-core-engine-plugin-infrastructure
    plan: 02
    provides: GitManager and JournalEntry for experiment orchestration
provides:
  - DomainPlugin Protocol with @runtime_checkable for structural subtyping
  - Plugin registry (register/get/list) with protocol conformance validation
  - Jinja2 template rendering for CLAUDE.md with plugin-injected domain rules
  - Jinja2 template rendering for experiments.md with run metadata
  - Hook settings.json generator with PreToolUse guard configuration
  - Executable guard script that denies writes to frozen files
affects: [02-experiment-loop, 03-cli-and-integration, tabular-plugin]

# Tech tracking
tech-stack:
  added: [jinja2]
  patterns: [typing.Protocol structural subtyping, module-level registry dict, PackageLoader template loading, stdin JSON hook protocol]

key-files:
  created:
    - src/mlforge/plugins.py
    - src/mlforge/templates/__init__.py
    - src/mlforge/templates/base_claude.md.j2
    - src/mlforge/templates/base_experiments.md.j2
    - src/mlforge/hooks.py
    - tests/mlforge/test_plugins.py
    - tests/mlforge/test_templates.py
    - tests/mlforge/test_hooks.py
  modified: []

key-decisions:
  - "Templates package: put rendering functions in templates/__init__.py to coexist with templates/*.j2 files (avoids module/package name collision)"
  - "Guard script uses python3 fallback for JSON parsing instead of requiring jq"
  - "Hook settings include both permissions.deny and PreToolUse hook for defense in depth"

patterns-established:
  - "Plugin Protocol pattern: @runtime_checkable Protocol for structural subtyping without inheritance"
  - "Registry pattern: module-level dict with register/get/list functions"
  - "Template rendering: PackageLoader + plugin.template_context() merge for domain-specific output"
  - "Hook guard: stdin JSON -> extract file_path -> check against frozen list -> deny/allow"

requirements-completed: [CORE-03, CORE-07]

# Metrics
duration: 3min
completed: 2026-03-19
---

# Phase 1 Plan 3: Plugin Protocol + Templates + Hooks Summary

**DomainPlugin Protocol with registry, Jinja2 CLAUDE.md/experiments.md rendering, and frozen-file guard hook engine -- 28 new tests, 64 total phase tests**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-19T22:56:45Z
- **Completed:** 2026-03-19T22:59:53Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- DomainPlugin Protocol enables structural subtyping -- any class with matching attributes/methods satisfies the contract without inheritance
- Plugin registry validates conformance on registration and provides lookup by name
- Jinja2 renders CLAUDE.md with domain-specific rules, metric info, and frozen/mutable file lists from merged plugin + config context
- Hook engine generates valid .claude/settings.json and executable guard script that denies writes to frozen files

## Task Commits

Each task was committed atomically:

1. **Task 1: Plugin protocol + Jinja2 template rendering** - `2e419e7` (feat)
2. **Task 2: Hook engine for frozen file enforcement** - `0ff0e25` (feat)

_Both tasks followed TDD: tests written first (RED), then implementation to pass (GREEN)._

## Files Created/Modified
- `src/mlforge/plugins.py` - DomainPlugin Protocol, register/get/list registry functions
- `src/mlforge/templates/__init__.py` - render_claude_md, render_experiments_md, get_template_env
- `src/mlforge/templates/base_claude.md.j2` - Jinja2 template for CLAUDE.md with plugin blocks
- `src/mlforge/templates/base_experiments.md.j2` - Jinja2 template for experiment journal
- `src/mlforge/hooks.py` - generate_hook_settings, generate_guard_script, write_hook_files
- `tests/mlforge/test_plugins.py` - 8 tests for Protocol conformance and registry
- `tests/mlforge/test_templates.py` - 10 tests for template rendering
- `tests/mlforge/test_hooks.py` - 10 tests for hook settings and guard script

## Decisions Made
- Put rendering functions in `templates/__init__.py` rather than a separate `templates.py` to avoid Python module/package name collision with the `templates/` directory containing .j2 files
- Guard script uses `python3 -c` for JSON parsing instead of requiring `jq`, ensuring portability
- Hook settings use both `permissions.deny` (declarative) and `PreToolUse` hook (runtime guard) for defense in depth

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Resolved templates.py / templates/ package name collision**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Plan specified both `src/mlforge/templates.py` (module) and `src/mlforge/templates/` (package directory) -- Python cannot have both
- **Fix:** Moved rendering functions into `src/mlforge/templates/__init__.py` so the package serves as both the template directory and the module
- **Files modified:** src/mlforge/templates/__init__.py (created with rendering functions)
- **Verification:** All 18 plugin + template tests pass, imports work correctly
- **Committed in:** 2e419e7 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Python packaging constraint required structural adjustment. Same API surface, no scope creep.

## Issues Encountered
None beyond the auto-fixed blocking issue above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Phase 1 modules complete: state, config, checkpoint, git_ops, journal, plugins, templates, hooks
- 64 tests across 8 test files, all passing
- Plugin architecture ready for tabular domain plugin implementation (Phase 2 or 3)
- Template rendering ready for scaffold integration
- Hook engine ready for experiment workspace setup

## Self-Check: PASSED

All 8 created files verified present. Both task commits (2e419e7, 0ff0e25) verified in git log.

---
*Phase: 01-core-engine-plugin-infrastructure*
*Completed: 2026-03-19*
