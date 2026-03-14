---
phase: 10-multi-agent-swarm
plan: 02
subsystem: infra
tags: [subprocess, git-worktrees, swarm, coordination, signal, argparse, fcntl]

# Dependency graph
requires:
  - phase: 10-multi-agent-swarm
    provides: SwarmScoreboard, swarm_claims TTL files, and GitManager.create_worktree/remove_worktree from Plan 10-01
  - phase: 09-resume-capability
    provides: cli.py and scaffold.py patterns used here
  - phase: 03-cli-and-integration
    provides: cli.py base structure extended with --agents flag
provides:
  - SwarmManager class composing scoreboard + claims + git worktrees into orchestration
  - spawn_agent function building claude -p subprocess with --allowedTools
  - CLI --agents N flag with validation and swarm invocation
  - scaffold .gitignore with .swarm/ coordination file entries
  - swarm_claude.md.tmpl agent coordination template with fcntl locking code
affects:
  - 10-03-swarm-validation: manual validation script uses SwarmManager and spawn_agent

# Tech tracking
tech-stack:
  added: [signal (SIGINT handler), subprocess.Popen (claude -p spawning)]
  patterns:
    - "Pattern: SwarmManager composes SwarmScoreboard + GitManager + subprocess.Popen"
    - "Pattern: spawn_agent builds claude -p command with --allowedTools for headless operation"
    - "Pattern: SIGINT handler sets _shutdown flag and proc.terminate() all agents"
    - "Pattern: Round-robin _divide_families with cap at len(ALGORITHM_FAMILIES)"

key-files:
  created:
    - src/automl/swarm.py
    - src/automl/templates/swarm_claude.md.tmpl
    - tests/test_swarm.py
  modified:
    - src/automl/cli.py
    - src/automl/scaffold.py
    - tests/test_cli.py
    - tests/test_scaffold.py

key-decisions:
  - "Cap n_agents at len(ALGORITHM_FAMILIES[task_type]) with stderr warning -- prevents empty draft phase"
  - "spawn_agent includes --max-turns 50 (same as run-validation-test.sh) for bounded experiment runs"
  - "CLI detects task_type via load_data() after scaffolding for SwarmManager initialization"
  - "swarm_claude.md.tmpl uses {placeholder} format (not template engine) -- injected at spawn time via prompt"

patterns-established:
  - "Pattern: TDD RED/GREEN -- write failing imports first, then implement to pass"
  - "Pattern: SwarmManager try/finally teardown ensures worktree cleanup even on error"

requirements-completed: [SWARM-04, SWARM-05, SWARM-06, SWARM-07, SWARM-08]

# Metrics
duration: 4min
completed: 2026-03-14
---

# Phase 10 Plan 02: SwarmManager Orchestrator Summary

**SwarmManager composing scoreboard + worktrees + claude -p subprocesses, CLI --agents flag, .swarm/ gitignore, and fcntl-locked agent coordination template -- 63 tests across all modified modules**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-14T05:19:19Z
- **Completed:** 2026-03-14T05:23:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- SwarmManager: setup (worktrees + config.json), run (SIGINT + agents), _monitor_loop (10s poll), teardown (cleanup + prune)
- spawn_agent: claude -p command with --allowedTools, --output-format json, --max-turns 50
- CLI --agents N flag: default=1, validates >=1, help mentions external terminal, invokes SwarmManager when >1
- scaffold .gitignore extended with 5 .swarm/ coordination file entries
- swarm_claude.md.tmpl: Swarm Coordination Protocol with before/after experiment sections and exact fcntl Python snippet
- 25 new unit tests for SwarmManager + 5 CLI tests + 4 scaffold tests = 34 new tests; full suite 233 passing

## Task Commits

Each task was committed atomically:

1. **Task 1: SwarmManager module with tests** - `81029ff` (feat)
2. **Task 2: CLI --agents flag, scaffold .gitignore, and swarm CLAUDE.md template** - `98cdb63` (feat)

## Files Created/Modified
- `src/automl/swarm.py` - SwarmManager class (setup, run, _monitor_loop, teardown) and spawn_agent function
- `src/automl/templates/swarm_claude.md.tmpl` - Agent coordination protocol with fcntl locking code and {placeholders}
- `tests/test_swarm.py` - 25 unit tests: TestDivideFamilies, TestSetup, TestTeardown, TestSpawnAgent
- `src/automl/cli.py` - Added --agents N flag with validation and SwarmManager invocation
- `src/automl/scaffold.py` - Extended _gitignore_content() with 5 .swarm/ entries
- `tests/test_cli.py` - Added TestCliAgentsFlag class (5 tests)
- `tests/test_scaffold.py` - Added TestScaffoldGitignoreSwarm class (4 tests)

## Decisions Made
- Cap n_agents at len(ALGORITHM_FAMILIES[task_type]) with stderr warning -- prevents empty draft phase for over-requested agents
- spawn_agent includes --max-turns 50 consistent with existing run-validation-test.sh pattern
- CLI invokes load_data() to detect task_type after scaffolding (needed for ALGORITHM_FAMILIES lookup)
- swarm_claude.md.tmpl uses simple {placeholder} format -- agent-specific values injected in spawn prompt, not template rendering

## Deviations from Plan

None - plan executed exactly as written. All behaviors from must_haves.truths and artifacts verified.

## Issues Encountered

None. All tests passed on first GREEN run. Full 233-test suite passed immediately.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- SwarmManager, spawn_agent, CLI --agents, scaffold .gitignore, and swarm_claude.md.tmpl ready for Plan 10-03
- Plan 10-03 will create scripts/run-swarm-test.sh for manual 2-agent validation
- No blockers -- all integration points from Plan 10-01 composed correctly

---
*Phase: 10-multi-agent-swarm*
*Completed: 2026-03-14*
