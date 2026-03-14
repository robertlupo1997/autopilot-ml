# Pitfalls Research

**Domain:** Autonomous ML Experiment Framework — v2.0 Time-Series Feature Engineering, Optuna, Walk-Forward Validation, Revenue Forecasting
**Researched:** 2026-03-14
**Confidence:** HIGH (grounded in original project research report + 2025-2026 literature on time-series ML, small-N forecasting, optuna optimization, and autonomous agent pitfalls)

---

## Scope Note

This document covers **v2.0-specific pitfalls** layered on top of the v1.0 pitfalls (which remain valid — see the v1.0 section at the bottom). The v2.0 pitfalls address the five questions in the research brief:

1. LLM agent feature engineering — lookahead bias and target leakage
2. Optuna + LLM agent — search space overfitting on small N
3. Walk-forward validation on 20-80 rows — not enough windows, unstable estimates
4. Revenue forecasting specifics — seasonality, regime changes, log transforms
5. The n=40 problem — what actually works with 20-80 quarterly data points

---

## Severity Ranking

| Pitfall | Severity | Why |
|---------|----------|-----|
| Temporal leakage in lag features | CRITICAL | Inflated metrics, silently wrong, model is useless in production |
| Agent using future data in rolling stats | CRITICAL | Silently corrupts every metric in the loop |
| Optuna overfitting the walk-forward splits | HIGH | Model selection is wrong; best hyperparams are illusions |
| Not establishing naive/seasonal baselines first | HIGH | Agent iterates on "improvements" that are actually worse than naive |
| Walk-forward with too few folds (< 5) | HIGH | Metric estimate has huge variance; keep/revert decisions are noise |
| Log transform mismatch — train vs. test | HIGH | MAPE/MAE computed in log space = meaningless numbers |
| Regime change blindness | MEDIUM | Model trained on pre-COVID revenue fails post-COVID silently |
| XGBoost/LightGBM on n=40 without constraint | MEDIUM | Overfits perfectly, zero generalization |
| Rolling stat window exceeding training set size | MEDIUM | NaN contamination silently drops rows or creates zeros |
| Expanding vs. sliding window wrong choice | MEDIUM | Data starvation (sliding) or regime drift (expanding) |
| Agent creating too many features on n=40 | MEDIUM | Dimensionality curse — p >> n guaranteed with unconstrained feature engineering |
| Seasonal artifact confusion | LOW-MEDIUM | Agent interprets FY calendar artifacts as real patterns |

---

## Critical Pitfalls

### Pitfall 1: Temporal Leakage in Lag Feature Calculation

**What goes wrong:**
The LLM agent calculates lag features using pandas `.shift()` incorrectly, or creates rolling statistics using the wrong window alignment. The most common form: computing a 4-quarter rolling mean using `rolling(4).mean()` on the full dataset before the train/test split, then splitting. This means the "lag-4 rolling mean" for Q4-2019 includes Q1-2020, Q2-2020, Q3-2020, Q4-2020 data in its window during training. The model learns from the future. Metrics look excellent (MAPE 3-5%) during the loop, but the model is useless in deployment (MAPE 40-60%).

This is the single most dangerous pitfall in v2.0. The agent will introduce it without knowing it, the metric will look great, and the keep/revert loop will lock it in as the "best" solution. There is no stack trace. The loop never catches it.

**Why it happens:**
LLMs do not reliably understand temporal indexing semantics. The agent knows that `rolling(4).mean()` computes a 4-period rolling average, but it does not reliably place the `shift(1)` call required to avoid including the current period. It also does not reliably understand that feature engineering must happen strictly within each training fold, not on the full dataset before splitting. The problem compounds with walk-forward validation: even if the lag is computed correctly on the full series, if features are computed globally and then the dataset is split, future-period statistics bleed into training samples.

**Concrete examples:**
- `df['revenue_4q_rolling_mean'] = df['revenue'].rolling(4).mean()` — includes current quarter in the mean, introduces 1-period lookahead at minimum
- `df['revenue_lag1'] = df['revenue'].shift(-1)` — agent accidentally uses negative shift (future) instead of positive (past)
- Computing `df['yoy_growth'] = df['revenue'].pct_change(4)` and then including `df.iloc[-1]['yoy_growth']` in a feature for the last known row — this requires knowing the revenue 4 quarters ago, which is fine, but the agent may then use it as a label proxy
- `df['revenue_normalized'] = (df['revenue'] - df['revenue'].mean()) / df['revenue'].std()` computed on full dataset before split — mean and std include future quarters

**How to avoid:**
1. **Freeze the feature engineering API.** The frozen pipeline provides `make_features(df, cutoff_date)` — a function that takes a DataFrame and a date and returns features computed strictly from data where `date < cutoff_date`. The agent calls this function; it cannot access the raw DataFrame directly.
2. **Enforce shift-first semantics.** In CLAUDE.md, explicitly state: "ALL lag features must use `.shift(N)` where N >= 1. `.shift(0)` or `.shift(-N)` are prohibited. ALL rolling stats must call `.shift(1)` after `.rolling()` before any split." Include a code example.
3. **Add a leakage detection test.** In the frozen evaluation module, check: `correlation(feature_values[test_idx], target[test_idx]) > 0.99` triggers a leakage warning. Perfect correlation between a feature and the target on test data is a red flag.
4. **Feature engineering inside the CV fold.** When using walk-forward validation, lag features must be computed using only the training data visible at each fold's cutoff. The agent should use `skforecast` or `sklearn.pipeline.Pipeline` with a custom transformer that recomputes lags at each fold.

