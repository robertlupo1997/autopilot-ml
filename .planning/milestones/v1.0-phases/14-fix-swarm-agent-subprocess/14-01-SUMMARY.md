---
phase: 14-fix-swarm-agent-subprocess
plan: 01
subsystem: swarm
tags: [subprocess, cli-flags, worktree, permissions, budget-inheritance]

requires:
  - phase: 05-domain-plugins-swarm
    provides: SwarmManager base implementation with worktree creation and scoreboard
  - phase: 13-wire-dead-code-rich-profile
    provides: publish_result wiring in SwarmManager.run()
provides:
  - Engine-matching CLI flags in swarm agent subprocess (--dangerously-skip-permissions, --output-format json, --max-budget-usd, --append-system-prompt)
  - CLAUDE.md protocol copied into worktrees during setup()
  - .mlforge/ directory created in each worktree for state persistence
  - state.json write instruction in swarm template for scoreboard integration
affects: [swarm-e2e, template-runtime-artifacts]

tech-stack:
  added: [shutil]
  patterns: [engine-matching subprocess flags, worktree file provisioning, template-driven state persistence]

key-files:
  created: [tests/mlforge/test_mlforge_swarm.py]
  modified: [src/mlforge/swarm/__init__.py, src/mlforge/templates/swarm_claude.md.j2]

key-decisions:
  - "Use child_config.budget_usd (total session budget) for --max-budget-usd, not per_experiment_budget_usd"
  - "Read CLAUDE.md content inline via Path.read_text() for --append-system-prompt (matching engine.py pattern)"
  - "Omit --append-system-prompt entirely when CLAUDE.md missing (graceful skip)"

patterns-established:
  - "Worktree provisioning: copy protocol files and create state dirs during setup() before agent spawn"
  - "Template-driven state persistence: agents write state.json, coordinator reads it"

requirements-completed: [SWARM-01, SWARM-02, SWARM-03, SWARM-04]

duration: 3min
completed: 2026-03-20
---

# Phase 14 Plan 01: Fix Swarm Agent Subprocess Summary

**Engine-matching CLI flags (--dangerously-skip-permissions, --max-budget-usd, --output-format json, --append-system-prompt) in swarm _build_agent_command(), CLAUDE.md worktree copy, .mlforge dir creation, and state.json template instruction**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T23:06:55Z
- **Completed:** 2026-03-20T23:10:08Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Fixed _build_agent_command() to include all required CLI flags matching engine.py pattern
- setup() now copies CLAUDE.md from experiment_dir to each worktree and creates .mlforge/ directory
- swarm_claude.md.j2 includes State Persistence section instructing agents to write state.json with best_metric, best_commit, experiment_count
- 8 new tests covering all flag assertions, CLAUDE.md copy, .mlforge dir, and template content

## Task Commits

Each task was committed atomically:

1. **Task 1: Write tests for swarm command flags, CLAUDE.md copy, and state.json template** - `1320691` (test)
2. **Task 2: Fix _build_agent_command(), setup(), and swarm template** - `aa52671` (feat)

## Files Created/Modified
- `tests/mlforge/test_mlforge_swarm.py` - 8 tests for command flags, setup side effects, and template content
- `src/mlforge/swarm/__init__.py` - Fixed _build_agent_command() with engine-matching flags, setup() with CLAUDE.md copy and .mlforge creation
- `src/mlforge/templates/swarm_claude.md.j2` - Added State Persistence section with state.json schema

## Decisions Made
- Used child_config.budget_usd (total session budget for child) for --max-budget-usd, not per_experiment_budget_usd -- child agent's own engine handles per-experiment budgeting internally
- Read CLAUDE.md content via Path.read_text() inline for --append-system-prompt, matching the engine.py pattern from Phase 6
- Omit --append-system-prompt entirely when CLAUDE.md is missing (graceful skip, not error)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Swarm agent subprocess now has all required flags for E2E operation
- Agents will have CLAUDE.md protocol context and can write state.json for scoreboard
- Ready for Phase 16 (Wire Template Runtime Artifacts) which depends on Phase 14

---
*Phase: 14-fix-swarm-agent-subprocess*
*Completed: 2026-03-20*
