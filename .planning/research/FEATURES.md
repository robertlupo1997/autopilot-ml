# Feature Research

**Domain:** Autonomous ML Forecasting — v2.0 Results-Driven Forecasting (time series features, optuna, walk-forward validation)
**Researched:** 2026-03-14
**Confidence:** MEDIUM-HIGH (web search + official docs for optuna; domain expertise from fpp2 + sklearn; AIDE from arxiv paper)

> **Scope note:** This file covers NEW capabilities for v2.0 only. v1.0 features (experiment loop, git state, multi-draft, CLI, resume, swarm) are complete and documented in the previous FEATURES.md revision (dated 2026-03-09). Do not re-implement those.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that must exist for v2.0 to be a credible forecasting system. Missing any of these means the system produces unreliable forecasts or cannot be trusted.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Walk-forward temporal validation** | Random CV on time series produces optimistic results by leaking future data into training. Every serious time series library (sklearn TimeSeriesSplit, skforecast backtesting) uses temporal ordering. Without it, metrics are meaningless. | MEDIUM | Replace random `train_test_split` in prepare.py with expanding-window or fixed-window splits that respect temporal order. Frozen in prepare.py — agent cannot touch it. Last N quarters as hold-out. |
| **Lag features (agent-mutable)** | Lag-t features are the primary mechanism for making tabular ML work on time series. Without them, models only see contemporaneous features, which are unavailable at prediction time. | MEDIUM | Agent writes lag creation code in train.py (mutable zone 2). Core lags for quarterly revenue: lag-1 (prior quarter), lag-4 (same quarter prior year). Agent must apply lags AFTER train/test split to avoid leakage. |
| **Rolling window statistics (agent-mutable)** | Rolling mean and std over 2, 4, 8-quarter windows capture trend and volatility that lag features alone miss. Standard practice in time series tabular ML. | MEDIUM | Agent writes rolling stats in train.py. Stats computed on training data only; test set uses training-period statistics (no leakage). Complexity: with only 20-80 data points, use small windows (2-4 quarters max) to avoid losing too many leading rows to NaN. |
| **Forecasting-appropriate metrics (MAPE + MAE + RMSE)** | Revenue forecasting requires metrics in dollar units (MAE, RMSE) and percentage error (MAPE). Directional accuracy (% quarters where direction predicted correctly) answers "does it predict growth vs. decline." These replace classification accuracy. | LOW | Frozen in prepare.py. Report all four: MAPE, MAE, RMSE, directional accuracy. Primary optimization target: MAPE (scale-independent, business-readable). Add MASE as fallback if revenue values approach zero. |
| **Expanded mutable zone (feature engineering + modeling)** | v1.0 agent only modifies algorithm and hyperparameters. v2.0 must let agent write feature engineering code. Without this, the agent cannot experiment with lag combinations, rolling windows, or growth rates. | MEDIUM | Mutable zone 2: agent can modify both a `features.py` section of train.py (feature creation) and the modeling section. Frozen zone: data loading, train/test split, metric calculation in prepare.py. |
| **Optuna hyperparameter search (agent writes search space)** | Manual hyperparameter guessing by the agent in v1.0 is inefficient. Optuna runs 100-200 trials to find optimal hyperparameters. Without it, each "experiment" is a single model fit rather than an optimized one. | MEDIUM | Agent writes `objective(trial)` function with `trial.suggest_*` calls. Optuna study runs inside train.py. Agent controls: which parameters to search, their ranges, and trial count. Orchestrator does not call optuna API — agent writes the code that calls it. |
| **No future data leakage by design** | Leakage is the most common mistake in time series ML. Validation strategy must enforce it structurally — the agent must not be able to accidentally use future data. | HIGH | prepare.py creates train/test indices before any feature engineering. Feature engineering happens on the training set only; test set features are computed using only training-period lookback values. This is an architectural constraint, not a reminder in CLAUDE.md. |

