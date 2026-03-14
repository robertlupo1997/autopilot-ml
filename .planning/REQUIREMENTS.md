# Requirements: AutoML

**Defined:** 2026-03-14
**Core Value:** Give Claude Code a dataset and a metric, and it autonomously discovers the best-performing traditional ML pipeline — running experiments, keeping improvements, reverting failures, and logging everything — without human intervention.

## v2.0 Requirements

### Temporal Validation

- [x] **TVAL-01**: `forecast.py` provides `walk_forward_evaluate(model_fn, X, y, n_splits)` using expanding window with configurable gap
- [x] **TVAL-02**: Evaluation always runs in original dollar scale (inverse-transform before metric calculation)
- [x] **TVAL-03**: Minimum 3 walk-forward folds enforced; warning when training window < 20 rows

### Forecasting Metrics

- [x] **FMET-01**: MAPE is the primary metric for revenue forecasting; added to `METRIC_MAP`
- [x] **FMET-02**: MAE and RMSE available as secondary metrics
- [x] **FMET-03**: Directional accuracy (predicted growth vs actual growth direction) reported alongside primary metric

### Baselines

- [x] **BASE-01**: Naive forecast (repeat last known value) computed as mandatory floor
- [x] **BASE-02**: Seasonal naive (same quarter last year) computed as mandatory floor
- [x] **BASE-03a**: Baselines computed on same walk-forward splits as agent evaluation (infrastructure)
- [x] **BASE-03b**: Agent must beat both baselines to "keep" an experiment; failing to beat naive = auto-revert (enforcement gate in CLAUDE.md protocol and/or `loop_helpers.should_keep()`)

### Feature Engineering

- [x] **FEAT-01**: `train.py` template includes starter feature engineering (lag_1, lag_4, YoY growth rate, rolling_mean_4q)
- [x] **FEAT-02**: Agent can add/modify feature engineering code in `train.py` (mutable zone 2 — no separate features.py)
- [x] **FEAT-03**: Feature count capped at 15 in CLAUDE.md guidance (small-N overfitting guard)
- [x] **FEAT-04**: Guard hook updated to protect both `prepare.py` and `forecast.py`

### Optuna Integration

- [x] **OPTA-01**: `train.py` template demonstrates optuna `create_study()` with `trial.suggest_*` for hyperparameters
- [x] **OPTA-02**: Trial budget capped at `min(50, 2 * n_rows)` in CLAUDE.md guidance
- [x] **OPTA-03**: Optuna objective function calls frozen `walk_forward_evaluate()` — agent cannot write own validation loop

### Scaffold & CLI

- [ ] **SCAF-01**: CLI accepts `--date-column` flag to enable forecasting mode
- [ ] **SCAF-02**: Scaffold generates forecasting-specific `train.py`, `CLAUDE.md`, and `program.md` when date column specified
- [ ] **SCAF-03**: `program.md` includes data summary with time range, frequency, trend, and naive baseline scores

### Validation

- [ ] **EVAL-01**: End-to-end test on synthetic quarterly revenue data (40 quarters) produces forecast that beats seasonal naive
- [ ] **EVAL-02**: Agent completes at least 5 keep/revert cycles within 50 turns (efficiency improvement over v1.0's 11 experiments)

## v3.0 Requirements

### Full Pipeline

- **FULL-01**: Agent owns entire pipeline from raw CSV to predictions (mutable zone 3)
- **FULL-02**: Agent can modify data preprocessing, feature engineering, and modeling
- **FULL-03**: Hidden holdout prevents leakage even with full pipeline control

### Advanced Search

- **TREE-01**: Branch-on-best — jump to best-ever git commit when plateau detected (AIDE-inspired)
- **TREE-02**: Solutions organized in tree structure with backtracking

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-company / cross-company models | v2 focuses on single-company forecasting |
| Deep learning / neural networks | Traditional ML only; insufficient data for neural approaches at N=40 |
| Real-time data ingestion | Batch CSV input only |
| Multi-GPU / distributed training | Single machine, CPU-first |
| tsfresh auto-feature generation | 700+ features on 40 rows = guaranteed overfitting |
| Full MCTS tree search | Complexity not justified for v2; branch-on-best deferred to v3 |
| FLAML as optimizer | Conflicts with agent-driven multi-draft architecture |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TVAL-01 | Phase 11 | Complete |
| TVAL-02 | Phase 11 | Complete |
| TVAL-03 | Phase 11 | Complete |
| FMET-01 | Phase 11 | Complete |
| FMET-02 | Phase 11 | Complete |
| FMET-03 | Phase 11 | Complete |
| BASE-01 | Phase 11 | Complete |
| BASE-02 | Phase 11 | Complete |
| BASE-03a | Phase 11 | Complete |
| BASE-03b | Phase 12 | Complete |
| FEAT-01 | Phase 12 | Complete |
| FEAT-02 | Phase 12 | Complete |
| FEAT-03 | Phase 12 | Complete |
| FEAT-04 | Phase 12 | Complete |
| OPTA-01 | Phase 12 | Complete |
| OPTA-02 | Phase 12 | Complete |
| OPTA-03 | Phase 12 | Complete |
| SCAF-01 | Phase 13 | Pending |
| SCAF-02 | Phase 13 | Pending |
| SCAF-03 | Phase 13 | Pending |
| EVAL-01 | Phase 14 | Pending |
| EVAL-02 | Phase 14 | Pending |

**Coverage:**
- v2.0 requirements: 22 total (BASE-03 split into BASE-03a infrastructure + BASE-03b enforcement)
- Mapped to phases: 22
- Unmapped: 0

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-14 — BASE-03 split into BASE-03a (Phase 11) and BASE-03b (Phase 12)*
