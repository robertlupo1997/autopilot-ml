# Project Research Summary

**Project:** AutoML v2.0 — Results-Driven Forecasting
**Domain:** Autonomous ML Framework — Time-Series Feature Engineering, Walk-Forward Validation, Hyperparameter Optimization for Quarterly Revenue Forecasting
**Researched:** 2026-03-14
**Confidence:** HIGH (direct codebase reading + verified official docs for all major libraries)

## Executive Summary

AutoML v2.0 extends the validated v1.0 autonomous experiment loop to support quarterly revenue forecasting on small datasets (20-80 rows). The v1.0 architecture — frozen `prepare.py`, mutable `train.py`, git-based keep/revert, multi-draft — is sound and carries forward unchanged. The key v2.0 challenge is that three things in v1.0 break for time series: random CV leaks future data into training, feature engineering (lags, rolling stats) is too domain-specific to freeze, and forecasting metrics (MAPE, MAE) require custom implementation. The solution is a clean architectural expansion: a new frozen module `forecast.py` owns walk-forward validation and metrics, while `train.py` expands to include feature engineering alongside model selection. The single-mutable-file constraint is preserved, which is critical for clean experiment attribution.

The recommended stack adds exactly two new dependencies: `optuna>=4.0` for Bayesian hyperparameter search and `feature-engine>=1.8` for sklearn-compatible lag/rolling transformers. `sklearn.model_selection.TimeSeriesSplit` is already available in the existing stack. MAPE and MAE are available from sklearn; SMAPE is a 3-line numpy implementation. The stack additions are minimal by design: tsfresh, sktime, prophet, statsmodels for ARIMA, and any neural network approach are explicitly rejected for the 20-80 row regime. The only borderline addition is `statsmodels` (for an exponential smoothing baseline), which the architecture deems acceptable.

The dominant risk for v2.0 is silent temporal leakage — the LLM agent introducing future data into training via rolling statistics computed on the full dataset before splitting, or via scalers fit on the full training set before walk-forward folds. This risk does not produce a stack trace; it produces suspiciously good metrics that lock in as the "best" solution. The mitigation is architectural: the frozen `forecast.py` module owns the walk-forward loop and calls the agent's feature code inside each fold, making it structurally difficult to leak across fold boundaries. All other pitfalls (Optuna overfitting, too-narrow folds, feature dimensionality explosion) are real but secondary to the leakage risk.

---

## Key Findings

### Recommended Stack

The v1.0 stack (scikit-learn, XGBoost, LightGBM, pandas, numpy, uv) carries forward unchanged. v2.0 adds two libraries and zero paradigm shifts.

**Core technologies (new additions only):**
- `optuna>=4.0,<5.0`: Bayesian hyperparameter search — agent writes the `objective(trial)` function; Optuna's TPE sampler explores the space. Pure optimizer with no model selection opinion, which preserves agent agency. FLAML rejected because it takes over algorithm selection, conflicting with multi-draft architecture.
- `feature-engine>=1.8,<2.0`: Sklearn-compatible lag and rolling window transformers (`LagFeatures`, `WindowFeatures`, `ExpandingWindowFeatures`) that fit inside `Pipeline` and handle the fit/transform split correctly. Manual pandas `shift()` works but risks leakage; feature-engine handles it structurally.
- `sklearn.model_selection.TimeSeriesSplit`: Already installed. Expanding-window temporal CV with `gap` parameter to prevent fold overlap. No new dependency.
- Forecasting metrics (MAPE, RMSE, MAE): Available from `sklearn.metrics`. SMAPE implemented as a 3-line numpy function registered as a custom scorer. No new dependency.
- `statsmodels>=0.14`: Added only for the exponential smoothing baseline in `forecast.py`. Lightweight and CPU-only.

**Key version constraints:** optuna `n_startup_trials` defaults to 20 (TPE random phase); for 30-trial budgets, set it to 5-10 so TPE kicks in early. Optuna's `timeout` parameter is critical — use `timeout=TIME_BUDGET * 0.6` to leave room for final model fitting.