### Differentiators (Competitive Advantage)

Features that go beyond standard practice and make this system meaningfully better than a basic regression or AutoML baseline.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Year-over-year (YoY) growth rate features** | Revenue is often more stationary in percentage-change space than in level space. YoY growth = (Q_t - Q_{t-4}) / Q_{t-4}. Outperforms raw lag features on detrended series. Canonical for financial data. | LOW | Agent adds YoY and QoQ growth rates as features. Requires lag-4 (YoY) and lag-1 (QoQ) to already exist. Compound growth rate over trailing 4-8 quarters is also useful. Compute on training data only. |
| **Optuna + multi-draft interaction** | v1.0 multi-draft generates 3-5 diverse algorithms. v2.0 adds optuna optimization to each draft candidate. The combination (algorithm diversity + hyperparameter optimization) captures AIDE's key insight — algorithm choice matters — while also extracting the best possible performance from each choice. | MEDIUM | During draft phase: each draft runs N optuna trials (N=50 for drafts, N=200 for best model). Agent controls trial budget. Prevents long draft phase from bottlenecking iteration speed. |
| **Naive baseline comparison in every experiment** | AIDE achieves better results partly by always measuring against a naive benchmark. For quarterly forecasting, the naive forecast is "last observed value repeated" or "same quarter last year." Without it, the agent cannot judge if its model is actually useful. | LOW | Frozen in prepare.py: compute naive_mape and naive_mae using both "repeat last value" and "same quarter last year" baselines. Agent sees these in the evaluation output. CLAUDE.md instructs: must beat both baselines to "keep." |
| **Trend and seasonality decomposition features** | Decomposing revenue into trend + seasonal + residual (via STL or classical) gives the agent separable components to model. Seasonal indices (Q1/Q2/Q3/Q4 average deviations from trend) are high-signal features for quarterly data. | MEDIUM | Agent can optionally add STL decomposition features. Only valid if N >= 2 full seasonal cycles (>=8 quarters). For N < 8, seasonal index features are unreliable — agent should avoid. CLAUDE.md should note the minimum-N constraint. |
| **Feature importance pruning per experiment** | Agent uses tree model feature importances or permutation importance to drop uninformative lag features before fitting the final model. Reduces overfitting risk on small N. Key to AIDE-style "simplicity criterion." | MEDIUM | Agent writes feature selection code in train.py using XGBoost/LightGBM importance or sklearn permutation importance. Threshold: drop features with importance < 1% of max. Enforces parsimony on small datasets. |
| **AIDE-inspired branch-on-best** | AIDE's key advantage over linear agents: when the current path plateaus, branch from the best-ever solution rather than the most-recent one. For forecasting, this means: if rolling MAE stops improving for 5 iterations, jump back to the best-performing train.py commit and try a different direction. | HIGH | Requires git log inspection to identify best-commit SHA, then `git checkout` that commit's train.py, then continue iterating. Orchestrator (CLAUDE.md) must instruct this behavior. Higher complexity: agent must reason about git history, not just current state. Reserve for later phase within v2.0. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Deep learning / LSTM / Transformer forecasting** | Seems more powerful. LSTMs and transformers are popular for time series. | 20-80 quarterly data points is catastrophically small for any neural network. LSTMs need hundreds of sequences. N-BEATS/Transformers need thousands. Result: overfitting, unstable training, worse results than XGBoost on small N. Training is also slow on CPU. | XGBoost/LightGBM with lag features outperforms LSTMs on small tabular data. Save neural networks for v3 or when N > 500. |
| **Foundation model time series (TimeGPT, Moirai, Chronos)** | Zero-shot forecasting, no feature engineering needed, state-of-the-art results on M4/M5 benchmarks. | These models are pretrained on diverse series. For single-company revenue, the pretrained prior may be wrong. Zero-shot performance on proprietary financial data is unreliable. Also requires API calls or model downloads, adding complexity. | Fine-tuning requires N > 500 typically. For N=20-80, traditional ML with domain-specific features (YoY, seasonality) is more reliable. |
| **ARIMA / SARIMA / state-space models** | Traditional time series, interpretable, well-understood for quarterly data. | Cannot be directly integrated into the agent's train.py + optuna pattern. ARIMA requires `statsmodels`, different fit API, different validation approach. Adding a second model family doubles the complexity of prepare.py. Agent also cannot easily engineer features for ARIMA. | Use ARIMA as a naive baseline comparison (implement once in prepare.py, frozen). Do not make it a mutable target for the agent. |
| **Expanding mutable zone to data loading** | Agent might find better ways to handle missing values or data normalization. | Data loading changes can silently corrupt the leakage-prevention guarantee. If agent modifies how train/test indices are created, all subsequent experiments produce invalid results with no warning. | Keep prepare.py strictly frozen. Mutable zone 2 = feature engineering + modeling only. If data preprocessing needs improvement, that is a human decision made outside the loop. |
| **Auto-differencing / stationarity tests (ADF, KPSS)** | Standard practice in classical time series to check stationarity. | With N=20-80, ADF/KPSS tests have very low power — they frequently fail to reject the null even when data is non-stationary. Acting on unreliable test results causes incorrect differencing. | Use YoY growth rates as features instead. Growth rates achieve near-stationarity for revenue without requiring formal testing. Agent can experiment with log-transforming the target variable instead. |
| **Cross-company or multi-series joint models** | Training on multiple companies seems to give more data. | Different companies have completely different revenue scales, growth rates, and seasonality profiles. A joint model either needs careful normalization or learns spurious cross-company patterns. In scope for v3 (with normalization layer), not v2. | Train one model per company. Multi-company is a v3 problem with explicit normalization and series-ID embeddings. |
| **Grid search / random search for hyperparameters** | Simpler than optuna, no new dependency. | Grid search is exponential in the number of parameters. Random search ignores trial history. For 5+ hyperparameters (n_estimators, max_depth, learning_rate, subsample, colsample), optuna's TPE sampler finds better solutions with fewer trials. The cost of adding optuna (one pip install) is low. | Use optuna with TPE sampler exclusively. It finds good solutions in 50-100 trials where grid search would require 1000+. |
| **N-fold cross-validation (non-temporal)** | Standard sklearn cross_val_score is familiar and easy. | For time series, k-fold CV shuffles the data, letting the model train on future data and test on past data. This produces wildly optimistic metrics (sometimes 30-50% better than actual out-of-sample performance). The leakage is silent and hard to detect. | Always use expanding-window or fixed-window walk-forward splits. Frozen in prepare.py. The agent must never import `KFold` or `cross_val_score`. |

