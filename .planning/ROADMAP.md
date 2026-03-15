# Roadmap: AutoML

## Milestones

- ✅ **v1.0 AutoML MVP + Swarm** — Phases 1-10 (shipped 2026-03-14)
- ✅ **v2.0 Results-Driven Forecasting** — Phases 11-14 (shipped 2026-03-15)
- 🚧 **v3.0 Intelligent Iteration** — Phases 15-18 (in progress)

## Phases

<details>
<summary>✅ v1.0 AutoML MVP + Swarm (Phases 1-10) — SHIPPED 2026-03-14</summary>

- [x] Phase 1: Foundation (3/3 plans) — completed 2026-03-10
- [x] Phase 2: Core Loop (3/3 plans) — completed 2026-03-10
- [x] Phase 3: CLI and Integration (2/2 plans) — completed 2026-03-10
- [x] Phase 4: E2E Baseline Test (1/1 plan) — completed 2026-03-11
- [x] Phase 5: Hooks and Enhanced Scaffolding (2/2 plans) — completed 2026-03-12
- [x] Phase 6: Structured Output and Metrics Parsing (2/2 plans) — completed 2026-03-13
- [x] Phase 7: E2E Validation Test (3/3 plans) — completed 2026-03-13
- [x] Phase 8: Permissions Simplification (1/1 plan) — completed 2026-03-14
- [x] Phase 9: Resume Capability (2/2 plans) — completed 2026-03-14
- [x] Phase 10: Multi-Agent Swarm (3/3 plans) — completed 2026-03-14

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v2.0 Results-Driven Forecasting (Phases 11-14) — SHIPPED 2026-03-15</summary>

- [x] Phase 11: Forecasting Infrastructure (2/2 plans) — completed 2026-03-14
- [x] Phase 12: Forecast Template and Mutable Zone 2 (2/2 plans) — completed 2026-03-14
- [x] Phase 13: Scaffold and CLI Updates (1/1 plan) — completed 2026-03-14
- [x] Phase 14: E2E Validation (1/1 plan) — completed 2026-03-15

Full details: `.planning/milestones/v2.0-ROADMAP.md`

</details>

### 🚧 v3.0 Intelligent Iteration (In Progress)

**Milestone Goal:** Make the agent smarter per iteration — learning from past experiments, diagnosing model weaknesses, and strategically exploring solution space instead of improvising.

- [x] **Phase 15: Diagnosis and Journal Infrastructure** - diagnose() function in forecast.py, experiments.md journal, scaffold pre-population (completed 2026-03-15)
- [ ] **Phase 16: Template and Protocol Updates** - All CLAUDE.md protocol rules: journal read/write, diagnostic recording, diff-aware iteration, hypothesis commits
- [ ] **Phase 17: Branch-on-Stagnation** - Best-commit tracking, stagnation detection, exploration branch mechanics
- [ ] **Phase 18: E2E Validation** - Observed journal usage and branch-on-stagnation triggering in live runs

## Phase Details

### Phase 15: Diagnosis and Journal Infrastructure
**Goal**: The agent has structured knowledge capture and error diagnosis tools available — a diagnose() function exposing where the model fails, and an experiments.md journal seeded with context at scaffold time
**Depends on**: Phase 14 (v2.0 complete)
**Requirements**: DIAG-01, KNOW-01, KNOW-03
**Success Criteria** (what must be TRUE):
  1. `forecast.py diagnose(y_true, y_pred, dates)` returns worst periods, bias direction/magnitude, error-vs-growth correlation, and seasonal error pattern
  2. `experiments.md` exists in every newly scaffolded experiment directory with dataset summary and baseline scores pre-populated
  3. `experiments.md` contains the four required sections: What Works, What Doesn't, Hypotheses Queue, Error Patterns
**Plans**: 2 plans

Plans:
- [x] 15-01-PLAN.md — diagnose() error analysis function in forecast.py (TDD)
- [x] 15-02-PLAN.md — experiments.md journal template and scaffold integration

