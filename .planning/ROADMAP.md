# Roadmap: AutoML

## Overview

AutoML delivers an autonomous ML experiment framework in three phases. Phase 1 builds the frozen data pipeline, mutable modeling template, git state management, and experiment logging -- everything needed to run and track a single experiment. Phase 2 wires the autonomous experiment loop with keep/revert logic, domain context injection, multi-draft initialization, and resilience features (crash recovery, stagnation detection). Phase 3 wraps the framework in a CLI that scaffolds ready-to-run experiment projects from any CSV. After v1 ships, Phase 4 expands the agent's mutable zones to include feature engineering and tree search.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Frozen pipeline, mutable modeling template, git operations, and experiment logging
- [ ] **Phase 2: Core Loop** - Autonomous experiment loop with multi-draft start, domain context, and resilience
- [ ] **Phase 3: CLI and Integration** - Project scaffolding CLI and end-to-end validation

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
- [ ] 02-01-PLAN.md — Loop helpers (keep/revert, stagnation, crash tracking) and git revert fix
- [ ] 02-02-PLAN.md — Multi-draft initialization system (algorithm families, generation, selection)
- [ ] 02-03-PLAN.md — Context templates (program.md and CLAUDE.md loop protocol)

### Phase 3: CLI and Integration
**Goal**: A user can go from CSV file to running autonomous experiment loop with a single CLI command
**Depends on**: Phase 2
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. User runs a CLI command with a CSV path, target column, and metric -- and gets a fully scaffolded project (prepare.py, train.py, program.md, CLAUDE.md, .gitignore, pyproject.toml)
  2. The scaffolded project is immediately runnable with `uv run train.py` and produces valid metric output
  3. End-to-end test: CLI scaffold, then autonomous loop runs on a real dataset and improves beyond the baseline
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete | 2026-03-10 |
| 2. Core Loop | 2/3 | In Progress|  |
| 3. CLI and Integration | 0/1 | Not started | - |