**Warning signs:**
- MAPE on the walk-forward splits drops below 5% for quarterly revenue on n=40 data
- Features have correlation > 0.95 with the target
- Removing the lag features causes metric to collapse (suggests they are proxies for the target, not predictors)
- Agent's feature list includes terms like "current_revenue", "same_period_revenue", or anything that sounds like it's encoding the target

**Phase to address:**
Phase 1 of v2.0 (Feature Engineering Mutable Zone). The frozen pipeline must enforce the `make_features(df, cutoff_date)` API before the agent touches any feature code. Non-negotiable.

---

### Pitfall 2: Agent Uses Future Data in Rolling Statistics Inside Walk-Forward Folds

**What goes wrong:**
Even if the agent correctly uses `.shift(1)` on the full series, the walk-forward implementation may be wrong in a subtler way: the agent computes ALL features on the full dataset first, then splits into folds. This means that a rolling-12-quarter standard deviation computed on rows [0..39] includes future data for rows near the train/test boundary of each fold. For example, fold 3 (train: rows 0-29, test: rows 30-34) — the feature at row 28 might use rows 17-28 for its rolling window, which is correct, but if features were computed globally before the fold split, the normalization factors (mean, std) used in any scaler applied after feature computation still see future data.

**Why it happens:**
The conceptual error is treating feature computation as a static preprocessing step and CV splits as a post-processing step. The correct order is: for each fold, compute features using only training data, fit scaler/encoder using only training data, transform test data using the training-fitted scaler.

**Concrete example:**
```python
# WRONG — agent does this:
df['rolling_mean'] = df['revenue'].rolling(4).mean().shift(1)
scaler = StandardScaler()
df['revenue_scaled'] = scaler.fit_transform(df[['revenue']])  # sees all rows
# then splits into walk-forward folds

# RIGHT — must do this inside each fold:
for train_idx, test_idx in walk_forward_splits:
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)  # transform only, not fit
```

**How to avoid:**
1. The frozen evaluation module must implement the walk-forward loop and call the agent's feature-engineering function inside each fold iteration, not before.
2. CLAUDE.md must explicitly prohibit: "Do NOT fit StandardScaler, MinMaxScaler, or any encoder on the full dataset. All scalers must be fit inside the CV loop on training data only."
3. Use `sklearn.pipeline.Pipeline` — it correctly handles fit vs. transform separation when used with `cross_val_score`.

**Warning signs:**
- Scaler is instantiated and fit once, outside any loop
- Agent's code has `scaler.fit_transform(df[...])` on the full DataFrame before any split
- Walk-forward metrics are suspiciously uniform across all folds (leakage makes every fold look good)

**Phase to address:**
Phase 1 of v2.0 (Feature Engineering Mutable Zone) + Phase 2 (Walk-Forward Validation). The frozen evaluation module's walk-forward loop must call the agent's feature code inside the fold, not outside.

---

### Pitfall 3: Optuna Overfitting the Walk-Forward Validation Metric on Small N

**What goes wrong:**
The agent uses optuna to tune hyperparameters, running 100-500 trials, each evaluated against the same walk-forward CV metric. With n=40 and 5 walk-forward folds, each fold has roughly 6-8 training samples and 1-2 test samples. Optuna's TPE sampler efficiently hill-climbs to hyperparameters that exploit the specific patterns in those 5-8 held-out data points. The "optimal" hyperparameters are not optimal for the distribution — they are optimal for those specific quarterly data points. Out-of-sample performance is worse than a simple model with default hyperparameters.

This is the "double dipping" problem: walk-forward CV is supposed to be an unbiased performance estimate, but when optuna uses it as the objective for hundreds of trials, the metric is no longer unbiased. You've fit the model selection criterion to the validation data.

**Why it happens:**
With n=40 and 5 folds, the test set across all folds has ~8-10 data points. Those 8-10 data points have specific quirks (one recession quarter, one acquisition quarter, etc.). Optuna's TPE algorithm finds hyperparameter combinations that happen to predict those 8-10 specific quarters well — even if they generalize poorly.

Optuna itself acknowledges this risk: with small datasets, traditional methods like grid search or random search may outperform TPE because the optimization surface is too noisy for Bayesian methods to find meaningful signal.

**Concrete example:**
An XGBoost model with default hyperparameters might achieve MAPE=15% on truly held-out 2024 data. After 200 optuna trials optimizing walk-forward MAPE on 2015-2023 data, the "optimized" model achieves walk-forward MAPE=8% but truly held-out MAPE=22%. The optimization made it worse.

**How to avoid:**
1. **Cap trials proportionally to n.** Rule of thumb: `max_trials = min(50, 2 * n_rows)`. With n=40, cap at 50 trials. With n=80, cap at 100.
2. **Use random search before bayesian.** For the first half of trials, use `optuna.samplers.RandomSampler`. Only switch to TPE after establishing a baseline. This prevents early exploitation of noise.
3. **Narrow the search space aggressively.** The agent must not define a search space covering `max_depth: [1, 20]` and `n_estimators: [10, 5000]`. Instead: `max_depth: [3, 6]`, `n_estimators: [30, 150]`. A narrow search space has less overfitting surface.
4. **Hold out the last 2 years (8 quarters) as a true holdout that optuna never sees.** Optuna optimizes on folds from the earlier period. The final model is then evaluated on the true holdout. If walk-forward metric and holdout metric diverge by >30%, the optimization overfit.
5. **Prefer regularization over complexity.** Include `lambda`, `alpha` (L1/L2) in the search space. Let optuna find regularization strength rather than model complexity.
6. **In CLAUDE.md:** "When using optuna on datasets with fewer than 100 rows, set `n_trials <= 50`. The search space must be narrow — see the example in this file. Always use the holdout set defined in evaluate.py to check whether optuna improved or hurt performance."

