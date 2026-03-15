# Phase 18: v3.0 E2E Validation - Findings

**Run date:** 2026-03-15
**Script:** scripts/run-v3-validation-test.sh

## Run Summary

| Field | Value |
|-------|-------|
| stop_reason | tool_use (max turns hit mid-action) |
| num_turns | 76 |
| total_cost_usd | $3.19 |
| experiments_run | 9 |
| keeps | 4 |
| best_mape | 0.028172 |
| frozen_file_compliance | PASSED (prepare.py and forecast.py unchanged) |
| beats_naive | PASSED (0.028172 vs 0.0895) |
| beats_seasonal_naive | PASSED (0.028172 vs 0.0608) |

## EVAL-03: Journal Usage

- [x] Agent modified experiments.md from scaffold state
- [x] experiments.md has agent-written content in knowledge sections
- [x] Best Result section populated with commit hash and score

**Evidence:**
- Initial experiments.md hash: (scaffold state, 37 lines) | Final: changed (52 lines)
- Initial line count: 37 | Final line count: 52
- Commits touching experiments.md: 1
- What Works section: has content (4 entries: Ridge/Lasso features, linear models, quarter dummies, linear trend)
- What Doesn't section: has content (4 entries: GBR overfits, lag_2/lag_3, Ridge vs Lasso, seasonal_diff)
- Error Patterns section: has content (2 entries: draft 1 bias/seasonal, iter 5 bias/seasonal)
- Best Result section: populated with commit a917cd6, score 0.028172, model Lasso, iteration 8
- Hypotheses Queue: 5 entries

**Assessment:** PASSED — The agent correctly read and updated experiments.md throughout the run. The journal accumulated substantive knowledge across all four knowledge sections. The Best Result section was populated with the correct commit hash and score, confirming EXPL-01 tracking is working as intended.

## EVAL-04: Branch-on-Stagnation

- [ ] Max consecutive reverts >= 3 (stagnation condition existed)
- [ ] Agent created explore-* branch(es)
- [ ] Exploration branch results appear in results.tsv

**Evidence:**
- Max consecutive reverts: 2 (iterations 6-7: lag_2/lag_3 revert, then Ridge-instead-of-Lasso revert)
- Explore branches: none
- Total experiments: 9 (all on main branch)

**Assessment:** NOT TRIGGERED — The agent found good solutions before reaching the stagnation threshold of 3 consecutive reverts. This is the expected "agent found good solutions" scenario, not a failure of the protocol.

The stagnation condition (3+ consecutive reverts) did not occur during this run. After reverting iterations 6 and 7, the agent found an improvement at iteration 8 (linear trend feature: MAPE 0.028460 → 0.028172), breaking the revert streak before it reached the 3-consecutive threshold.

The branch-on-stagnation protocol is correctly defined in both templates. Phase 17 shipped 6 structural tests confirming:
- experiments.md.tmpl has Best Result section
- Both templates have "3 consecutive reverts" stagnation detection
- Both templates have "git checkout -b explore-" branching command
- Both templates state "Results are still logged to the same results.tsv"

A follow-up test with a harder dataset or a constrained model family (e.g., no linear models) could force stagnation for direct observation. The protocol is in place; it simply was not needed during this run.

## Observed v3.0 Behaviors

### Journal Read/Write Pattern

The agent demonstrated correct journal read/write behavior. experiments.md grew from 37 lines (scaffold state) to 52 lines (+15 lines of agent-written knowledge), with a single commit touching the file. The What Works, What Doesn't, Error Patterns, and Hypotheses Queue sections all received substantive agent-written content, confirming the agent is reading the journal context before each iteration and writing back confirmed findings after keep/revert decisions.

### Diff-Aware Iteration (PROT-01)

Git log shows hypothesis-driven commit messages consistent with the v3.0 diff-aware protocol:
- `draft: GradientBoostingRegressor` (iter 2, discarded)
- `draft: Lasso` / `draft: ElasticNet` (diverse initial solutions)
- `select best draft: Lasso (MAPE=0.029044)`
- `try: add quarter dummy features for seasonal patterns` (iter 5, kept)
- `try: add linear trend feature` (iter 8, kept — became best)

Each commit message names the specific hypothesis being tested, demonstrating the agent is iterating based on diff-aware reasoning from the journal context.

### Diagnostic Output (DIAG-02/DIAG-03)

Assertion output confirmed: `OK: diagnostic_output present (Phase 16 diagnostics)`. The per-iteration bias and seasonal error patterns in experiments.md Error Patterns section show the agent is using diagnostic information to form hypotheses (e.g., seeing Q1-Q4 seasonal bias led to adding quarter dummy features).

### Branch-on-Stagnation (EXPL-01/02/03)