---

## Feature Dependencies

```
[Walk-Forward Temporal Validation (prepare.py, frozen)]
    +--required by--> [All metrics: MAPE, MAE, RMSE, DA]
    +--required by--> [Lag features (agent)]
                          +--required by--> [YoY / QoQ growth rate features]
                          +--required by--> [Rolling window statistics]
                                                +--feeds--> [Feature importance pruning]
                                                              +--feeds--> [Optuna search]

[Optuna search space (agent writes in train.py)]
    +--enhances--> [Multi-draft (v1.0, existing)]
    +--depends on--> [Expanded mutable zone 2]

[Naive baseline (prepare.py, frozen)]
    +--required by--> [AIDE-inspired branch-on-best]
    +--informs--> [CLAUDE.md "keep" criterion]

[Expanded mutable zone 2 (architectural)]
    +--enables--> [Lag features]
    +--enables--> [Rolling window statistics]
    +--enables--> [YoY growth rates]
    +--enables--> [STL decomposition features]
    +--enables--> [Feature importance pruning]
    +--enables--> [Optuna search space]
```

### Dependency Notes

- **Walk-forward validation must be built before any features are tested.** If leakage exists in the validation strategy, every experimental result is invalid. This is a prepare.py change and must be the first thing implemented in v2.0.
- **Expanded mutable zone 2 is an architectural prerequisite.** CLAUDE.md must be updated to tell the agent which parts of train.py it can modify (features section + modeling section) and which it cannot (evaluation calls, data loading).
- **Lag features are a prerequisite for YoY/QoQ growth rates.** Growth rates are computed from lags, so lag creation must come first in the feature pipeline.
- **Optuna enhances but does not replace multi-draft.** The draft phase still generates 3-5 diverse algorithms; optuna then optimizes each draft's hyperparameters. The sequencing is: multi-draft → evaluate each with optuna(N=50) → pick best → iterate with optuna(N=200).
- **Naive baseline is a frozen evaluation artifact.** It is computed once per experiment inside prepare.py and reported alongside model metrics. Agent cannot modify it.
- **AIDE-style branch-on-best requires git log inspection.** This is the most complex dependency: it requires the agent (or orchestrator) to parse `results.tsv`, identify the best-MAPE commit SHA, and `git checkout` that file before continuing iteration. Build after all other features are stable.

