# Roadmap: AutoML

## Overview

AutoML delivers an autonomous ML experiment framework in seven phases. Phases 1-3 (complete) built the frozen pipeline, autonomous loop, and CLI scaffolding. Phases 4-7 follow a test-fix-test pattern: Phase 4 runs the autonomous loop as-is to discover what breaks, Phase 5 adds hooks and enhanced scaffolding to fix those problems, Phase 6 adds structured output if parsing proves fragile, and Phase 7 re-runs the loop to prove everything works unattended.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Frozen pipeline, mutable modeling template, git operations, and experiment logging
- [x] **Phase 2: Core Loop** - Autonomous experiment loop with multi-draft start, domain context, and resilience (completed 2026-03-10)
- [x] **Phase 3: CLI and Integration** - Project scaffolding CLI and end-to-end validation (completed 2026-03-10)
- [x] **Phase 4: E2E Baseline Test** - Run the autonomous loop as-is on a test dataset, document what works and what breaks (completed 2026-03-11)
- [x] **Phase 5: Hooks and Enhanced Scaffolding** - PreToolUse mutable zone enforcement, .claude/settings.json generation, allowedTools, CLAUDE.md upgrade, UX polish (completed 2026-03-12)
- [x] **Phase 6: Structured Output and Metrics Parsing** - Additive JSON output line in train.py, parse_run_result.py for Phase 7 test harness, optional runner.py JSON parser (completed 2026-03-13)
- [x] **Phase 7: E2E Validation Test** - Re-run the autonomous loop after all changes, prove the system works unattended end-to-end (gap closure in progress) (completed 2026-03-13)
- [x] **Phase 8: Permissions Simplification** - Broaden permissions.allow, add permissions.deny, remove --allowedTools from scripts (completed 2026-03-14)
- [x] **Phase 9: Resume Capability** - Checkpoint persistence for session resume via checkpoint.json and --resume CLI flag (completed 2026-03-14)
- [ ] **Phase 10: Multi-Agent Swarm** - Parallel claude -p agents with git worktrees, scoreboard coordination, and family partitioning

## Phase Details

### Phase 1: Foundation
**Goal**: A single experiment can be run, evaluated, committed or reverted, and logged -- with all safety boundaries in place
**Depends on**: Nothing (first phase)
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PIPE-06, PIPE-07, MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05, GIT-01, GIT-02, GIT-03, GIT-04, GIT-05, LOG-01, LOG-02, LOG-03
**Success Criteria** (what must be TRUE):
  1. User can point the framework at a CSV file and get a working train/test split with cross-validated evaluation on a configurable metric
  2. A baseline train.py runs, prints structured metric output, and the frozen evaluation function scores it correctly
  3. Sanity-check baselines (majority class, mean predictor) are computed and available for comparison
  4. A successful experiment is committed to a run branch with a descriptive message; a failed experiment resets to the last good commit
  5. Each experiment's metric, status, commit hash, and description are appended to results.tsv
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffolding and frozen data pipeline (prepare.py)
- [x] 01-02-PLAN.md — Git state management and experiment logging modules
- [x] 01-03-PLAN.md — Mutable train.py template and experiment runner

### Phase 2: Core Loop
**Goal**: The agent autonomously runs experiments in a loop -- generating diverse drafts, selecting the best, iterating with keep/revert, recovering from crashes, and breaking out of stagnation -- all guided by domain context
**Depends on**: Phase 1
**Requirements**: LOOP-01, LOOP-02, LOOP-03, LOOP-04, LOOP-05, LOOP-06, LOOP-07, LOOP-08, CTX-01, CTX-02, CTX-03, DRAFT-01, DRAFT-02, DRAFT-03, DRAFT-04
**Success Criteria** (what must be TRUE):
  1. The agent generates 3-5 diverse initial drafts (different algorithm families), evaluates them, and selects the best to iterate on
  2. The agent runs autonomously and indefinitely -- executing train.py, extracting the metric, deciding keep or revert, and looping without human intervention
  3. When train.py crashes, the agent reads the traceback, attempts a fix, and moves on (giving up after 3 consecutive failures on the same issue)
  4. After 5 consecutive reverts, the agent shifts to a different strategy category instead of making tiny adjustments
  5. The agent reads program.md at each iteration for domain-specific guidance, and CLAUDE.md provides the loop protocol
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Loop helpers (keep/revert, stagnation, crash tracking) and git revert fix
- [x] 02-02-PLAN.md — Multi-draft initialization system (algorithm families, generation, selection)
- [x] 02-03-PLAN.md — Context templates (program.md and CLAUDE.md loop protocol)

### Phase 3: CLI and Integration
**Goal**: A user can go from CSV file to running autonomous experiment loop with a single CLI command
**Depends on**: Phase 2
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. User runs a CLI command with a CSV path, target column, and metric -- and gets a fully scaffolded project (prepare.py, train.py, program.md, CLAUDE.md, .gitignore, pyproject.toml)
  2. The scaffolded project is immediately runnable with `uv run train.py` and produces valid metric output
  3. End-to-end test: CLI scaffold, then autonomous loop runs on a real dataset and improves beyond the baseline
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Scaffold module: experiment directory generation from CSV
- [x] 03-02-PLAN.md — CLI entry point, entry point registration, and end-to-end validation

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete | 2026-03-10 |
| 2. Core Loop | 3/3 | Complete | 2026-03-10 |
| 3. CLI and Integration | 2/2 | Complete | 2026-03-10 |
| 4. E2E Baseline Test | 1/1 | Complete | 2026-03-11 |
| 5. Hooks + Scaffolding | 2/2 | Complete   | 2026-03-12 |
| 6. Structured Output | 2/2 | Complete   | 2026-03-13 |
| 7. E2E Validation Test | 3/3 | Complete   | 2026-03-13 |
| 8. Permissions Simplification | 1/1 | Complete   | 2026-03-14 |
| 9. Resume Capability | 2/2 | Complete   | 2026-03-14 |
| 10. Multi-Agent Swarm | 0/0 | Not planned | — |

