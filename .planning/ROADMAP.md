# Roadmap: mlforge

## Overview

mlforge is a ground-up rebuild of autopilot-ml into a multi-domain autonomous ML research framework. The roadmap delivers a shared core engine with plugin architecture, validates it end-to-end with the proven tabular domain, then expands to deep learning and LLM fine-tuning. Five phases move from foundation through validated tabular pipeline to full three-domain support with swarm mode.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core Engine + Plugin Infrastructure** - State management, git ops, checkpoint/resume, config system, plugin protocol, and template rendering (completed 2026-03-19)
- [ ] **Phase 2: Tabular Plugin + Experiment Intelligence** - Tabular ML plugin validating the architecture, plus baselines, diagnostics, stagnation, and multi-draft
- [ ] **Phase 3: Scaffold, CLI + Run Engine** - User entry point, experiment loop orchestration, guardrails, and overnight reliability
- [ ] **Phase 4: E2E Validation + UX** - End-to-end tabular validation on real data, user experience modes, artifact export, and run summaries
- [ ] **Phase 5: Domain Plugins + Swarm** - Deep learning plugin, LLM fine-tuning plugin, and multi-agent swarm mode

## Phase Details

### Phase 1: Core Engine + Plugin Infrastructure
**Goal**: The foundational engine exists -- state tracking, git operations, checkpoint/resume, configuration, plugin protocol, and protocol template rendering are all operational
**Depends on**: Nothing (first phase)
**Requirements**: CORE-03, CORE-04, CORE-05, CORE-06, CORE-07, CORE-08, CORE-10
**Success Criteria** (what must be TRUE):
  1. State can be created, persisted to JSON, and restored across simulated context resets with experiment count, best metric, and budget remaining intact
  2. Git operations create a branch per run, commit on keep, reset on revert, and tag best model -- all programmatically via GitPython
  3. A crashed session can be resumed from the last checkpoint and continues from where it left off
  4. A domain plugin conforming to the typing.Protocol interface can register, scaffold files, and render its CLAUDE.md template via Jinja2
  5. Hook engine intercepts tool calls and blocks writes to files marked as frozen in config
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md -- Package skeleton + State + Config + Checkpoint (CORE-04, CORE-06, CORE-05)
- [ ] 01-02-PLAN.md -- Git ops + Experiment journal (CORE-10, CORE-08)
- [ ] 01-03-PLAN.md -- Plugin protocol + Templates + Hook engine (CORE-03, CORE-07)

### Phase 2: Tabular Plugin + Experiment Intelligence
**Goal**: The tabular ML plugin proves the plugin architecture works, and the experiment intelligence features (baselines, diagnostics, stagnation, multi-draft, diff-aware iteration) are operational
**Depends on**: Phase 1
**Requirements**: TABL-01, TABL-02, TABL-03, TABL-04, TABL-05, INTL-01, INTL-02, INTL-03, INTL-04, INTL-05, INTL-06, INTL-08
**Success Criteria** (what must be TRUE):
  1. Tabular plugin handles CSV/Parquet input for classification and regression, generating frozen prepare.py and mutable train.py with scikit-learn/XGBoost/LightGBM support
  2. Baseline establishment runs naive and domain-specific baselines, and the dual-baseline gate rejects experiments that do not beat both
  3. Diagnostics engine reports worst predictions, bias direction, and feature correlations -- telling the agent WHERE the model fails
  4. After 3 consecutive reverts, branch-on-stagnation triggers and creates a new branch from the best-ever commit
  5. Multi-draft start generates 3-5 diverse initial solutions across model families and picks the best before iterating linearly
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD
- [ ] 02-03: TBD

### Phase 3: Scaffold, CLI + Run Engine
**Goal**: Users can install mlforge, run it from the command line, and it orchestrates the full experiment loop with guardrails for unattended overnight execution
**Depends on**: Phase 2
**Requirements**: CORE-01, CORE-02, CORE-09, GUARD-01, GUARD-02, GUARD-03, GUARD-04, GUARD-05, INTL-07
**Success Criteria** (what must be TRUE):
  1. User can pip install mlforge and run `mlforge <dataset> <goal>` to start an autonomous experiment session
  2. The run engine executes fresh-context-per-iteration experiment loops -- spawning `claude -p` sessions that keep improvements and revert failures
  3. Deviation handling auto-recovers from crashes (retry), OOM (reduce batch), and divergence (revert) without human intervention
  4. Resource guardrails enforce cost caps, GPU hour limits, disk usage, and per-experiment timeouts with hard stops
  5. Live terminal output shows current experiment number, best metric, and remaining budget
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD
- [ ] 03-03: TBD

### Phase 4: E2E Validation + UX
**Goal**: The full tabular pipeline is validated end-to-end on real data, and user experience features (simple/expert modes, artifact export, run summaries) are complete
**Depends on**: Phase 3
**Requirements**: UX-01, UX-02, UX-03, UX-04, UX-05, GUARD-06, TABL-03
**Success Criteria** (what must be TRUE):
  1. A complete mlforge run on a real tabular dataset scaffolds, iterates, checkpoints, resumes, and produces a best model that beats both baselines
  2. Simple mode auto-detects task type, selects metrics, and runs with minimal user input (just dataset + goal)
  3. Expert mode accepts custom CLAUDE.md, custom frozen/mutable zones, custom baselines, and plugin API access
  4. Best model artifact is exported with metadata (metric value, config, training history) after session completes
  5. Run retrospective summarizes approaches tried, what worked, what failed, cost breakdown, and recommendations
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Domain Plugins + Swarm
**Goal**: Deep learning and LLM fine-tuning plugins extend mlforge to all three domains, and swarm mode enables parallel agent exploration
**Depends on**: Phase 4
**Requirements**: DL-01, DL-02, DL-03, DL-04, DL-05, FT-01, FT-02, FT-03, FT-04, FT-05, SWARM-01, SWARM-02, SWARM-03, SWARM-04
**Success Criteria** (what must be TRUE):
  1. Deep learning plugin trains PyTorch models for image/text classification with GPU management, LR scheduling, early stopping, and fixed time budgets per run
  2. Fine-tuning plugin runs LoRA/QLoRA fine-tuning of open models with VRAM management, quantization config, and evaluation metrics (perplexity, ROUGE)
  3. Both new plugins generate domain-specific CLAUDE.md protocols and work through the same scaffold/run/iterate pipeline as tabular
  4. Swarm mode spawns parallel agents in git worktrees with file-locked scoreboard coordination and budget inheritance preventing spawn explosion
  5. Verification agent checks metric improvement claims against actual holdout performance
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD
- [ ] 05-03: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Engine + Plugin Infrastructure | 3/3 | Complete   | 2026-03-19 |
| 2. Tabular Plugin + Experiment Intelligence | 0/3 | Not started | - |
| 3. Scaffold, CLI + Run Engine | 0/3 | Not started | - |
| 4. E2E Validation + UX | 0/2 | Not started | - |
| 5. Domain Plugins + Swarm | 0/3 | Not started | - |