**What NOT to add:** tsfresh (700+ features at 20-80 rows = guaranteed overfitting), sktime/darts (paradigm mismatch — tabular ML approach vs. forecasting-native framework), prophet/neuralprophet (neural, CPU-slow, wrong for traditional ML scope), ARIMA/statsmodels for modeling (different API, incompatible with agent's train.py + optuna pattern), ray tune (distributed overhead for a 30-trial search).

See: `.planning/research/STACK.md`

### Expected Features

**Must have (table stakes — v2.0 core, all interdependent):**
- Walk-forward temporal validation in `forecast.py` — expanding-window split, last 4 quarters as hold-out, no data shuffling; without this, all metrics are invalid
- Forecasting metrics (MAPE, MAE, RMSE, directional accuracy) — frozen in `forecast.py`, printed in parseable format
- Naive baselines (last-value repeat + same-quarter-last-year) — frozen; agent must beat both to "keep" an experiment
- Expanded mutable zone 2 — `CLAUDE.md` updated to describe feature engineering section + modeling section in `train.py`
- Lag features template (lag-1, lag-4) — `CLAUDE.md` provides canonical starter code for agent drafts
- Optuna search space in `train.py` — agent writes `optuna.create_study` + `objective(trial)`, not the orchestrator

**Should have (post-validation additions):**
- YoY and QoQ growth rate features (low complexity, high signal for detrended revenue)
- Rolling window statistics — 2 and 4-quarter windows, constrained to `<= N/4` to avoid consuming training rows
- Feature importance pruning — drop features below 1% of max importance before final model to reduce small-N overfitting
- Optuna trial budget guidance in `CLAUDE.md` (50 trials for drafts, 200 for final model)

**Defer to v2.x or v3.0:**
- AIDE-style branch-on-best (git log inspection to jump to best-ever commit when plateau detected — high reward, high complexity)
- STL decomposition features (requires N >= 8 quarters minimum, only valid for larger series)
- Multi-company joint models (different revenue scales require normalization layer — v3 problem)

**Anti-features to avoid explicitly:**
- Deep learning (LSTM, Transformer) — catastrophically small N for any neural network
- Foundation model forecasting (TimeGPT, Chronos) — zero-shot performance unreliable on proprietary financial data
- Non-temporal k-fold CV — `KFold(shuffle=True)` is categorically wrong for time series; produces 30-50% inflated metrics
- ADF/KPSS stationarity tests — unreliable at N < 30; use YoY growth rates for stationarity instead

See: `.planning/research/FEATURES.md`

### Architecture Approach

The v1.0 frozen/mutable boundary shifts in one precise way: `prepare.py` is simplified to data loading and temporal split only, and a new frozen module `forecast.py` owns all validation and metrics. The mutable `train.py` expands to include feature engineering alongside model selection. The single-mutable-file constraint is preserved. The agent writes feature engineering code (lag functions, rolling stats, growth rates) and Optuna search space code, all in `train.py`. The frozen module provides the walk-forward evaluation loop via a callable interface — the agent passes `model_fn: Callable[[DataFrame, Series], Any]` to `walk_forward_evaluate()`, and the frozen module controls the split protocol.

**Major components:**
1. `prepare.py` (frozen, simplified) — `load_data(csv_path, target_col, date_col)` returning raw DataFrame with datetime index; `temporal_split(df, target_col, holdout_fraction=0.15)` returning time-ordered train/holdout splits; `get_data_summary()`. Removes: `build_preprocessor`, `evaluate`, `get_baselines`, `split_data`, `METRIC_MAP`.
2. `forecast.py` (new frozen module) — `METRIC_MAP` with mape/smape/mae/rmse; `walk_forward_evaluate(model_fn, X, y, metric, n_splits=3)` using `TimeSeriesSplit`; `compute_metric(y_true, y_pred, metric_name)`; `get_forecasting_baselines()` computing naive, seasonal naive, and exponential smoothing baselines.
3. `train.py` (mutable, expanded) — agent writes: `engineer_features(df)` function with lag/rolling/growth features; Optuna `objective(trial)` calling `walk_forward_evaluate()`; final model training on full train set; holdout evaluation calling `compute_metric()`; structured output unchanged from v1.
4. `scaffold.py` (updated) — adds `date_column` parameter, copies `forecast.py` into experiment directory, calls `get_forecasting_baselines()` for `program.md`, uses `train_template_forecast.py`, expands deny list.
5. `guard-frozen.sh` + `settings.json` (updated) — deny list expands from `prepare.py` to `prepare.py forecast.py`.

**Key patterns:**
- Callable `model_fn` interface between mutable and frozen modules — agent controls what happens inside each fold, frozen module controls the split
- Feature engineering inside each CV fold, not globally before splitting — structural leakage prevention
- Optuna `timeout=TIME_BUDGET * 0.6` — leaves room for final model and holdout evaluation
- Expanding window (not rolling) for quarterly revenue — all available history is relevant; rolling discards old data wastefully at N=20-80

**Build order:** Layer 1: `forecast.py` + simplified `prepare.py` with tests. Layer 2: `train_template_forecast.py`. Layer 3: `scaffold.py` updates. Layer 4: `CLAUDE.md` and `program.md` template updates. Layer 5: `cli.py` `--date-column` flag. Layer 6: integration tests.

See: `.planning/research/ARCHITECTURE.md`

### Critical Pitfalls

1. **Temporal leakage in lag/rolling feature calculation** (CRITICAL) — agent computes features on full dataset before fold split, or uses `rolling(4).mean()` without `shift(1)`. Metrics look excellent (MAPE 3-5%) but model is useless in production. Prevention: frozen `walk_forward_evaluate()` must call agent's `engineer_features()` inside each fold iteration, not before. `CLAUDE.md` must explicitly state: "ALL rolling stats must call `.shift(1)` before `.rolling()`." Add leakage detection in `forecast.py`: warn if `correlation(feature, target) > 0.99` on test data.

2. **Scaler fit on full training set before walk-forward folds** (CRITICAL) — `StandardScaler.fit_transform(df_train)` before CV loop leaks fold distribution information. Prevention: CLAUDE.md must prohibit fitting any scaler outside the CV loop. Agent must fit scaler inside `model_fn` on `X_train_fold` only.

3. **Optuna overfitting walk-forward metric at small N** (HIGH) — with n=40 and 5 folds, each test set has 6-8 samples; 200+ optuna trials hill-climb to hyperparameters that exploit those specific data points. Holdout MAPE gets worse while walk-forward MAPE improves. Prevention: cap trials at `min(50, 2 * n_rows)`. Use narrow search spaces (`max_depth: [3,6]`, not `[1,20]`). CLAUDE.md must set explicit trial cap of 50 for datasets under 100 rows.

4. **Insufficient walk-forward folds producing noisy keep/revert decisions** (HIGH) — n=40 with minimum 20-quarter training window yields at most 5 test folds; MAPE estimate has ±40-50% confidence interval. Prevention: design `walk_forward_evaluate()` to warn when total test points across all folds is less than 20. Report fold-level standard deviation alongside mean MAPE. CLAUDE.md: do not "keep" when improvement is less than 2x the fold standard deviation.

5. **Not establishing naive/seasonal baselines before iterating** (HIGH) — agent iterates on "improvements" that are worse than the naive last-value or seasonal-naive forecast. Prevention: `get_forecasting_baselines()` runs at scaffold time and results are embedded in `program.md`. CLAUDE.md keep criterion: must beat BOTH naive baselines to "keep." If seasonal naive beats the model, agent must try different feature engineering, not just different hyperparameters.

6. **Feature dimensionality explosion on small N** (MEDIUM) — unconstrained agent creates 20+ features on 40 training rows. Prevention: `program.md` recommends 5-10 features maximum. Agent applies feature importance pruning (drop below 1% of max importance). CLAUDE.md warning: "With fewer than 50 training rows, more than 10 features guarantees overfitting."

See: `.planning/research/PITFALLS.md`

---

## Implications for Roadmap

Based on combined research, the v2.0 roadmap has a strict dependency ordering driven by one constraint: the walk-forward validation module must exist before any features can be safely tested. Without a leakage-free evaluation framework, every experiment result is invalid, and the agent's keep/revert decisions build on a corrupt foundation. This forces the first phase to be purely foundational.

### Phase 1: Foundational Modules (forecast.py + simplified prepare.py)

**Rationale:** Walk-forward validation is the prerequisite for everything else. Without `forecast.py`, there is no safe way to test features or Optuna. This phase has zero external dependencies — it only requires the existing sklearn stack. It is also the highest-risk phase: getting the `walk_forward_evaluate()` interface wrong creates subtle leakage that is hard to detect later.

**Delivers:** `forecast.py` with METRIC_MAP, compute_metric, walk_forward_evaluate, get_forecasting_baselines. Simplified `prepare.py` with load_data (date_col support), temporal_split, get_data_summary. Comprehensive unit tests for both modules — tests must verify: walk-forward split never shuffles data, compute_metric returns higher-is-better for all four metrics, baselines compute correctly on synthetic quarterly data, leakage detection warns when correlation > 0.99.

**Addresses features:** Walk-forward temporal validation, forecasting metrics (MAPE/MAE/RMSE/directional accuracy), naive baselines.

**Avoids pitfalls:** Pitfall 1 (temporal leakage) and Pitfall 2 (scaler leakage) — by structurally enforcing leakage prevention in the frozen module.

**Research flag:** Standard patterns — skip research-phase. sklearn TimeSeriesSplit and statsmodels SimpleExpSmoothing are well-documented.

### Phase 2: Forecast Template and Expanded Mutable Zone

**Rationale:** Once the frozen evaluation infrastructure exists, the agent needs a starting point that demonstrates the correct `engineer_features()` + Optuna pattern. CLAUDE.md and program.md must be updated before any agent experiments, or the agent will write incorrect feature engineering code and the loop will produce meaningless results.

**Delivers:** `train_template_forecast.py` with correct lag features, Optuna study stub calling `walk_forward_evaluate()`, structured output unchanged from v1. Updated `CLAUDE.md` template with v2 mutable zone description, leakage warnings (shift-first mandate), Optuna trial cap (50 for N < 100), forbidden file list expanded to include `forecast.py`. Updated `program.md` template with forecasting context section (date range, baselines, feature engineering hints).

**Addresses features:** Expanded mutable zone 2, lag features template, Optuna search space in train.py.

**Avoids pitfalls:** Pitfall 1 (shift-first in CLAUDE.md), Pitfall 3 (trial cap in CLAUDE.md), Pitfall 6 (feature count warning in CLAUDE.md).

**Research flag:** Standard pattern — skip research-phase. ARCHITECTURE.md provides a complete `train.py` example with exact code. Template is mechanical.

### Phase 3: Scaffold and CLI Updates

**Rationale:** The scaffold is the delivery mechanism. Once the frozen modules and templates exist, `scaffold.py` must be updated to wire them together: copy `forecast.py` into the experiment directory, compute baselines, render the updated program.md, expand the deny list. CLI needs `--date-column` to identify forecast mode.

**Delivers:** Updated `scaffold.py` with `date_column` parameter, `forecast` mode detection, `get_forecasting_baselines()` call, expanded `_dot_claude_settings()` deny list (`prepare.py forecast.py`), expanded `guard-frozen.sh`. Updated `cli.py` with `--date-column` flag. Updated `pyproject.toml` with `optuna` and `statsmodels` dependencies.

**Addresses features:** Guard hook updates, CLI forecasting mode entry point.

**Avoids pitfalls:** Inadvertent agent editing of `forecast.py` (structural protection via deny list and hook).

**Research flag:** Standard pattern — skip research-phase. Changes are mechanical wiring of existing components.

### Phase 4: End-to-End Validation

**Rationale:** Before declaring v2.0 complete, a real or synthetic 60-row quarterly dataset should be run through the full loop: scaffold, multi-draft (3 algorithms), pick best, 10 iterations, confirm metrics improve and agent beats seasonal naive. This phase also validates which optional features (YoY growth, rolling stats, feature importance pruning) should be included in CLAUDE.md starter hints versus left for the agent to discover.

**Delivers:** FINDINGS.md documenting: baseline scores, best model MAPE, iterations to beat seasonal naive, any leakage warnings observed, Optuna trial counts used, wall-clock time per experiment. Decision log on optional feature hints. Updated CLAUDE.md with trial budget guidance based on observed performance.

**Addresses features:** v2.0 post-validation features (YoY/QoQ growth rates, rolling window stats, feature importance pruning, Optuna trial budget guidance).

**Avoids pitfalls:** Pitfall 4 (insufficient folds) — observed in real data; Pitfall 5 (baseline comparison) — verified agent beats both baselines.

**Research flag:** Execution-phase discovery — no pre-research needed. Run the loop and document findings.

### Phase Ordering Rationale

- Phase 1 before Phase 2: Template cannot demonstrate correct walk-forward integration until `forecast.py` exists with the right API signature.
- Phase 1 before Phase 3: Scaffold cannot copy `forecast.py` or call `get_forecasting_baselines()` until the module exists.
- Phase 2 before Phase 3: Scaffold uses `train_template_forecast.py` — template must exist first.
- Phase 3 before Phase 4: Cannot run end-to-end validation without scaffolding system working.
- Phases 1 and 2 can partially overlap if `walk_forward_evaluate()`'s interface (function signature only) is locked in early — the template only needs the signature, not the implementation.

### Research Flags

Phases needing deeper research during planning:
- None for core phases (1-3). All components have well-documented patterns. ARCHITECTURE.md provides precise function signatures and complete code examples. Implementation is mechanical.

Phases where additional research would be valuable but is not blocking:
- **Phase 4 post-validation observation:** If the agent consistently fails to beat seasonal naive by iteration 10, research whether `feature-engine`'s `WindowFeatures` with configurable aggregation outperforms manual lag construction for quarterly revenue. Not blocking — run the loop first.
- **Future v2.x AIDE branch-on-best:** When planned, will need research into git worktree interaction with the keep/revert protocol and `results.tsv` parsing for best-commit SHA identification.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | optuna, sklearn TimeSeriesSplit, sklearn MAPE all verified via official docs. feature-engine MEDIUM-HIGH (confirmed at 1.9.4, sklearn-compatible, less battle-tested for this exact use case). statsmodels HIGH. No unresolved version conflicts. |
| Features | HIGH | Walk-forward validation, lag features, MAPE are textbook practice (fpp2 + sklearn docs). Naive baseline requirement informed by AIDE paper (arxiv:2502.13138). Small-N thresholds (N=20, N=30, N=60 cutoffs) are domain-reasoned, not benchmarked against this exact dataset size — treat as MEDIUM confidence guidelines, not hard rules. |
| Architecture | HIGH | Based on direct codebase reading of `prepare.py`, `scaffold.py`, `train_template.py`, `CLAUDE.md`. Callable `model_fn` interface is a clean design with clear sklearn precedent. Single-mutable-file constraint is well-justified by autoresearch and AIDE findings. |
| Pitfalls | HIGH | Temporal leakage mechanisms are precisely documented with concrete code examples. Optuna small-N overfitting is acknowledged in Optuna's own documentation. Walk-forward fold count math is straightforward. |

**Overall confidence:** HIGH

### Gaps to Address

- **Small-N thresholds need empirical validation:** STACK.md and FEATURES.md recommend specific cutoffs (N < 30: prefer Ridge; N >= 60: 5 folds safe). These are domain-reasoned. During Phase 4 E2E validation, observe actual fold sizes and metric variance on the real dataset and adjust CLAUDE.md guidance accordingly.
- **feature-engine vs. manual `shift()` inside `model_fn`:** Architecture recommends manual `shift()` inside `engineer_features()` for simplicity. feature-engine is listed as a dependency but its transformers may not be strictly required if the agent writes correct manual lag functions. Resolve during Phase 2 template authoring — decide whether to require feature-engine or list it as optional.
- **`statsmodels` necessity:** Added for exponential smoothing baseline. If ETS baseline adds complexity without meaningfully improving agent decisions (baselines are reference points only), consider removing ETS and keeping only naive + seasonal naive. Two baselines may be sufficient. Resolve during Phase 1 implementation.
- **Optuna trial budget split between draft phase and iteration phase:** FEATURES.md recommends 50 trials per draft. With 5 drafts at 50 trials each, the draft phase alone runs 250 Optuna trials before the iteration loop starts. Phase 2 template authoring must clarify: no Optuna during drafts (evaluate default hyperparameters only for algorithm selection), full Optuna only during iteration phase.

---

## Sources

### Primary (HIGH confidence)
- `src/automl/prepare.py` — direct codebase reading, current frozen module API
- `src/automl/scaffold.py` — direct codebase reading, current scaffolding implementation
- `src/automl/train_template.py` — direct codebase reading, current mutable zone structure
- `src/automl/templates/claude.md.tmpl` — direct codebase reading, current agent protocol
- sklearn TimeSeriesSplit docs (v1.8.0) — gap parameter, n_splits, expanding window behavior
- sklearn MAPE docs — `mean_absolute_percentage_error` available since sklearn 0.24, confirmed in current stack
- Optuna 4.7.0 official docs — define-by-run API, TPE sampler, n_startup_trials default, timeout parameter
- statsmodels exponential smoothing docs — `SimpleExpSmoothing` API confirmed

### Secondary (MEDIUM confidence)
- feature-engine 1.9.4 docs (feature-engine.trainindata.com) — `LagFeatures`, `WindowFeatures`, `ExpandingWindowFeatures` sklearn compatibility confirmed
- AIDE paper (arxiv:2502.13138) — tree search mechanism, naive baseline requirement, algorithm diversity rationale; adoption feasibility for this task type is speculative
- Hyndman & Athanasopoulos "Forecasting: Principles and Practice" (fpp2) — walk-forward validation, MASE, STL decomposition
- Optuna small-N trial recommendations — synthesized from Optuna docs examples; not formally benchmarked against n=40 quarterly revenue

### Tertiary (LOW confidence)
- FLAML vs. Optuna benchmark (FLAIRS conference paper) — FLAML 2.52% vs. Optuna 1.96% average improvement over random search; used only to confirm Optuna is competitive
- XGBoost walk-forward forecasting (arXiv:2601.08896v1) — general pattern confirmation only

---

*Research completed: 2026-03-14*
*Ready for roadmap: yes*
