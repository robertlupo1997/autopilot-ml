---
phase: 05-hooks-and-enhanced-scaffolding
plan: 01
subsystem: scaffolding
tags: [claude-code, hooks, settings-json, bash, scaffold]

# Dependency graph
requires:
  - phase: 03-cli-and-integration
    provides: scaffold_experiment function that this plan extends
  - phase: 04-e2e-baseline-test
    provides: finding that CLAUDE.md is primary enforcement, hooks are safety net
provides:
  - scaffold_experiment creates .claude/settings.json with permissions.allow and PreToolUse hooks
  - scaffold_experiment creates executable .claude/hooks/guard-frozen.sh denying writes to prepare.py
  - _dot_claude_settings() helper for .claude/ directory generation
  - _guard_frozen_hook_content() bash hook that enforces mutable zones
affects: [07-e2e-validation-test, cli-usage-docs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hook script reads PreToolUse JSON from stdin, exits 0 with deny JSON or exits 0 silently"
    - "jq with python3 fallback for JSON parsing in bash hooks"
    - "settings.json permissions.allow allowlist pattern for Claude Code projects"

key-files:
  created: []
  modified:
    - src/automl/scaffold.py
    - tests/test_scaffold.py

key-decisions:
  - "permissions.allow allowlist: Bash, Edit(train.py), Write(train.py), Read, Glob, Grep — train.py explicitly scoped, not a wildcard"
  - "Hook exits 0 in all cases (deny JSON for frozen files, silent for allowed) — non-zero exit would abort Claude Code"
  - "jq with python3 fallback in hook ensures portability across environments"
  - "CLAUDE.md remains primary enforcement mechanism; hook is safety net per Phase 4 findings"

patterns-established:
  - "TDD RED commit before GREEN implementation commit"
  - "Hook script content as Python string literal in scaffold.py — no external template file"
  - "chmod(0o755) on hook script via pathlib Path.chmod() after write_text()"

requirements-completed: [HOOK-01, HOOK-02, HOOK-03, HOOK-04]

# Metrics
duration: 2min
completed: 2026-03-12
---

# Phase 5 Plan 01: Hooks and Enhanced Scaffolding Summary

**scaffold_experiment now generates .claude/settings.json with a tool allowlist and a PreToolUse bash hook that hard-denies writes to prepare.py**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-12T22:05:20Z
- **Completed:** 2026-03-12T22:07:09Z
- **Tasks:** 1 (TDD: 2 commits — RED test then GREEN impl)
- **Files modified:** 2

## Accomplishments
- scaffold_experiment creates .claude/ directory with settings.json and hooks/guard-frozen.sh
- settings.json pre-approves Bash, Edit(train.py), Write(train.py), Read, Glob, Grep — no need for --dangerously-skip-permissions
- guard-frozen.sh reads PreToolUse stdin JSON, denies writes to prepare.py with a reason message, silently allows all other files
- .gitignore updated to exclude .claude/settings.local.json (user-local overrides)
- 9 new tests added (TestScaffoldDotClaude), 2 existing tests updated; 121 total passing (up from 111+)

## Task Commits

Each task was committed atomically (TDD):

1. **RED: Failing tests for .claude/ scaffolding** - `6d08832` (test)
2. **GREEN: Implementation of _dot_claude_settings and _guard_frozen_hook_content** - `7616ed4` (feat)

## Files Created/Modified
- `src/automl/scaffold.py` - Added `_guard_frozen_hook_content()`, `_dot_claude_settings()`, updated `_gitignore_content()`, wired call in `scaffold_experiment()`
- `tests/test_scaffold.py` - Added `TestScaffoldDotClaude` (7 tests), updated file count assertion (7->8), added .gitignore pattern assertion

## Decisions Made
- permissions.allow uses explicit `Edit(train.py)` and `Write(train.py)` rather than wildcard — tightest possible scope
- Hook exits 0 in all cases; deny is signaled via JSON body not exit code (Claude Code convention)
- Python string literal for hook content (textwrap.dedent) rather than an external template file — keeps scaffolding self-contained in one module

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 5 Plan 01 complete: scaffolded experiment directories are now fully Claude Code-aware
- Phase 5 Plan 02 (if any) or Phase 6 (Structured Output) can proceed
- Hooks wire up automatically on `uv run automl` — no manual steps for users

---
*Phase: 05-hooks-and-enhanced-scaffolding*
*Completed: 2026-03-12*