### Phase 16: Template and Protocol Updates
**Goal**: Both CLAUDE.md templates (classification and forecasting) carry the full v3.0 protocol — agents read the journal before each iteration, update it after, record diagnostic output, review their own diffs, and write hypothesis commit messages
**Depends on**: Phase 15
**Requirements**: KNOW-02, DIAG-02, DIAG-03, PROT-01, PROT-02, PROT-03
**Success Criteria** (what must be TRUE):
  1. `train_template_forecast.py` calls `diagnose()` after each experiment and its output appears in `run.log` as structured text
  2. Both `claude.md.tmpl` and `claude_forecast.md.tmpl` instruct the agent to read `experiments.md` before each iteration and update it after results
  3. Both templates instruct the agent to run `git diff HEAD~1 -- train.py` and `git log --oneline -5` before each iteration
  4. Both templates instruct the agent to record diagnostic error patterns in `experiments.md`
  5. Both templates instruct the agent to write a `## Hypothesis` section in each commit message
**Plans**: 2 plans

Plans:
- [ ] 16-01-PLAN.md — diagnose() call in train_template_forecast.py + DIAG-03 template rule
- [ ] 16-02-PLAN.md — CLAUDE.md template updates (KNOW-02, PROT-01, PROT-02, PROT-03)

### Phase 17: Branch-on-Stagnation
**Goal**: The agent tracks the best result it has ever achieved and, when stuck in a losing streak, branches back to that best commit and tries a different model family instead of continuing to iterate from a degraded state
**Depends on**: Phase 15 (experiments.md provides the journal where best commit is tracked)
**Requirements**: EXPL-01, EXPL-02, EXPL-03
**Success Criteria** (what must be TRUE):
  1. `experiments.md` contains a best-ever commit hash and score that is updated on each "keep" decision
  2. Both CLAUDE.md templates define stagnation as 3+ consecutive reverts and instruct the agent to branch from best-ever commit when stagnation is detected
  3. Agent can execute `git checkout -b explore-{family} {best_commit}` to create an exploration branch, with its results recorded in the same `results.tsv`
**Plans**: TBD

Plans:
- [ ] 17-01: Best-commit tracking in experiments.md + stagnation + exploration branch protocol in templates

### Phase 18: E2E Validation
**Goal**: Live runs on synthetic data demonstrate both v3.0 capabilities — the agent visibly using the journal between iterations, and the agent triggering branch-on-stagnation after a losing streak
**Depends on**: Phases 15, 16, 17 (all v3.0 infrastructure complete)
**Requirements**: EVAL-03, EVAL-04
**Success Criteria** (what must be TRUE):
  1. An observed run shows the agent reading `experiments.md` before at least one iteration and updating it with findings after results
  2. An observed run shows the agent invoking `git checkout -b explore-{family} {best_commit}` after 3+ consecutive reverts
  3. Results from the exploration branch appear in `results.tsv` alongside results from the main branch
**Plans**: TBD

Plans:
- [ ] 18-01: E2E validation run and VALIDATION.md documentation

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | Complete | 2026-03-10 |
| 2. Core Loop | v1.0 | 3/3 | Complete | 2026-03-10 |
| 3. CLI and Integration | v1.0 | 2/2 | Complete | 2026-03-10 |
| 4. E2E Baseline Test | v1.0 | 1/1 | Complete | 2026-03-11 |
| 5. Hooks + Scaffolding | v1.0 | 2/2 | Complete | 2026-03-12 |
| 6. Structured Output | v1.0 | 2/2 | Complete | 2026-03-13 |
| 7. E2E Validation Test | v1.0 | 3/3 | Complete | 2026-03-13 |
| 8. Permissions Simplification | v1.0 | 1/1 | Complete | 2026-03-14 |
| 9. Resume Capability | v1.0 | 2/2 | Complete | 2026-03-14 |
| 10. Multi-Agent Swarm | v1.0 | 3/3 | Complete | 2026-03-14 |
| 11. Forecasting Infrastructure | v2.0 | 2/2 | Complete | 2026-03-14 |
| 12. Forecast Template + Zone 2 | v2.0 | 2/2 | Complete | 2026-03-14 |
| 13. Scaffold and CLI Updates | v2.0 | 1/1 | Complete | 2026-03-14 |
| 14. E2E Validation | v2.0 | 1/1 | Complete | 2026-03-15 |
| 15. Diagnosis and Journal Infrastructure | v3.0 | 2/2 | Complete | 2026-03-15 |
| 16. Template and Protocol Updates | 1/2 | In Progress|  | - |
| 17. Branch-on-Stagnation | v3.0 | 0/1 | Not started | - |
| 18. E2E Validation | v3.0 | 0/1 | Not started | - |
