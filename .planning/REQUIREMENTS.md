# Requirements: AutoML

**Defined:** 2026-03-09
**Core Value:** Give Claude Code a dataset and a metric, and it autonomously discovers the best-performing traditional ML pipeline — running experiments, keeping improvements, reverting failures, and logging everything — without human intervention.

## v1 Requirements

### Frozen Pipeline

- [x] **PIPE-01**: Framework accepts any CSV file + target column + evaluation metric as input
- [x] **PIPE-02**: Data is automatically split into train/test (time-based if temporal, stratified if classification)
- [x] **PIPE-03**: Evaluation function computes configurable metric (AUC, RMSE, F1, accuracy, MAE) using cross-validation
- [x] **PIPE-04**: Sanity-check baselines are computed before agent loop starts (majority class, mean predictor, random)
- [x] **PIPE-05**: Hidden holdout set is reserved that the agent never sees (final validation)
- [x] **PIPE-06**: Basic data preprocessing handled in frozen layer (missing values, categorical encoding, type inference)
- [x] **PIPE-07**: Data preview/summary generated for agent context (shape, dtypes, distributions, correlations)

### Mutable Modeling

- [x] **MODEL-01**: Agent edits a single train.py file containing model selection, hyperparameters, and ensemble logic
- [x] **MODEL-02**: train.py template provides baseline model (e.g., LogisticRegression or XGBoost with defaults)
- [x] **MODEL-03**: train.py imports frozen evaluation function and data from prepare.py
- [x] **MODEL-04**: train.py prints structured metric output parseable by the agent (metric name, value, direction)
- [x] **MODEL-05**: train.py enforces a configurable time budget per experiment (default ~60s for tabular ML)

### Experiment Loop

- [x] **LOOP-01**: Agent runs train.py, extracts metric from output, decides keep or revert
- [x] **LOOP-02**: All stdout/stderr redirected to run.log to prevent context flooding
- [x] **LOOP-03**: Agent reads metric via grep/regex from run.log (not by reading full output)
- [x] **LOOP-04**: Keep/revert logic: if metric improved → git commit; if equal/worse → git reset
- [x] **LOOP-05**: Agent runs autonomously and indefinitely until manually interrupted ("NEVER STOP")
- [x] **LOOP-06**: Timeout enforcement: experiments exceeding 2x budget are killed and treated as failures
- [x] **LOOP-07**: Crash recovery: if train.py crashes, agent reads traceback, attempts fix, moves on after 3 failed attempts
- [x] **LOOP-08**: Stagnation detection: after N consecutive reverts (default 5), agent is prompted to try a different strategy category

### Git State Management

- [x] **GIT-01**: Each experiment run operates on a dedicated branch (e.g., automl/run-<tag>)
- [x] **GIT-02**: Successful experiments are committed with descriptive messages
- [x] **GIT-03**: Failed/reverted experiments reset to the last good commit
- [x] **GIT-04**: results.tsv is untracked by git (listed in .gitignore)
- [x] **GIT-05**: Git operations use subprocess + CLI (not GitPython)

### Experiment Logging

- [x] **LOG-01**: results.tsv tracks: commit hash, metric value, memory/time, status (keep/discard/crash), description
- [x] **LOG-02**: results.tsv is tab-separated and append-only
- [x] **LOG-03**: Each experiment's full output is captured in run.log (overwritten per experiment)

### Domain Context

- [x] **CTX-01**: program.md file accepts human-written domain expertise (data patterns, feature hints, known issues)
- [x] **CTX-02**: Agent reads program.md at each iteration for strategy guidance
- [x] **CTX-03**: CLAUDE.md provides the meta-orchestrator instructions (experiment loop protocol)

### Multi-Draft Start

- [x] **DRAFT-01**: Before iterating, agent generates 3-5 diverse initial solutions using different algorithm families
- [x] **DRAFT-02**: Each draft is evaluated using the frozen evaluation function
- [x] **DRAFT-03**: Best-performing draft is selected as the starting point for linear iteration
- [x] **DRAFT-04**: Draft results are logged in results.tsv with status "draft-keep" or "draft-discard"

### CLI and Scaffolding

- [x] **CLI-01**: CLI command scaffolds a new experiment project from a CSV file
- [x] **CLI-02**: CLI accepts: data path, target column, metric name, goal description
- [x] **CLI-03**: CLI generates: prepare.py, train.py, program.md, CLAUDE.md, .gitignore, pyproject.toml
- [x] **CLI-04**: Generated project is immediately runnable with `uv run train.py`

### Hooks and Enhanced Scaffolding

- [x] **HOOK-01**: Scaffold generates .claude/settings.json with permissions.allow rules (Bash, Edit(train.py), Write(train.py), Read, Glob, Grep)
- [x] **HOOK-02**: Scaffold generates .claude/hooks/guard-frozen.sh PreToolUse hook that denies writes to prepare.py
- [x] **HOOK-03**: Hook script is executable (chmod 755) and uses jq with Python fallback for JSON parsing
- [x] **HOOK-04**: .gitignore includes .claude/settings.local.json to prevent personal overrides from being committed
- [x] **HOOK-05**: CLAUDE.md includes graceful shutdown section addressing max_turns mid-action interrupt
- [x] **HOOK-06**: Scaffolded project requires no --dangerously-skip-permissions or manual --allowedTools flags

### Validation