**Warning signs:**
- Walk-forward MAPE falls dramatically (>40% relative improvement) after optuna, but holdout MAPE is worse
- Optimal hyperparameters are extreme values (`max_depth=1` or `max_depth=15`, `n_estimators=10` or `n_estimators=2000`)
- Each optuna run picks very different "optimal" hyperparameters (sign of noise, not signal)
- Optuna run takes longer than 10 minutes on n=40 data (sign that n_trials is too high)

**Phase to address:**
Phase 2 of v2.0 (Optuna Integration). The CLAUDE.md for v2.0 must include explicit trial caps and narrow search space examples.

---

### Pitfall 4: Walk-Forward Validation With Too Few Folds — Unreliable Metric Estimates

**What goes wrong:**
With n=40 quarterly data points and a minimum training window of 20 quarters (5 years), you can generate at most 5 walk-forward test folds (quarters 21-25, 22-26, 23-27, 24-28, 25-29 if sliding 1 quarter at a time, less if expanding). With only 5 test folds, the MAPE estimate has a 95% confidence interval of roughly ±40-50% of its value. A model showing MAPE=10% might actually be anywhere from 5% to 15% in expectation. The keep/revert loop is making decisions on noise.

Research confirms: achieving statistical power of 80% for quarterly forecasting requires approximately 540 test folds. With 5-10 folds, you achieve roughly 12-20% power. Nearly every keep vs. revert decision is statistically indistinguishable from a coin flip.

**Why it happens:**
Walk-forward validation is the correct approach, but its statistical properties are well-known in the research literature and almost universally ignored in practice. The smaller the dataset, the wider the confidence interval on the performance estimate, and the less reliable the keep/revert decision becomes.

**Expanding vs. sliding window tradeoffs for n=40:**
- **Expanding window**: Maximizes training data at each fold (good). Means early folds have very small training sets (bad — first fold might train on 16 quarters, ~4 years). If a regime change occurred 10 years ago, expanding window includes pre-change data that might be misleading.
- **Sliding window**: Fixes training set size (e.g., always 20 quarters). Avoids regime drift. But with n=40, a fixed 20-quarter window means only 20 test quarters available — still only 5-10 folds if using 2-4 quarter steps.

**Recommendation: Expanding window is correct for n=40.** With only 40 rows, you cannot afford to discard data via sliding window. Accept that early folds have small training sets. The expanding window's gradual accumulation mirrors how the model will be used in production (more data available over time).

**How to avoid:**
1. **Set a minimum of 6 walk-forward folds.** If n < 30, walk-forward is not reliable enough to use as the keep/revert metric — fall back to leave-one-out CV or accept wider uncertainty.
2. **Report fold count and training-set size in results.tsv.** The agent should log: `folds=8, min_train_n=16, max_train_n=36` so a human can audit whether the validation setup is credible.
3. **Use step size of 1 quarter.** Do not skip quarters in the walk-forward procedure. Each additional fold reduces variance in the metric estimate. With n=40, every fold matters.
4. **Set minimum training window = 4 years (16 quarters).** Fewer than 16 training quarters means the model is fitting on 4 years of quarterly patterns — insufficient for seasonality detection or trend estimation.
5. **Accept wide error bars.** In CLAUDE.md: "On n=40, a MAPE improvement of less than 2 percentage points may be noise. Only keep changes that improve MAPE by >5% relative (e.g., from 12% to 11.4% at minimum)."

**Warning signs:**
- Walk-forward folds < 5
- Agent declares a winner with MAPE improvement of 0.5-1.0 percentage points
- Minimum training set size < 12 quarters
- Results vary wildly between runs with different random seeds (sign of high-variance metric)

**Phase to address:**
Phase 2 of v2.0 (Walk-Forward Validation implementation). The frozen evaluation module must enforce minimum fold count and report training set sizes.

---

### Pitfall 5: Naive and Seasonal Baselines Not Established First — Agent "Improves" on Nothing