---

## MVP Definition for v2.0

### Launch With (v2.0 core — must ship together)

All of these must be implemented before the v2.0 loop is valid. They are interdependent: without the leakage-free split, all features and metrics are unreliable.

- [ ] **Walk-forward temporal validation in prepare.py** — expanding-window split, last 4 quarters as hold-out, no data shuffling. Leakage prevention by construction.
- [ ] **Forecasting metrics (MAPE, MAE, RMSE, directional accuracy)** — frozen in prepare.py, printed in a parseable format (e.g., `MAPE: 8.3%`, `MAE: $12.4M`).
- [ ] **Naive baselines (last-value repeat + same-quarter-last-year)** — frozen in prepare.py, always reported. CLAUDE.md keep criterion: beat both.
- [ ] **Expanded mutable zone 2** — CLAUDE.md updated to describe feature engineering section + modeling section. Guard hook updated to protect prepare.py only.
- [ ] **Core lag features template** — CLAUDE.md provides canonical lag-1 and lag-4 starter code that agent uses as starting point for drafts.
- [ ] **Optuna search space (agent writes objective function)** — agent writes `optuna.create_study` + `objective(trial)` in train.py. Orchestrator does not call optuna; agent writes and runs the code.

### Add After Core Validation

Add these once the core loop produces valid, leakage-free metrics on a real dataset.

- [ ] **YoY / QoQ growth rate features** — agent learns to add these from CLAUDE.md hints. Low complexity.
- [ ] **Rolling window statistics** — agent adds 2- and 4-quarter rolling mean/std. Constrain window size to ≤ N/4 to avoid consuming too many training samples.
- [ ] **Feature importance pruning** — agent adds post-fit pruning step using model.feature_importances_ before reporting final metric.
- [ ] **Optuna trial budget guidance in CLAUDE.md** — 50 trials for drafts, 200 trials for final model. Prevents agent from using 1000+ trials and burning time budget.

### Future Consideration (v2.x or v3.0)