- [x] **VAL-01**: Noisy dataset fixture exists (tests/fixtures/noisy.csv -- 300 rows, 10% label noise, binary classification)
- [x] **VAL-02**: Validation test harness script exists (scripts/run-validation-test.sh -- no --allowedTools, uses parse_run_result.py)
- [x] **VAL-03**: Full autonomous loop runs unattended via `claude -p` with 0 permission denials
- [x] **VAL-04**: stop_reason is end_turn or max_turns (not tool_use) from a run where experiments executed
- [x] **VAL-05**: Hook fires on prepare.py write attempt OR agent never attempts (both acceptable outcomes)
- [x] **VAL-06**: json_output line present and parseable in run.log (Phase 6 structured output verified)
- [x] **VAL-07**: Stagnation behavior documented (consecutive reverts counted, strategy shift observed or noted as not triggered)

## v2 Requirements

### Feature Engineering Zone

- **FEAT-01**: Agent can modify a features.py file (feature creation, selection, transformation)
- **FEAT-02**: Leakage detection checks run automatically after each feature engineering change
- **FEAT-03**: features.py receives raw dataframes (not pre-split arrays)

### Tree Search

- **TREE-01**: Solutions organized in a tree structure (like AIDE's journal)
- **TREE-02**: Agent can branch from any good node, not just the current best
- **TREE-03**: Search policy balances exploration (new approaches) vs exploitation (improving best)

### Enhanced Intelligence

- **INTEL-01**: Automated EDA phase generates insights before experiments begin
- **INTEL-02**: Report generation: markdown summary of what was tried, what worked, key findings
- **INTEL-03**: Sub-agent spawning for parallel draft generation
- **INTEL-04**: Simplicity scoring: penalize solutions that add complexity without proportional metric improvement

### Full Pipeline (v3)

- **FULL-01**: Agent owns entire pipeline from raw CSV to predictions
- **FULL-02**: Agent can modify data preprocessing, feature engineering, and modeling
- **FULL-03**: Hidden holdout prevents leakage even with full pipeline control

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web UI / dashboard | Adds complexity without core value; CLI is sufficient |
| MLflow / W&B integration | Git IS the experiment log; external tracking adds network dependency |
| Deep learning / neural networks | Traditional ML only; different hardware requirements |
| Multi-GPU / distributed | Single machine; tabular ML doesn't need distributed compute |
| LLM-as-judge for metrics | Simple regex parsing is sufficient for v1; structured output from train.py |
| GitPython | Memory leaks, opaque errors; subprocess + CLI is simpler and more reliable |
| Real-time experiment monitoring | Review results.tsv and git log after the run |
| MLE-bench integration | Requires Docker harness; future milestone after framework is stable |
| Extensible plugin system | Over-engineering; template modification is sufficient |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PIPE-01 | Phase 1 | Complete |
| PIPE-02 | Phase 1 | Complete |
| PIPE-03 | Phase 1 | Complete |
| PIPE-04 | Phase 1 | Complete |
| PIPE-05 | Phase 1 | Complete |
| PIPE-06 | Phase 1 | Complete |
| PIPE-07 | Phase 1 | Complete |
| MODEL-01 | Phase 1 | Complete |
| MODEL-02 | Phase 1 | Complete |
| MODEL-03 | Phase 1 | Complete |
| MODEL-04 | Phase 1 | Complete |
| MODEL-05 | Phase 1 | Complete |
| GIT-01 | Phase 1 | Complete |
| GIT-02 | Phase 1 | Complete |
| GIT-03 | Phase 1 | Complete |
| GIT-04 | Phase 1 | Complete |
| GIT-05 | Phase 1 | Complete |
| LOG-01 | Phase 1 | Complete |
| LOG-02 | Phase 1 | Complete |
| LOG-03 | Phase 1 | Complete |
| LOOP-01 | Phase 2 | Complete |
| LOOP-02 | Phase 2 | Complete |
| LOOP-03 | Phase 2 | Complete |
| LOOP-04 | Phase 2 | Complete |
| LOOP-05 | Phase 2 | Complete |
| LOOP-06 | Phase 2 | Complete |
| LOOP-07 | Phase 2 | Complete |
| LOOP-08 | Phase 2 | Complete |
| CTX-01 | Phase 2 | Complete |
| CTX-02 | Phase 2 | Complete |
| CTX-03 | Phase 2 | Complete |
| DRAFT-01 | Phase 2 | Complete |
| DRAFT-02 | Phase 2 | Complete |
| DRAFT-03 | Phase 2 | Complete |
| DRAFT-04 | Phase 2 | Complete |
| CLI-01 | Phase 3 | Complete |
| CLI-02 | Phase 3 | Complete |
| CLI-03 | Phase 3 | Complete |
| CLI-04 | Phase 3 | Complete |
| HOOK-01 | Phase 5 | Planned |
| HOOK-02 | Phase 5 | Planned |
| HOOK-03 | Phase 5 | Planned |
| HOOK-04 | Phase 5 | Planned |
| HOOK-05 | Phase 5 | Planned |
| HOOK-06 | Phase 5 | Planned |
| VAL-01 | Phase 7 | Planned |
| VAL-02 | Phase 7 | Planned |
| VAL-03 | Phase 7 | Complete |
| VAL-04 | Phase 7 | Complete |
| VAL-05 | Phase 7 | Complete |
| VAL-06 | Phase 7 | Complete |
| VAL-07 | Phase 7 | Complete |

**Coverage:**
- v1 requirements: 52 total
- Mapped to phases: 52
- Unmapped: 0

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-13 after Phase 7 gap closure*