**What goes wrong:**
The keep/revert loop starts with a draft ML model (e.g., XGBoost with lag features) and iterates to improve it. After 50 experiments, it achieves MAPE=14%. This sounds good. But seasonal naive (use last year's same quarter as the forecast) achieves MAPE=11%. The agent spent 50 iterations getting worse than a naive baseline.

This is specific and well-documented: the M-Competitions and their successors consistently show that naive baselines (naive, seasonal naive, drift, exponential smoothing) are surprisingly competitive — often outperforming ML methods on short corporate financial time series. A model that cannot beat seasonal naive on quarterly revenue with n=40 has learned nothing.

**Why it happens:**
The multi-draft start generates diverse ML models but does not generate naive baselines. MAPE=14% looks like a real result because the agent has no reference point. Nobody said "MAPE=11% is achievable with zero complexity."

**How to avoid:**
1. **Make seasonal naive the mandatory floor baseline.** Before the first experiment, the frozen evaluation module computes: (a) naive baseline (last observed value), (b) seasonal naive (same quarter last year), (c) drift (linear extrapolation), (d) exponential smoothing (ETS). Store these as `floor_metrics` in a JSON file. Any model that does not beat ALL four baselines is automatically reverted, regardless of metric value.
2. **Include baselines in the multi-draft start.** Draft 0 is always the seasonal naive baseline. Drafts 1-5 are ML approaches. This establishes calibration from iteration 0.
3. **Log baseline comparisons in results.tsv.** Every experiment row should include `vs_seasonal_naive: +3.2%` so the agent knows its margin above the floor.

**Warning signs:**
- No baseline computation before the first ML experiment
- Agent celebrates MAPE < 15% without knowing what seasonal naive achieves
- results.tsv has no "vs_baseline" column
- First draft is already an ML model (no naive baseline draft)

**Phase to address:**
Phase 1 of v2.0 (Metric Redesign + Baseline Infrastructure). Baselines must be computed in the frozen `evaluate.py` before ANY model runs.

---

## High Severity Pitfalls

### Pitfall 6: Log Transform Mismatch — Metrics Computed in Wrong Space

**What goes wrong:**
Revenue data is right-skewed and grows over time. The agent log-transforms the target (`y = log(revenue)`), trains a model, and evaluates MAPE. But MAPE in log space is not meaningful — it measures percentage error in log-revenue, not revenue. A log-space MAPE of 5% could correspond to a revenue MAPE of 5% or 50%, depending on the magnitude. The agent optimizes log-space MAPE and reports it as the final metric. Stakeholders see "MAPE=5%" but the model is 30% off in dollar terms.

**Why it happens:**
The agent knows log transforms help with skewed regression targets. It applies the transform correctly for training but forgets to inverse-transform predictions before computing the metric, or computes the metric after inverse-transforming but using a biased inverter (Jensen's inequality: `exp(E[log(y)]) != E[y]`).

**Concrete example:**
- Model predicts `log(revenue)` and achieves log-MAE = 0.08
- Inverse transform: `predicted_revenue = exp(log_prediction)` — introduces downward bias because `E[exp(X)] > exp(E[X])` for non-zero variance
- The correct inverse: use `exp(log_prediction + 0.5 * sigma^2)` for bias correction, or evaluate on raw revenue after inverse transform
- Agent does neither and reports log-space MAE as the metric

**How to avoid:**
1. **Always evaluate metrics on the original revenue scale.** The frozen `evaluate.py` must inverse-transform predictions before computing MAPE, MAE, RMSE. The agent may log-transform internally during training, but the evaluation function always works in dollar space.
2. **Use MAPE and MAE on raw revenue, not log-revenue.** The metric that gets reported to results.tsv must be in the original scale.
3. **In CLAUDE.md:** "If you log-transform the target, you MUST inverse-transform predictions before calling evaluate(). The evaluate() function always reports metrics in original scale. Never report log-space metrics."
4. **Apply bias correction on inverse transform.** If `sigma` is available: `exp(pred + 0.5 * residual_variance)` corrects Jensen's inequality bias. The agent should implement this when using log transforms.

**Warning signs:**
- MAPE is suspiciously low (< 3%) on quarterly revenue with n=40
- Agent mentions "log-MAPE" or "log-MAE" in experiment descriptions
- Metric units are inconsistent across experiments (some log-space, some original-scale)
- Large discrepancy between logged MAPE and actual dollar error when manually checked

**Phase to address:**
Phase 1 of v2.0 (Metric Redesign). The frozen `evaluate.py` must enforce original-scale metrics with explicit inverse-transform if needed.

---

### Pitfall 7: Regime Change Blindness — Model Trained on Pre-Event Data

**What goes wrong:**
A company's quarterly revenue history from 2005-2024 includes pre-2008 (pre-financial crisis), 2009-2019 (recovery + growth), 2020 (COVID collapse), 2021-2022 (rebound), 2023-2024 (normalization). A model trained on all of this history may fit the average of multiple regimes — none of which reflects the current dynamics. Walk-forward validation starting from 2005 will test the model on 2019-2024 data, which spans 3+ different regimes. The model's errors in early walk-forward folds (2019) may be low (stable growth regime), but errors in later folds (2020-2021) are high. The average MAPE obscures regime-specific failure.

The agent sees MAPE=18% overall and treats it as a single number. It does not notice that fold-by-fold errors jump from 5% to 65% to 8%. It iterates toward minimizing the average, which may mean fitting the COVID regime better at the expense of the normal regime.

**Why it happens:**
The keep/revert metric is a single scalar (mean MAPE across folds). It collapses temporal structure. The agent cannot see that the model is good in normal quarters but catastrophically bad in transition quarters.

**How to avoid:**
1. **Report per-fold MAPE in addition to mean MAPE.** The frozen `evaluate.py` logs fold-level metrics to results.tsv. The agent can see: `fold_mapes: [4.2, 5.1, 62.3, 11.2, 8.9]`.
2. **Flag high-variance folds.** If any single fold's MAPE is > 3x the median fold MAPE, the experiment log shows a warning: "HIGH VARIANCE: fold 3 MAPE=62% suggests potential regime change."
3. **Recommend recency weighting.** In CLAUDE.md: "For quarterly revenue, consider limiting training data to the most recent 20 quarters (5 years). Older data from different regimes may hurt more than help. Try both full history and 5-year window and report which performs better."
4. **Structural break detection as a feature.** Adding a binary `post_event` flag (e.g., post-COVID, post-acquisition) as a feature often outperforms implicit regime learning.

**Warning signs:**
- High standard deviation of per-fold MAPE (std > mean)
- Agent reports mean MAPE without fold-level breakdown
- Model performs well in early folds but poorly in the most recent 4-8 quarters
- Revenue history spans known macroeconomic events (2008-09, 2020) that the agent ignores

**Phase to address:**
Phase 2 of v2.0 (Walk-Forward Validation). Per-fold metrics must be part of the evaluation output. Flagging should be automated in the frozen evaluator.

---

### Pitfall 8: XGBoost/LightGBM On n=40 Without Heavy Regularization — Perfect Train, Zero Test

**What goes wrong:**
XGBoost and LightGBM are the agent's preferred algorithms (they win on most tabular benchmarks). With n=40 and even 5-10 features, these models have enough capacity to memorize the training data. Training RMSE approaches 0 while test RMSE stays high. The model has learned the quarterly revenue sequence by heart, including its noise. It generalizes nothing.

This is not theoretical. XGBoost's default `max_depth=6` with `n_estimators=100` can perfectly overfit 40 rows in seconds. The agent will see low training error and use it as a positive signal unless the metric is strictly walk-forward CV on held-out data.

**Why it happens:**
The agent defaults to models that work well on large tabular benchmarks. The "more trees = better" heuristic that works at n=10,000 becomes "more trees = more overfit" at n=40.

**How to avoid:**
1. **Set conservative XGBoost/LightGBM defaults for small N.** In CLAUDE.md: "For datasets with fewer than 100 rows, start with: `max_depth=3`, `n_estimators=50`, `learning_rate=0.1`, `subsample=0.8`, `colsample_bytree=0.8`, `reg_lambda=10`, `reg_alpha=1`. These are mandatory starting points, not suggestions."
2. **Require the agent to justify relaxing regularization.** If it wants `max_depth > 4` or `n_estimators > 100` on n < 80, it must explain why in the experiment description.
3. **Force early stopping with walk-forward.** Use XGBoost's `early_stopping_rounds=10` with the walk-forward validation set as the eval_set. This automatically prevents overfitting.
4. **Make Ridge regression a mandatory draft.** Ridge (linear model) with polynomial features or lag features cannot overfit the same way. It should always be one of the initial drafts on small-N data.
5. **Include linear models in every draft generation.** On n=40, Ridge/Lasso/ElasticNet with carefully chosen features often outperforms tree-based models. The agent must be explicitly told this.

**Warning signs:**
- Training RMSE approaches 0 while validation RMSE stays high
- `n_estimators > 200` or `max_depth > 5` on n < 80 with no regularization
- Holdout performance is dramatically worse than walk-forward CV performance
- Agent never tries linear models (Ridge, Lasso, ElasticNet) — defaults to tree-based

**Phase to address:**
Phase 1 of v2.0 (Feature Engineering + Mutable Zone 2 Design). CLAUDE.md small-N defaults section is mandatory. Phase 2 (Optuna) must enforce regularization in the search space.

---

## Moderate Pitfalls

### Pitfall 9: Dimensionality Curse — Agent Engineers More Features Than Rows

**What goes wrong:**
The agent generates lag-1 through lag-8 (8 features), 4-quarter and 8-quarter rolling mean and std (4 features), quarter dummies (3 features), year-over-year growth (1 feature), 2-year CAGR (1 feature), linear trend (1 feature) — 18+ features on 40 rows. p/n ratio = 0.45. This is already in dangerous territory for regression. If the agent gets ambitious and adds cross-products or interaction terms, p/n > 1 and OLS-style methods are undefined; tree methods will overfit. Even XGBoost with heavy regularization struggles when p/n > 0.5 on time-series data.

**How to avoid:**
1. **Enforce a feature budget.** CLAUDE.md: "On datasets with fewer than 80 rows, limit total features to `max(10, n_rows / 5)`. With n=40, maximum 10 features total including all lags, rolling stats, and calendar features."
2. **Require feature importance pruning.** After fitting, log feature importances. Features with importance < 0.01 should be removed in the next iteration.
3. **Penalize feature count in the keep/revert decision.** A 20-feature model that achieves the same MAPE as a 5-feature model should be reverted — the 5-feature model is better.
4. **Mandatory feature selection step.** One of the multi-draft options should be a heavily pruned model: 3-5 features selected by correlation with the target, then fitted with Ridge.

**Phase to address:**
Phase 1 of v2.0 (Feature Engineering Mutable Zone). Feature budget must be in CLAUDE.md from day one.

---

### Pitfall 10: Rolling Stat Windows Wider Than Available Training Data

**What goes wrong:**
The agent creates a rolling-12-quarter (3-year) mean feature. On the first fold of walk-forward validation, where only 16 quarters are in the training set, rows 1-11 have `NaN` for this feature (insufficient history). Pandas silently fills these with NaN or zeros depending on `min_periods`. If NaN: those rows drop from training (training set shrinks from 16 to 5). If zero: the feature is wrong. Either way, the model trains on corrupted data and the agent does not notice.

**How to avoid:**
1. **Set `min_periods=1` on all rolling calculations** so partial windows are used rather than producing NaN, and document this choice.
2. **Limit rolling window to half the minimum training set size.** With a minimum 16-quarter training window, rolling stats should use at most 8 quarters.
3. **Log the number of valid (non-NaN) rows in each training fold.** If fewer than 12 valid training rows exist, raise a warning.
4. **Validate feature completeness.** After feature engineering, assert: `X_train.isna().sum().sum() == 0`. Any NaN must be handled explicitly (fill, drop, or flag).

**Phase to address:**
Phase 1 of v2.0 (Feature Engineering). The feature validation assertion must be in the frozen `evaluate.py`.

---

### Pitfall 11: Seasonal Artifact Confusion — FY Calendar vs. True Seasonality

**What goes wrong:**
Corporate quarterly revenue exhibits two types of patterns: true economic seasonality (retail Q4 holiday surge, B2B Q1 budget flush) and fiscal calendar artifacts (companies close Q4 deals to make annual numbers, regardless of underlying demand). An agent engineering seasonal features may treat FY calendar patterns as stable seasonality and create lag-4 (same quarter last year) features. But if the company changed its FY end, or if the economic seasonal pattern shifted (e.g., post-COVID B2B buying patterns changed), the lag-4 feature encodes a broken assumption.

Additionally, with only 10 years of quarterly data (40 rows), you have 10 observations per quarter. A sample of 10 is insufficient to estimate quarterly seasonality reliably. The agent's "seasonal feature" may be fitting noise.

**How to avoid:**
1. **Limit to lag-1 and lag-4 as the only seasonal lags.** Don't create lag-2, lag-3, lag-5, etc. without evidence from the data that those lags have predictive value.
2. **Validate seasonal features with autocorrelation.** If lag-4 autocorrelation < 0.4, the seasonal feature may be noise. Include this check in the CLAUDE.md: "Before adding a seasonal lag feature, verify that the autocorrelation at that lag is > 0.4."
3. **Note fiscal year end in program.md.** If the company's FY ends in March (not December), lag-4 = same FY quarter, not same calendar quarter. The agent needs this context in program.md.

**Phase to address:**
Phase 1 of v2.0 (Feature Engineering). program.md must include FY end date and known structural breaks.

---

### Pitfall 12: MAPE Undefined or Misleading on Near-Zero Revenue

**What goes wrong:**
MAPE = `|actual - predicted| / actual`. If any actual revenue value is zero or near-zero (startup quarters, write-downs, discontinued segments), MAPE becomes undefined (divide by zero) or extremely large (99% error on a $1M actual when predicted $2M). The agent's walk-forward MAPE spikes in one fold due to a near-zero quarter and the metric becomes uninterpretable. The agent reverts a good model because one anomalous quarter dominated MAPE.

**How to avoid:**
1. **Use sMAPE or MASE as alternatives, or clip MAPE at 200%.** Symmetric MAPE = `2 * |actual - predicted| / (|actual| + |predicted|)` is bounded and defined when actual = 0 if predicted != 0. MASE (Mean Absolute Scaled Error) normalizes by the seasonal naive forecast and is the recommended metric for intermittent/near-zero series.
2. **Use MAE in dollars as the primary metric for small-N forecasting.** MAE is robust to zero values and interpretable: "average error of $2.3M per quarter."
3. **Flag anomalous quarters.** If any quarter's revenue is > 3 standard deviations from the mean, flag it in program.md so the agent knows to treat it as an outlier rather than a signal.

**Phase to address:**
Phase 1 of v2.0 (Metric Redesign). The frozen `evaluate.py` must choose between MAPE, sMAPE, and MASE depending on the target distribution.

---

## The n=40 Problem — What Actually Works

This deserves its own section because it fundamentally constrains what v2.0 can do.

### Evidence-Based Model Recommendations for n=20-80 Quarterly

| Method | Expected Performance | When It Works | When It Fails |
|--------|---------------------|---------------|---------------|
| Seasonal Naive | Baseline | Always (trivial) | Cannot improve regardless |
| Exponential Smoothing (ETS) | Often best or near-best | Stable trend + seasonality | Structural breaks, exogenous drivers |
| ARIMA/SARIMA | Often competitive | Stationary or differenced series | Regime changes, complex seasonality |
| Ridge Regression + 5 lag features | Competitive | When linear trend dominates | Non-linear relationships |
| Random Forest (shallow, `max_depth=3`) | Competitive if well-regularized | Multiple interacting features | p/n > 0.3, without regularization |
| XGBoost (conservative params) | Often worse than Ridge on n=40 | n > 80, more features | n < 60 — overfits |
| LightGBM | Same as XGBoost | Same | Same |

**The honest answer:** With 20-40 quarterly data points, the following hierarchy holds in the literature:
1. Seasonal Naive (baseline)
2. ETS / Exponential Smoothing
3. ARIMA/SARIMA
4. Ridge Regression with 3-5 lag features

Complex ML models (tree-based, gradient boosting) rarely outperform simple methods at n < 60 on quarterly financial time series. The agent should be told this explicitly.

**AIDE comparison on small-N forecasting:**
AIDE's tree-search approach is designed for datasets where many experiment iterations are informative. On n=40 quarterly data, the evaluation function is too noisy for AIDE's tree search to converge reliably — it would need hundreds of walk-forward folds to get a stable metric, which is impossible with n=40. The AutoML framework's simpler keep/revert loop is actually better suited here, because it makes fewer assumptions about the noise level of the metric. However, both systems share the same risk: the keep/revert decision is made on a noisy metric, and improvements of < 5% relative MAPE should be treated as inconclusive.

**Recommendation for the agent:**
CLAUDE.md for v2.0 should explicitly say: "The primary competition is seasonal naive and ETS, not other ML models. If your model does not improve on seasonal naive MAPE by at least 10% relative, it is not useful. Start simple: Ridge regression with lag-1, lag-4, and a linear trend. Expand complexity only if the simple model clearly beats seasonal naive."

---

## Technical Debt Patterns (v2.0)

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Compute all features on full dataset, then split | Simple code | Temporal leakage guaranteed | Never. Always compute inside the fold. |
| Use random K-fold CV instead of walk-forward | More folds, lower variance | Shuffle destroys temporal order, estimates are biased | Never for time series. Walk-forward only. |
| Report mean MAPE only (no per-fold breakdown) | Clean single metric | Regime changes invisible | Never — always report fold-level MAPE |
| 200+ optuna trials on n=40 | "Thorough" optimization | Optimization overfits the walk-forward folds | Never. Cap at 50 trials for n<80. |
| No naive baseline before first ML experiment | Faster to start | Agent may iterate on worse-than-naive forever | Never. Baselines are free and critical. |
| Log-transform target without inverse-transform in evaluate() | Easier model fitting | Metrics meaningless; comparing log-space MAPE across experiments | Never. Evaluate in original scale always. |
| Skip feature budget enforcement | Agent has full creative freedom | p >> n → guaranteed overfit on n=40 | Never for n < 80. Enforce feature cap. |
| Use all 40 years of company history | Maximizes data | Pre-regime data contaminates model | Acceptable only if regime stability verified |

---

## Integration Gotchas (v2.0)

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Pandas shift() for lags | `df['lag1'] = df['revenue'].shift(-1)` (negative shift = future) | Always positive shift: `df['lag1'] = df['revenue'].shift(1)` |
| Pandas rolling() for windows | `df['roll4'] = df['revenue'].rolling(4).mean()` (includes current row) | `df['roll4'] = df['revenue'].rolling(4).mean().shift(1)` |
| StandardScaler in CV loop | `scaler.fit_transform(X_full)` before split | Fit inside loop on train only, transform on test |
| Optuna + walk-forward | Same walk-forward splits used for both optuna and model selection | Reserve a final holdout that optuna never sees |
| MAPE with zero revenue | Divide by zero or inf | Use sMAPE or MASE; clip MAPE at 200% |
| Log transform + evaluation | Evaluate MAPE in log space | Always inverse-transform before evaluate() |
| XGBoost early_stopping | Passing full dataset as eval_set | Pass fold-specific validation set only |
| Seasonal dummies on n=40 | 3 quarter dummies on 40 rows = 3 predictors for 10 observations each | Use only if autocorrelation confirms seasonality (>0.4 at lag 4) |

---

## Performance Traps (v2.0)

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Optuna runs 500 trials on 5-fold walk-forward | 10+ minutes per experiment; optuna "converges" to nonsense | Cap trials at 50 for n<80 | Immediately on small datasets |
| Feature engineering recomputed inside every optuna trial | 50 trials × 5 folds × feature computation = 250 expensive computations | Precompute features once, pass to optuna as numpy arrays | When feature computation includes rolling stats on large windows |
| Rolling stats with `min_periods=None` on walk-forward training splits | NaN rows silently dropped; training set shrinks; no error reported | Set `min_periods=1`; assert zero NaN after feature engineering | First walk-forward fold always affected |
| log1p transform on revenue with large values | Numerically fine, but inverse transform is `expm1` not `exp` — easy mistake | Use log1p/expm1 pair consistently; document in code | Any time revenue > 0 (always) |

---

## "Looks Done But Isn't" Checklist (v2.0)

- [ ] **Temporal leakage test:** Remove all features and verify that the metric collapses — if it doesn't, features are encoding the target directly.
- [ ] **Shift direction test:** For every lag feature `df['lagN'] = df['revenue'].shift(N)`, verify N > 0 in the code.
- [ ] **Scaler placement test:** Search agent code for `scaler.fit_transform` — it must ONLY appear inside a CV loop, never on the full dataset.
- [ ] **Baseline floor test:** Verify that seasonal naive MAPE is computed before any ML experiment runs and stored as a floor in the evaluation module.
- [ ] **Optuna holdout test:** The holdout set used to validate optuna's result must not overlap with any optuna trial's train or test data.
- [ ] **Metric scale test:** Print an actual vs. predicted table in dollars (not log dollars) and verify the numbers make sense.
- [ ] **Feature budget test:** Assert `X_train.shape[1] <= max(10, n_rows // 5)` before fitting any model.
- [ ] **Fold count test:** Assert walk-forward produces >= 6 folds; log the count.
- [ ] **NaN assertion:** Assert `X_train.isna().sum().sum() == 0` after feature engineering.
- [ ] **Small-N model defaults test:** Verify XGBoost/LightGBM default config includes `max_depth <= 4`, `reg_lambda >= 5` for n < 80.
- [ ] **Per-fold MAPE logged:** Verify results.tsv includes both mean MAPE and per-fold MAPE breakdown.

---

## Recovery Strategies (v2.0)

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Temporal leakage discovered in lag features | HIGH | Discard ALL experiments since leakage introduction. Git reset to last known-clean feature code. Recompute baselines. All prior metrics are invalid. |
| Optuna overfitting detected (holdout much worse than CV) | MEDIUM | Reset hyperparameters to conservative defaults (max_depth=3, etc.). Rerun with trial cap = 20. Compare holdout metrics. |
| Walk-forward had too few folds | MEDIUM | Increase step size to 1 quarter if not already. Check if n_rows allows more folds. If not, switch metric to leave-one-out CV. |
| Log-space metric detected (metrics too good to be true) | MEDIUM | Fix evaluate() to inverse-transform. Rerun last 10-20 experiments. The "best model" may change. |
| Regime change causing high-variance folds | LOW-MEDIUM | Limit training window to post-2020 data. Rerun walk-forward. Compare mean MAPE on recent folds only. |
| XGBoost overfit (train=0, test=high) | LOW | Revert to last model with reasonable train/test gap. Tighten regularization in CLAUDE.md. Add Ridge as mandatory draft. |
| Feature dimensionality > n_rows / 5 | LOW | Revert to last model within budget. Add feature count assertion to evaluate.py. Reduce feature set. |
| Seasonal naive beats all ML models | LOW (recognition, not failure) | Accept this outcome. Report it honestly. Try ETS/ARIMA instead of ML. Document that the dataset may be too small for ML. |

---

## Pitfall-to-Phase Mapping (v2.0)

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Temporal leakage in lag features | v2.0 Phase 1: Feature Engineering API | Leakage detection test passes on synthetic future-leak injection |
| Rolling stat leakage across folds | v2.0 Phase 1 + Phase 2: Walk-Forward | Scaler placement test: no fit_transform outside CV loop |
| Optuna overfitting walk-forward | v2.0 Phase 2: Optuna Integration | Holdout test: optuna-tuned model within 10% of default-param model on holdout |
| Too few walk-forward folds | v2.0 Phase 2: Walk-Forward Validation | Fold count assertion fires; minimum 6 folds enforced |
| No naive baseline | v2.0 Phase 1: Metric Redesign | Baseline floor computed before experiment 1; visible in results.tsv |
| Log transform metric mismatch | v2.0 Phase 1: Metric Redesign | evaluate() outputs dollar-scale MAPE and MAE; log-space values absent |
| Regime change blindness | v2.0 Phase 2: Walk-Forward | Per-fold MAPE logged; high-variance flag fires on synthetic regime-change test |
| XGBoost overfit on small N | v2.0 Phase 1: CLAUDE.md defaults | Small-N defaults enforced; Ridge is mandatory draft 1 |
| Feature dimensionality > budget | v2.0 Phase 1: Feature Engineering | Feature count assertion in evaluate.py |
| Rolling window wider than training set | v2.0 Phase 1: Feature Engineering | NaN assertion passes; min_periods=1 enforced |
| Seasonal artifact confusion | v2.0 Phase 1: Feature Engineering | Autocorrelation check passes for any seasonal lag feature added |
| MAPE undefined on near-zero revenue | v2.0 Phase 1: Metric Redesign | evaluate() uses sMAPE or clipped MAPE; no inf/NaN in metric output |

---

## v1.0 Pitfalls (Still Valid)

The following pitfalls from the v1.0 research remain applicable and unchanged. They are not repeated in detail here but should be reviewed:

1. Silent failures — code runs but produces garbage (prediction distribution checks)
2. Data leakage in automated pipelines (hard boundary enforcement)
3. Context window flooding (run.log redirect, results.tsv as memory)
4. Agent stuck in loops (stagnation detection, exploration prompts)
5. Metric gaming and overfitting to validation set (hidden holdout)
6. Git state corruption (atomic operations, pre-experiment status check)
7. Over-complexity in generated code (single-file constraint, code length limits)
8. Claude Code orchestrator-specific failures (permission pre-authorization, heartbeat)
9. Multi-draft selection bias (CV for draft selection, runner-up preservation)
10. Inadequate experiment logging (rich results.tsv schema)

---

## Sources

- [A Standardized Benchmark of Look-ahead Bias in Point-in-Time Forecasting](https://arxiv.org/pdf/2601.13770) — INRIA, 2026. Look-ahead bias formalization.
- [A Test of Lookahead Bias in LLM Forecasts](https://arxiv.org/abs/2512.23847) — Gao et al., 2025. Lookahead Propensity (LAP) metric for LLM forecast evaluation.
- [Data Leakage, Lookahead Bias, and Causality in Time Series Analytics](https://medium.com/@kyle-t-jones/data-leakage-lookahead-bias-and-causality-in-time-series-analytics-76e271ba2f6b) — Kyle Jones. Practical examples of temporal leakage patterns.
- [Machine learning for financial forecasting, planning and analysis](https://link.springer.com/article/10.1007/s42521-021-00046-2) — Digital Finance, Springer. Revenue forecasting pitfalls specific to corporate finance.
- [Mind the naive forecast! a rigorous evaluation of forecasting models for time series with low predictability](https://link.springer.com/article/10.1007/s10489-025-06268-w) — Applied Intelligence, 2025. Naive baseline competitiveness on short series.
- [Reducing Optuna Optimization Overfitting Using Multi-Objective Approach](https://davidpalazon00.medium.com/reducing-optuna-omptimization-overfitting-using-specific-multi-objective-approach-ef3194f6e754) — Palazon Palau. Optuna overfitting mitigation.
- [How To Backtest Machine Learning Models for Time Series Forecasting](https://machinelearningmastery.com/backtest-machine-learning-models-time-series-forecasting/) — MachineLearningMastery. Walk-forward validation implementation patterns.
- [Interpretable Hypothesis-Driven Trading: Walk-Forward Validation Framework](https://arxiv.org/html/2512.12924v1) — 2025. Statistical power of walk-forward folds (540 folds for 80% power finding).
- [5 Critical Feature Engineering Mistakes That Kill Machine Learning Projects](https://www.kdnuggets.com/5-critical-feature-engineering-mistakes-that-kill-machine-learning-projects) — KDnuggets. Feature leakage patterns and prevention.
- [Selected Topics in Time Series Forecasting: Statistical Models vs. Machine Learning](https://pmc.ncbi.nlm.nih.gov/articles/PMC11941414/) — PMC, 2025. Model comparison on small financial time series.
- [Forecasting Time Series Subject to Multiple Structural Breaks](https://rady.ucsd.edu/_files/faculty-research/timmermann/time-series.pdf) — Timmermann. Regime change forecasting theory.
- [Avoiding Data Leakage in Timeseries 101](https://towardsdatascience.com/avoiding-data-leakage-in-timeseries-101-25ea13fcb15f/) — Towards Data Science. Practical leakage avoidance patterns.
- Autonomous ML Agents Research Report (project file: `Autonomous_ML_Agents_Research_Report.docx`) — project-specific landscape analysis.
- AIDE architecture (arXiv:2502.13138) — comparison baseline for AIDE's tree-search limitations on noisy metrics.

---

*Pitfalls research for: v2.0 Results-Driven Forecasting (time-series feature engineering, optuna, walk-forward validation, revenue forecasting, small-N regime)*
*Researched: 2026-03-14*
