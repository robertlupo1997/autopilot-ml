---
phase: 03-scaffold-cli-run-engine
plan: 01
subsystem: cli
tags: [argparse, scaffold, cli, config, hooks, jinja2]

requires:
  - phase: 01-core-engine
    provides: Config, plugins, hooks, templates
  - phase: 02-tabular-plugin
    provides: TabularPlugin with scaffold/template_context
provides:
  - CLI entry point (mlforge <dataset> <goal>)
  - scaffold_experiment() wiring plugins + templates + hooks
  - Config budget/timeout/model fields
affects: [03-02, 03-03, 04-e2e]

tech-stack:
  added: [argparse]
  patterns: [CLI-to-scaffold pipeline, auto-register plugin, TOML config serialization]

key-files:
  created: [src/mlforge/cli.py, src/mlforge/scaffold.py, tests/mlforge/test_cli.py, tests/mlforge/test_scaffold.py]
  modified: [src/mlforge/config.py]

key-decisions:
  - "CLI overrides Config defaults (not TOML merge) for simplicity"
  - "Auto-register TabularPlugin in scaffold if not in registry"
  - "TOML serialization via string formatting (no extra dependency)"

patterns-established:
  - "CLI builds Config from defaults + flag overrides, passes to scaffold"
  - "scaffold_experiment is the single entry point that wires plugin, templates, hooks, dataset copy"

requirements-completed: [CORE-01, GUARD-01]

duration: 3min
completed: 2026-03-20
---

# Phase 03 Plan 01: Scaffold + CLI Summary

**argparse CLI entry point with dataset validation, Config budget/model fields, and plugin-based experiment directory scaffolding**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T00:40:26Z
- **Completed:** 2026-03-20T00:43:26Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 5

## Accomplishments
- CLI parses dataset, goal, and all optional flags (domain, budget-usd, budget-minutes, budget-experiments, model, output-dir, resume)
- Config extended with budget_usd, per_experiment_timeout_sec, per_experiment_budget_usd, max_turns_per_experiment, model -- all loadable from TOML
- scaffold_experiment creates complete directory: prepare.py, train.py, CLAUDE.md, experiments.md, .claude/settings.json, guard-frozen.sh, mlforge.config.toml, dataset copy

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: CLI entry point + Config extension**
   - `ef26d93` (test) - failing tests for CLI parsing and Config new fields
   - `8cb7aac` (feat) - cli.py with argparse, Config budget/model fields, scaffold stub
2. **Task 2: Scaffold experiment directory**
   - `3fe5674` (test) - failing tests for scaffold_experiment
   - `0176d3a` (feat) - full scaffold_experiment with plugin, templates, hooks, dataset copy, TOML

## Files Created/Modified
- `src/mlforge/cli.py` - CLI entry point with argparse, dataset validation, Config building
- `src/mlforge/scaffold.py` - scaffold_experiment wiring plugin, templates, hooks, dataset, config TOML
- `src/mlforge/config.py` - Added budget_usd, per_experiment_timeout_sec, per_experiment_budget_usd, max_turns_per_experiment, model fields
- `tests/mlforge/test_cli.py` - 19 tests for CLI parsing, validation, Config new fields
- `tests/mlforge/test_scaffold.py` - 14 tests for directory creation, files, hooks, TOML

## Decisions Made
- CLI builds Config from defaults then applies flag overrides (not TOML-then-CLI merge) -- simpler, TOML loading deferred to run engine
- Auto-registers TabularPlugin in scaffold if not already in registry -- avoids requiring explicit registration before scaffold
- TOML serialization uses string formatting (repr for lists) -- no tomli_w dependency needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TOML max_turns field name mismatch**
- **Found during:** Task 1 (Config extension)
- **Issue:** Config.load() was reading `max_turns_per_experiment` from TOML but plan specified `max_turns` as the TOML key
- **Fix:** Changed TOML key lookup from `max_turns_per_experiment` to `max_turns`
- **Files modified:** src/mlforge/config.py
- **Verification:** test_budget_usd_from_toml passes with max_turns = 50
- **Committed in:** 8cb7aac (Task 1 feat commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor naming fix for TOML field consistency. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CLI and scaffold are ready for the run engine (Plan 03-02) to wire up
- scaffold_experiment returns the target_dir that the engine will operate in
- Config has all budget/timeout/model fields the engine needs

---
*Phase: 03-scaffold-cli-run-engine*
*Completed: 2026-03-20*