- [ ] **AIDE-style branch-on-best** — jump to best-ever git commit when plateau detected. High complexity, high reward. Requires orchestrator changes.
- [ ] **STL decomposition features** — seasonal indices from statsmodels.tsa.seasonal. Only valid N >= 8. Add when benchmark datasets confirm value.
- [ ] **Multi-draft + optuna interaction optimization** — tune the trial budget split between draft phase and iteration phase based on observed wall-clock performance.
- [ ] **MASE metric** — add if any dataset has revenue values that approach zero, making MAPE undefined. Low priority for corporate revenue.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Phase |
|---------|------------|---------------------|-------|
| Walk-forward temporal validation | HIGH | MEDIUM | v2.0 core |
| Forecasting metrics (MAPE/MAE/RMSE/DA) | HIGH | LOW | v2.0 core |
| Naive baseline comparison | HIGH | LOW | v2.0 core |
| Expanded mutable zone 2 | HIGH | MEDIUM | v2.0 core |
| Lag features (lag-1, lag-4) | HIGH | LOW | v2.0 core |
| Optuna search space (agent writes) | HIGH | MEDIUM | v2.0 core |
| YoY / QoQ growth rate features | MEDIUM | LOW | v2.0 post-validation |
| Rolling window statistics | MEDIUM | LOW | v2.0 post-validation |
| Feature importance pruning | MEDIUM | LOW | v2.0 post-validation |
| Optuna trial budget in CLAUDE.md | MEDIUM | LOW | v2.0 post-validation |
| AIDE branch-on-best | HIGH | HIGH | v2.x |
| STL decomposition features | LOW | MEDIUM | v2.x |
| MASE metric | LOW | LOW | v3.0 if needed |

**Priority key:**
- v2.0 core: Must ship together, all interdependent
- v2.0 post-validation: Add after first successful v2.0 end-to-end run
- v2.x: Valuable but not blocking
- v3.0: Defer until motivated by real use case

---

## Technical Guidance: The Five Core Research Questions

### 1. What time-series feature engineering matters most for small-N quarterly revenue?

**Constraints:** With 20-80 quarterly observations, the effective training set after an expanding-window split is 12-60 samples. Feature engineering must be parsimonious or it will overfit.

**Ranked by impact for small N:**

1. **Lag-1 and lag-4** (prior quarter, same quarter last year): highest signal, direct seasonal anchor. Always include. Loss of 4 leading rows is acceptable.
2. **YoY growth rate** (Q_t - Q_{t-4}) / Q_{t-4}: detrends the series, often more stationary than levels. Include as soon as lag-4 exists.
3. **2-quarter rolling mean**: smooths one-quarter noise. Use lag-2 as base to avoid leakage. Window > 4 loses too many rows on small N.
4. **Quarter-of-year indicator (Q1/Q2/Q3/Q4)**: captures fixed seasonal effects without requiring decomposition. 3 dummy variables, zero data cost.
5. **Compound growth rate over trailing 4 quarters**: captures acceleration / deceleration of growth. Derives from lag features already present.

**Do not use on small N:** lag-8 or beyond (reduces training set further), STL decomposition (needs 2+ full seasons = 8+ quarters minimum), ADF stationarity tests (unreliable at N < 30).

**Confidence:** MEDIUM (standard practice verified in sklearn docs + fpp2 textbook; small-N constraint is domain reasoning, not benchmarked against this specific dataset size)

### 2. How should optuna integrate — agent writes search space vs. agent calls optuna API?

**Recommendation: Agent writes the entire `objective(trial)` function inside train.py. The orchestrator does not call optuna.**

**Rationale:** Optuna's define-by-run API is designed to be written by a developer (or agent). The agent writes:

```python
import optuna
def objective(trial):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 50, 500),
        "max_depth": trial.suggest_int("max_depth", 2, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
    }
    model = xgb.XGBRegressor(**params)
    # ... fit + evaluate on walk-forward folds ...
    return mape

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=100)
```

The agent controls: which parameters to tune, their ranges, the trial budget, and which metric optuna optimizes. The orchestrator only reads the final MAPE printed at the end.

**Why not have orchestrator call optuna?** The agent must be able to change the search space (e.g., add a new parameter, change ranges) as part of its improvement iterations. If orchestrator controls optuna, the agent cannot do this without changing orchestrator code — defeating the purpose of the autonomous loop.

**Trial budget guidance for CLAUDE.md:**
- Draft evaluation: 50 trials per draft (fast, sufficient for algorithm selection)
- Final model iteration: 200 trials (thorough optimization of winning algorithm)
- Do not exceed 500 trials per experiment (diminishing returns + wall-clock cost)