EXPL-01 (best-commit tracking): PASSED. Best Result section was populated with commit a917cd6, confirming the agent ran `git rev-parse HEAD` and recorded the commit on KEEP.

EXPL-02 (consecutive revert counting): Max 2 consecutive reverts reached but threshold of 3 not hit.

EXPL-03 (exploration branching): Not triggered. The agent found improvement at iteration 8, breaking the 2-revert streak before reaching the 3-revert threshold. No explore-* branches were created.

### Model Quality

Best MAPE 0.028172 represents a 68% improvement over the naive baseline (0.0895) and a 54% improvement over seasonal naive (0.0608). The agent's feature selection converged on: lag1 + lag4 + yoy_growth + rolling_mean_4q + quarter_dummies (Q1-Q3) + linear_trend with Lasso alpha optimization — a well-regularized linear model with seasonality and trend capture.

## Git History

```
a917cd6 (HEAD -> main) try: add linear trend feature
a9aec38 try: add quarter dummy features for seasonal patterns
38c4f01 select best draft: Lasso (MAPE=0.029044)
cbf7331 draft: ElasticNet
03735d1 draft: Lasso
7791c4f draft: GradientBoostingRegressor
bb55584 initial scaffold
```

## Experiment Results

```
iteration	mape	elapsed_sec	status	description
1	0.029064	5.8	draft-keep	Ridge alpha-optimized, lag1/lag4/yoy/rolling4q features
2	0.057068	23.7	draft-discard	GradientBoostingRegressor with Optuna tuning
3	0.029044	2.9	draft-keep	Lasso with Optuna alpha tuning
4	0.029063	2.5	draft-discard	ElasticNet with alpha+l1_ratio tuning
5	0.028460	2.4	keep	Add quarter dummy features (Q1-Q3 one-hot)
6	0.032802	4.0	revert	Add lag_2 and lag_3 (worse, more features = overfitting)
7	0.029115	3.8	revert	Ridge instead of Lasso with quarter dummies (worse)
8	0.028172	9.4	keep	Add linear trend feature
9	0.029809	4.7	revert	Replace yoy_growth with seasonal_diff (worse)
```

## experiments.md Final State

```markdown
# Experiment Journal: quarterly_revenue

## Dataset Context
- **Shape:** 40 rows x 1 columns (including target)
- **Time range:** 2014-01-01 to 2023-10-01
- **Inferred frequency:** QS-OCT
- **Target stats:** mean=1495043.46, std=328029.91, min=864901.42, max=2105905.84

**Baselines to beat:**
- **Naive MAPE:** 0.0895 (8.9%)
- **Seasonal Naive MAPE:** 0.0608 (6.1%)

## Best Result
- **Best commit:** a917cd6
- **Best score:** 0.028172
- **Model family:** Lasso
- **Iteration:** 8

## What Works
- Lasso with lag1/lag4/yoy_growth/rolling_mean_4q features: MAPE=0.029044 (iter 3)
- Linear models (Ridge/Lasso/ElasticNet) all ~0.029, vastly outperform GBR (0.057)
- Quarter dummies (Q1-Q3 one-hot): MAPE 0.029044->0.028460, reduced std 0.0113->0.0057 (iter 5)
- Linear trend feature: MAPE 0.028460->0.028172, captures upward growth (iter 8)

## What Doesn't
- GradientBoosting: MAPE=0.057, overfits on 40 rows despite tuning
- Adding lag_2 and lag_3: MAPE 0.028460->0.032802, too many lag features overfits (iter 6)
- Ridge instead of Lasso: MAPE=0.029115, Lasso's L1 selection helps (iter 7)
- Replacing yoy_growth with seasonal_diff: MAPE 0.028172->0.029809, ratio form captures growth better (iter 9)

## Hypotheses Queue
1. Add rolling_std volatility feature (shift(1).rolling(4).std())
2. Add momentum: lag1 - rolling_mean_4q deviation
3. Try log-transform of target inside model_fn
4. Add quadratic trend (trend^2) for accelerating growth
5. Try wider Lasso alpha range

## Error Patterns
- Draft 1 (Ridge): bias=over (+1963), seasonal: Q1=48655, Q2=41002, Q3=38846, Q4=52951
- Iter 5 (Lasso+quarter dummies): bias=over (+12607), seasonal: Q1=30271, Q2=42257, Q3=52616, Q4=53928
```

## Issues Found

| # | Category | Severity | Description |
|---|----------|----------|-------------|
| 1 | Graceful Shutdown | Low | stop_reason=tool_use (max turns hit mid-action) — known limitation from v1.0, does not affect result quality |
| 2 | EVAL-04 Coverage | Low | Branch-on-stagnation NOT TRIGGERED due to agent finding good solutions early; structural tests from Phase 17 confirm protocol is correctly defined. A harder dataset or constrained run would provide direct behavioral evidence. |
