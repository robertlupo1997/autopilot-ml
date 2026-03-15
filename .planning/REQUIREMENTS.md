# Requirements: AutoML

**Defined:** 2026-03-15
**Core Value:** Give Claude Code a dataset and a metric, and it autonomously discovers the best-performing traditional ML pipeline — running experiments, keeping improvements, reverting failures, and logging everything — without human intervention.

## v3.0 Requirements

### Knowledge Accumulation

- [ ] **KNOW-01**: Agent maintains an `experiments.md` journal in the experiment directory with sections: What Works, What Doesn't, Hypotheses Queue, Error Patterns
- [ ] **KNOW-02**: CLAUDE.md template instructs the agent to read `experiments.md` before each iteration and update it after results
- [ ] **KNOW-03**: Scaffold creates a starter `experiments.md` with dataset summary and baseline scores pre-populated

### Error Diagnosis

- [ ] **DIAG-01**: `forecast.py` exports a `diagnose(y_true, y_pred, dates)` function returning worst periods, bias direction/magnitude, error-vs-growth correlation, and seasonal error pattern
- [ ] **DIAG-02**: `train_template_forecast.py` calls `diagnose()` after each experiment and prints results to `run.log` as structured output
- [ ] **DIAG-03**: CLAUDE.md template instructs the agent to read diagnostic output and record error patterns in `experiments.md`

### Strategic Exploration

- [ ] **EXPL-01**: Agent tracks best-ever commit hash and MAPE in `experiments.md` (updated on each "keep")
- [ ] **EXPL-02**: CLAUDE.md template defines stagnation as 3+ consecutive reverts and instructs the agent to branch from best-ever commit and try a different model family
- [ ] **EXPL-03**: Agent uses `git checkout -b explore-{family} {best_commit}` to create exploration branches, with results tracked in the same `results.tsv`

### Iteration Protocol

- [ ] **PROT-01**: CLAUDE.md template instructs agent to run `git diff HEAD~1 -- train.py` and `git log --oneline -5` before each iteration to review recent changes
- [ ] **PROT-02**: Agent writes a `## Hypothesis` section in each commit message explaining what it expects to improve and why
- [ ] **PROT-03**: Both `claude.md.tmpl` (v1 classification) and `claude_forecast.md.tmpl` (v2 forecasting) templates updated with all v3.0 protocol rules

### Validation

- [ ] **EVAL-03**: E2E test on synthetic data demonstrates the agent using the experiment journal (reads before iteration, updates after)
- [ ] **EVAL-04**: E2E test demonstrates branch-on-stagnation triggering (agent branches after 3+ reverts and tries a different approach)

## v4.0 Requirements

### Full Pipeline

- **FULL-01**: Agent owns entire pipeline from raw CSV to predictions (mutable zone 3)
- **FULL-02**: Agent can modify data preprocessing, feature engineering, and modeling
- **FULL-03**: Hidden holdout prevents leakage even with full pipeline control

### Advanced Search

- **TREE-01**: Full tree search with UCB-like exploration/exploitation balance
- **TREE-02**: Solutions organized in persistent tree structure with backtracking

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full MCTS / UCB selection | Branch-on-stagnation captures 80% of value at 10% complexity |
| LLM-as-judge for novelty | Real metrics are authoritative |
| Multi-agent research/dev split | Single agent + CLAUDE.md protocol is simpler and proven |
| Mutable zone 3 (full pipeline) | Prove smart iteration before expanding agent scope |
| MLE-bench evaluation | Requires Docker harness, separate effort |
| Deep learning support | Traditional ML only |
| Multi-company models | Single-company forecasting focus |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| KNOW-01 | — | Pending |
| KNOW-02 | — | Pending |
| KNOW-03 | — | Pending |
| DIAG-01 | — | Pending |
| DIAG-02 | — | Pending |
| DIAG-03 | — | Pending |
| EXPL-01 | — | Pending |
| EXPL-02 | — | Pending |
| EXPL-03 | — | Pending |
| PROT-01 | — | Pending |
| PROT-02 | — | Pending |
| PROT-03 | — | Pending |
| EVAL-03 | — | Pending |
| EVAL-04 | — | Pending |

**Coverage:**
- v3.0 requirements: 14 total
- Mapped to phases: 0
- Unmapped: 14

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 after initial definition*