**Confidence:** HIGH (based on optuna official docs define-by-run API; integration pattern is standard Python coding style)

### 3. What walk-forward validation strategy works for 20-80 quarterly data points?

**Recommendation: Expanding-window walk-forward with a fixed 4-quarter hold-out.**

**Design:**
- Hold-out: last 4 quarters (1 year), never touched during training or optuna optimization
- Validation folds: expanding window starting from min_train_size = 12 quarters (3 years)
- Number of folds: (N - hold_out_size - min_train_size) / step_size, stepping 1 quarter at a time
- For N=20: 20 - 4 - 12 = 4 folds. For N=80: 80 - 4 - 12 = 64 folds (use step=4 to keep fold count manageable)

**Why expanding (not rolling)?** Expanding window uses all available historical data as the series grows. For revenue forecasting, older data is still relevant (it establishes base-period levels). Rolling windows discard old data, which is wasteful at N=20-80.

**Why fixed hold-out (not part of CV)?** The hold-out measures final generalization. It must never influence model selection or hyperparameter tuning. Optuna optimizes on the CV folds; the hold-out is the final report card.

**Minimum viable at N=20:** 12 training + 4 validation + 4 hold-out = 20. Tight but workable. CLAUDE.md must warn agent: with N < 16, walk-forward CV is unreliable — use a simple last-4-quarter hold-out only.

**What to freeze:** The walk-forward split logic lives in prepare.py (frozen). The agent never touches it. The agent only writes feature engineering + model fitting code that operates on the pre-split indices.

**Confidence:** HIGH (walk-forward expanding window is textbook practice; specific N thresholds are domain-reasoned, not benchmarked)

### 4. What metrics matter for revenue forecasting?

**Primary optimization target: MAPE** (Mean Absolute Percentage Error)
- Why: scale-independent, business-readable ("our forecasts are off by X% on average"), enables comparison across different revenue magnitudes
- Limitation: undefined when actual revenue = 0; inflated when actuals are small positive numbers
- For corporate quarterly revenue, actuals are typically large ($M or $B) — MAPE is safe

**Report alongside MAPE:**
- **MAE** (Mean Absolute Error in dollar units): tells stakeholders the dollar magnitude of errors
- **RMSE**: penalizes large misses more heavily; relevant if a single-quarter miss is catastrophic
- **Directional accuracy**: % of quarters where model correctly predicts growth vs. decline. A model can have good MAPE but consistently predict wrong direction, making it useless for strategic planning

**Naive baselines (frozen, always reported):**
- Naive-last: forecast = last observed quarter value
- Naive-seasonal: forecast = same quarter from prior year (lag-4)
- Agent must beat BOTH to justify keeping an experiment. If the optimized model loses to Naive-seasonal, the agent should try a different approach.

**MASE** (Mean Absolute Scaled Error): add only if revenue values approach zero (startup with early losses). MASE scales by the in-sample naive MAE, so it is always defined. Low priority for established companies.

**What not to use:** MSE (not interpretable in dollar-squared units), R-squared (misleading for time series), accuracy (wrong framing for regression).

