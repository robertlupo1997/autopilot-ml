# Requirements: AutoML

**Defined:** 2026-03-14
**Core Value:** Give Claude Code a dataset and a metric, and it autonomously discovers the best-performing traditional ML pipeline — running experiments, keeping improvements, reverting failures, and logging everything — without human intervention.

## v2.0 Requirements

### Temporal Validation

- [ ] **TVAL-01**: `forecast.py` provides `walk_forward_evaluate(model_fn, X, y, n_splits)` using expanding window with configurable gap
- [ ] **TVAL-02**: Evaluation always runs in original dollar scale (inverse-transform before metric calculation)
- [ ] **TVAL-03**: Minimum 3 walk-forward folds enforced; warning when training window < 20 rows

### Forecasting Metrics

- [ ] **FMET-01**: MAPE is the primary metric for revenue forecasting; added to `METRIC_MAP`
- [ ] **FMET-02**: MAE and RMSE available as secondary metrics
- [ ] **FMET-03**: Directional accuracy (predicted growth vs actual growth direction) reported alongside primary metric

### Baselines

- [ ] **BASE-01**: Naive forecast (repeat last known value) computed as mandatory floor
- [ ] **BASE-02**: Seasonal naive (same quarter last year) computed as mandatory floor
- [ ] **BASE-03**: Agent must beat both baselines to "keep" an experiment; failing to beat naive = auto-revert

### Feature Engineering

- [ ] **FEAT-01**: `train.py` template includes starter feature engineering (lag_1, lag_4, YoY growth rate, rolling_mean_4q)
- [ ] **FEAT-02**: Agent can add/modify feature engineering code in `train.py` (mutable zone 2 — no separate features.py)
- [ ] **FEAT-03**: Feature count capped at 15 in CLAUDE.md guidance (small-N overfitting guard)
- [ ] **FEAT-04**: Guard hook updated to protect both `prepare.py` and `forecast.py`

### Optuna Integration

- [ ] **OPTA-01**: `train.py` template demonstrates optuna `create_study()` with `trial.suggest_*` for hyperparameters
- [ ] **OPTA-02**: Trial budget capped at `min(50, 2 * n_rows)` in CLAUDE.md guidance
- [ ] **OPTA-03**: Optuna objective function calls frozen `walk_forward_evaluate()` — agent cannot write own validation loop

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
| TVAL-01 | - | Pending |
| TVAL-02 | - | Pending |
| TVAL-03 | - | Pending |
| FMET-01 | - | Pending |
| FMET-02 | - | Pending |
| FMET-03 | - | Pending |
| BASE-01 | - | Pending |
| BASE-02 | - | Pending |
| BASE-03 | - | Pending |
| FEAT-01 | - | Pending |
| FEAT-02 | - | Pending |
| FEAT-03 | - | Pending |
| FEAT-04 | - | Pending |
| OPTA-01 | - | Pending |
| OPTA-02 | - | Pending |
| OPTA-03 | - | Pending |
| SCAF-01 | - | Pending |
| SCAF-02 | - | Pending |
| SCAF-03 | - | Pending |
| EVAL-01 | - | Pending |
| EVAL-02 | - | Pending |

**Coverage:**
- v2.0 requirements: 21 total
- Mapped to phases: 0
- Unmapped: 21

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-14 after v2.0 milestone definition*