### Phase 4: E2E Baseline Test

**Goal:** Run the autonomous loop as-is on a small test dataset (iris or synthetic), using `claude -p` with --max-turns, and document exactly what works and what breaks — draft generation, keep/revert decisions, frozen file compliance, metric parsing, stagnation handling
**Depends on:** Phase 3
**Requirements:** E2E-BASELINE-01, E2E-BASELINE-02, E2E-BASELINE-03
**Plans:** 1 plan

Plans:
- [x] 04-01-PLAN.md — Run baseline test on iris dataset and document findings

### Phase 5: Hooks and Enhanced Scaffolding

**Goal:** Scaffold generates .claude/settings.json with PreToolUse hooks (mutable zone enforcement), permissions.allow config, and a CLAUDE.md with graceful shutdown — so the user experience is just `cd experiment-dir && claude`
**Depends on:** Phase 4 (informed by what broke in baseline test)
**Requirements:** HOOK-01, HOOK-02, HOOK-03, HOOK-04, HOOK-05, HOOK-06
**Plans:** 2/2 plans complete

Plans:
- [x] 05-01-PLAN.md — .claude/settings.json + guard-frozen.sh hook generation in scaffold.py
- [x] 05-02-PLAN.md — CLAUDE.md graceful shutdown section

### Phase 6: Structured Output and Metrics Parsing

**Goal:** Add a json_output line to train.py's structured output for agent ergonomics, create parse_run_result.py to automate extraction from claude -p JSON output for Phase 7, and add an optional JSON parser to runner.py -- all additive, no replacement of working grep-based parsing
**Depends on:** Phase 5
**Requirements:** STRUCT-01, STRUCT-02, STRUCT-03
**Plans:** 2/2 plans complete

Plans:
- [x] 06-01-PLAN.md — JSON output line in train_template.py + optional runner.py JSON parser
- [x] 06-02-PLAN.md — parse_run_result.py helper script for Phase 7 test harness

### Phase 7: E2E Validation Test

**Goal:** Re-run the full autonomous loop after all Phase 5-6 changes, proving hooks enforce frozen files, keep/discard cycle works, metrics parse correctly, and the system runs unattended end-to-end
**Depends on:** Phase 6
**Requirements:** VAL-01, VAL-02, VAL-03, VAL-04, VAL-05, VAL-06, VAL-07
**Plans:** 3/3 plans complete

Plans:
- [x] 07-01-PLAN.md — Generate noisy dataset, run validation test, document findings
- [ ] 07-02-PLAN.md — Fix scaffold.py permissions for headless mode, add VAL-xx to REQUIREMENTS.md (gap closure)
- [ ] 07-03-PLAN.md — Re-run validation test after fix, re-populate FINDINGS.md (gap closure)

### Phase 8: Permissions Simplification

**Goal:** Broaden settings.json allow rules to match --allowedTools patterns, add permissions.deny for prepare.py as defense-in-depth, document the headless permissions limitation
**Requirements**: PERM-01, PERM-02, PERM-03
**Depends on:** Phase 7
**Plans:** 1/1 plans complete

Plans:
- [ ] 08-01-PLAN.md — Broaden allow, add deny, document headless limitation

### Phase 9: Resume Capability

**Goal:** Add checkpoint persistence (checkpoint.json) so `claude -p` sessions can resume from where the last session left off — recording best commit, best score, loop phase, iteration count, and strategy state — with a --resume CLI flag and CLAUDE.md Resume Protocol section
**Requirements**: RES-01, RES-02, RES-03, RES-04, RES-05
**Depends on:** Phase 8
**Success Criteria** (what must be TRUE):
  1. checkpoint.py module saves LoopState + metadata to checkpoint.json with atomic write-then-rename
  2. checkpoint.json round-trips LoopState without data loss (all fields including lists and None values preserved)
  3. Scaffolded .gitignore includes checkpoint.json and checkpoint.json.tmp
  4. CLI accepts --resume flag without error
  5. CLAUDE.md template includes Session Resume Check section that instructs the agent to check for checkpoint.json on startup, restore state, and update checkpoint after every keep/revert
**Plans:** 2/2 plans complete

Plans:
- [ ] 09-01-PLAN.md — Checkpoint persistence module and scaffold gitignore update
- [ ] 09-02-PLAN.md — CLI --resume flag and CLAUDE.md Resume Protocol section

### Phase 10: Multi-Agent Swarm

**Goal:** Spawn N parallel `claude -p` agents exploring different algorithm families via git worktrees, with file-locked scoreboard for global best tracking, family-based partitioning during draft phase, TTL claim files during iteration phase, and a SwarmManager orchestrator — accessed via `--agents N` CLI flag
**Requirements**: TBD
**Depends on:** Phase 9
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 10 to break down)
