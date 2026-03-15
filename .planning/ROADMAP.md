# Roadmap: AutoML

## Milestones

- ✅ **v1.0 AutoML MVP + Swarm** — Phases 1-10 (shipped 2026-03-14)
- 📋 **v2.0 Results-Driven Forecasting** — Phases 11-14 (planned)

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

### 📋 v2.0 Results-Driven Forecasting (Planned)

**Milestone Goal:** Refactor the autonomous loop so the agent engineers features, uses Optuna for hyperparameter search, respects time ordering via walk-forward validation, and produces revenue forecasts that beat naive baselines on synthetic quarterly data.

- [x] **Phase 11: Forecasting Infrastructure** - New `forecast.py` frozen module with walk-forward validation, forecasting metrics, and naive baselines; simplified `prepare.py` with date-column support (completed 2026-03-14)
- [x] **Phase 12: Forecast Template and Mutable Zone 2** - `train_template_forecast.py` demonstrating correct lag features + Optuna pattern; updated `CLAUDE.md` and `program.md` templates with v2 agent protocol; dual-baseline enforcement gate (completed 2026-03-14)
- [x] **Phase 13: Scaffold and CLI Updates** - `--date-column` CLI flag, scaffold wiring to copy `forecast.py`, compute baselines, render updated templates, expand deny list and guard hook (completed 2026-03-14)
- [x] **Phase 14: E2E Validation** - Full autonomous loop on synthetic 40-quarter dataset; confirm agent beats seasonal naive and completes 5+ keep/revert cycles within 50 turns (completed 2026-03-15)

## Phase Details

### Phase 11: Forecasting Infrastructure
**Goal**: Leakage-free temporal evaluation infrastructure exists and is tested before any agent runs
**Depends on**: Phase 10 (v1.0 complete)
**Requirements**: TVAL-01, TVAL-02, TVAL-03, FMET-01, FMET-02, FMET-03, BASE-01, BASE-02, BASE-03a
**Success Criteria** (what must be TRUE):
  1. `forecast.walk_forward_evaluate(model_fn, X, y, metric, n_splits)` returns fold metrics without shuffling data — verified by unit test that asserts all test-fold indices are strictly after all train-fold indices
  2. `forecast.compute_metric()` returns MAPE, MAE, RMSE, and directional accuracy on dollar-scale values, all available via METRIC_MAP
  3. `forecast.get_forecasting_baselines()` returns naive and seasonal-naive MAPE scores computed on the same walk-forward splits the agent will use
  4. `prepare.load_data(csv_path, target_col, date_col)` returns a DataFrame with a datetime index sorted in ascending order; `prepare.temporal_split()` returns time-ordered train/holdout without shuffling
  5. Walk-forward folds of fewer than 3 raise a warning; training windows below 20 rows log a warning rather than silently proceeding
  6. `guard-frozen.sh` FROZEN_FILES includes `forecast.py` immediately after module creation
**Plans:** 2/2 plans complete

Plans:
- [ ] 11-01-PLAN.md — forecast.py: walk-forward evaluation, metrics, baselines, guard hook update, tests
- [ ] 11-02-PLAN.md — prepare.py refactor: date_col support, temporal_split, tests

### Phase 12: Forecast Template and Mutable Zone 2
**Goal**: Agent has a correct starting template and explicit protocol for feature engineering and Optuna, so first drafts are structurally leakage-free
**Depends on**: Phase 11
**Requirements**: BASE-03b, FEAT-01, FEAT-02, FEAT-03, FEAT-04, OPTA-01, OPTA-02, OPTA-03
**Success Criteria** (what must be TRUE):
  1. `train_template_forecast.py` contains an `engineer_features(df)` function with lag_1, lag_4, YoY growth rate, and rolling_mean_4q as starter features — all using `.shift(1)` before any rolling operation
  2. The template's Optuna `objective(trial)` function calls `walk_forward_evaluate()` from the frozen `forecast` module — not a custom CV loop — verifiable by inspection of the template file
  3. `CLAUDE.md` template states the 15-feature cap, the shift-first mandate for rolling stats, the `min(50, 2*n_rows)` trial budget cap, and the dual-baseline gate (must beat both naive and seasonal-naive to keep) as explicit numbered rules
  4. `guard-frozen.sh` and `settings.json` deny list include both `prepare.py` and `forecast.py` as protected files, verified by running the guard hook against a simulated write to `forecast.py`
**Plans:** 2/2 plans complete

Plans:
- [ ] 12-01-PLAN.md — train_template_forecast.py with engineer_features + Optuna + walk_forward_evaluate; claude_forecast.md.tmpl agent protocol; structural tests
- [ ] 12-02-PLAN.md — scaffold.py patches: forecast.py deny list, optuna dependency, forecast.py copy into experiment dir

### Phase 13: Scaffold and CLI Updates
**Goal**: `uv run automl data.csv target metric --date-column date` scaffolds a complete forecasting project with baselines pre-computed in `program.md`
**Depends on**: Phase 12
**Requirements**: SCAF-01, SCAF-02, SCAF-03
**Success Criteria** (what must be TRUE):
  1. Running `uv run automl data.csv revenue quarterly --date-column date` produces a scaffolded directory containing `forecast.py`, `train.py` (from forecast template), `CLAUDE.md`, and `program.md` — no manual file copying required
  2. The generated `program.md` includes the dataset's time range, inferred frequency, and naive + seasonal-naive MAPE scores computed at scaffold time
  3. Running the same command without `--date-column` scaffolds the v1.0 template unchanged — forecasting mode is strictly opt-in
**Plans:** 1/1 plans complete

Plans:
- [ ] 13-01-PLAN.md — --date-column CLI flag, scaffold_experiment forecasting branch, forecast program.md with baselines, tests

### Phase 14: E2E Validation
**Goal**: The full v2.0 loop runs autonomously on synthetic quarterly data and produces a forecast that beats seasonal naive
**Depends on**: Phase 13
**Requirements**: EVAL-01, EVAL-02
**Success Criteria** (what must be TRUE):
  1. Scaffolding a 40-quarter synthetic revenue dataset with `--date-column` completes without errors and `program.md` shows non-zero naive baseline MAPE scores
  2. Running the autonomous loop for 50 turns produces at least 5 keep/revert cycles with at least one "keep" decision (model beats both naive baselines)
  3. The best model's holdout MAPE is lower than seasonal-naive holdout MAPE on the synthetic dataset
  4. FINDINGS.md documents baseline scores, best-model MAPE, iterations to first beat seasonal naive, observed Optuna trial counts, and wall-clock time per experiment
**Plans:** 1/1 plans complete

Plans:
- [ ] 14-01-PLAN.md — Generate synthetic dataset, write validation harness script, run E2E loop, populate FINDINGS.md

## Progress

**Execution Order:**
Phases execute in numeric order: 11 → 12 → 13 → 14

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
| 11. Forecasting Infrastructure | 2/2 | Complete    | 2026-03-14 | - |
| 12. Forecast Template + Mutable Zone 2 | 2/2 | Complete    | 2026-03-14 | - |
| 13. Scaffold and CLI Updates | 1/1 | Complete    | 2026-03-14 | - |
| 14. E2E Validation | 1/1 | Complete    | 2026-03-15 | - |