**Confidence:** MEDIUM-HIGH (standard forecasting metrics verified in Hyndman & Athanasopoulos fpp2; directional accuracy is domain best practice; naive baseline requirement is informed by AIDE's benchmark-first approach)

### 5. How does AIDE achieve better results — what can we adopt?

AIDE's three mechanisms for better results, ranked by adoptability for this project:

**Mechanism 1: Algorithm diversity at start (adopted in v1.0)**
AIDE generates 5 diverse initial solutions covering different algorithm families. v1.0 already does this (multi-draft). No change needed.

**Mechanism 2: Tree-based reuse of best solutions (partially adopt)**
AIDE stores all solutions in a tree. When exploring, it selects parent nodes based on score + visit count (UCB-like). The key insight adoptable without full tree search: **when stuck, jump back to best-ever commit, not just last commit.** v1.0 does linear keep/revert from the current state. v2.x adds: if MAE fails to improve for 5 consecutive iterations, `git checkout` the best-ever train.py and try a different feature engineering direction.

**Mechanism 3: Fine-grained code reuse (adopt partially via optuna)**
AIDE caches code at the "stage" level, reusing the parts that work and only changing the parts that don't. In our system, optuna achieves something similar: the agent fixes the algorithm family and feature set, while optuna explores hyperparameter variations. The agent's role shifts from "guess hyperparameters" to "design the search space and feature engineering."

**What AIDE does that we should NOT adopt in v2.0:**
- Full MCTS with backpropagation: requires maintaining a tree of N git branches simultaneously. Extremely complex. Multi-draft + linear with branch-on-best (v2.x) gets 80% of the benefit.
- LLM-as-judge for metric extraction: adds latency and non-determinism. Our frozen prepare.py with structured metric output is strictly better for deterministic evaluation.
- Two-model architecture (draft model + refinement model): overkill for a single-company forecasting use case.

**The single highest-value AIDE insight to adopt:** measure against a strong naive baseline at every iteration, and only "keep" if the model beats the baseline. This prevents the agent from iterating on mediocre models and forces it to genuinely improve.

**Confidence:** MEDIUM (AIDE paper arxiv:2502.13138 is authoritative; adoption feasibility reasoning is speculative — benchmark against this specific task type not available)

---

## Competitor Feature Analysis

| Feature | Basic Regression | Standard AutoML (FLAML/H2O) | AIDE (aideml) | Our v2.0 Approach |
|---------|-----------------|---------------------------|---------------|-------------------|
| Feature engineering | Manual or none | Automated (all possible features) | Agent-written per task | Agent-written, CLAUDE.md-guided, parsimonious |
| Hyperparameter search | None or manual | Full AutoML search across algorithms | Agent-defined search space | Optuna (agent writes search space) |
| Time series validation | Often random CV | Some have time-aware CV | Not time-series-specific | Expanding window, frozen in prepare.py |
| Naive baseline | Usually absent | Included in some | Not standard | Always computed, required to beat for "keep" |
| Overfitting risk on small N | High (no constraint) | High (too many features) | Unconstrained | Mitigated by feature importance pruning + small window constraint |
| Interpretability | High | Low | Low | CLAUDE.md can ask for comments; feature importances reported |
| Domain knowledge injection | Manual | None | Goal description | program.md (rich domain context) |
| Forecasting metrics | RMSE usually | RMSE/MAE | Task-dependent | MAPE + MAE + RMSE + directional accuracy |
| Autonomous iteration | None | One-shot | Tree search, autonomous | Linear keep/revert + multi-draft, git-based |

---

## Sources

- Optuna official documentation v4.7.0 (optuna.readthedocs.io) — define-by-run API, trial.suggest_* methods, TPE sampler
- AIDE paper: arxiv.org/abs/2502.13138 — tree search mechanism, code reuse, naive baseline practice
- Hyndman & Athanasopoulos "Forecasting: Principles and Practice" (fpp2, otexts.com) — walk-forward validation, STL decomposition, MASE
- scikit-learn TimeSeriesSplit documentation — expanding window split mechanics
- Feature Engine library (feature-engine.trainindata.com) — lag features, rolling window features for time series
- XGBoosting.com — walk-forward validation with XGBoost
- numberanalytics.com — walk-forward CV guide
- mljourney.com — time series feature engineering techniques
- pmorgan.com.au — MAE, MAPE, MASE comparison
- Microsoft FLAML GitHub (github.com/microsoft/FLAML) — BlendSearch vs optuna comparison
- PROJECT.md — architecture decisions, staged mutable zones, existing v1.0 capabilities

---

*Feature research for: v2.0 Results-Driven Forecasting*
*Researched: 2026-03-14*
