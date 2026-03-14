# Technology Stack

**Project:** AutoML v2.0 — Results-Driven Forecasting additions
**Domain:** Hyperparameter search, time-series feature engineering, walk-forward validation, forecasting metrics
**Researched:** 2026-03-14
**Confidence:** MEDIUM-HIGH (WebSearch + official docs verified; exact latest minor versions confirmed via PyPI search results)

---

## Scope Note

This document covers ONLY the stack additions needed for v2.0. The v1.0 stack (scikit-learn, XGBoost, LightGBM, pandas, numpy, uv, subprocess git) is already validated and in production. Do not re-research or re-discuss what already works.

**Existing pyproject.toml dependencies (carry forward unchanged):**
```
scikit-learn>=1.5
pandas>=2.0
numpy>=2.0
xgboost
lightgbm
```

---

## New Additions: Core Technologies

### Hyperparameter Optimization

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| optuna | >=4.0,<5.0 | Bayesian hyperparameter search inside agent-written train.py | Current stable is 4.7.0 (Nov 2025). TPE sampler converges faster than grid/random search. Define-by-run API means the agent can write a search space as plain Python — no special syntax or decorators. Agent writes the objective function; optuna runs the trials. Integrates with XGBoost and LightGBM natively via optuna-integration. |

**Why Optuna over FLAML:** FLAML is a full AutoML system that picks algorithms AND hyperparameters autonomously. That conflicts with our architecture — Claude Code is the algorithm selector. Optuna is a pure hyperparameter optimizer: the agent defines the search space, optuna samples it efficiently. This preserves agent agency while making search faster than manual iteration.

**Why not FLAML:** FLAML's BlendSearch showed 2.52% average improvement vs Optuna's 1.96% on benchmarks, but FLAML takes over model selection — incompatible with our agent-driven multi-draft architecture where Claude picks the model family. Optuna is the right primitive here.

**Small-N regime note (20-80 rows):** With 20-80 training samples, overfitting via hyperparameter search is a real risk. Mitigate by: (1) using CV score (not holdout) as the Optuna objective, (2) keeping `n_trials` low (30-50 is enough — TPE needs only ~10 trials to beat random), (3) reducing `n_startup_trials` to 5-10 so TPE kicks in early (default is 20, which would use all trials in random mode for 30-trial budgets). Agent should write conservative search spaces with regularization-heavy ranges.

### Walk-Forward Temporal Validation

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| sklearn.model_selection.TimeSeriesSplit | (part of scikit-learn>=1.5, already installed) | Walk-forward cross-validation — no future data leakage | Already in the installed stack. Accepts `n_splits`, `gap`, `test_size`, `max_train_size`. The `gap` parameter (added in sklearn 0.24) inserts a buffer between train and test to prevent leakage from overlapping features. No new dependency needed. |

**Why not tscv (the standalone library):** `tscv.GapRollForward` offers `min_train_size` and `roll_size` parameters that sklearn's `TimeSeriesSplit` lacks, but those features are only valuable when you have enough data to make sliding windows meaningful. With 20-80 quarterly rows, you can configure sklearn's `TimeSeriesSplit` directly: `TimeSeriesSplit(n_splits=3, test_size=2, gap=1)` gives 3 folds with a 1-quarter gap — enough for temporal validation without an extra dependency.

**Walk-forward configuration for 20-80 quarterly rows:**
```python
# 20-40 rows: 3 folds, test_size=2 quarters (one holdout period)
TimeSeriesSplit(n_splits=3, test_size=2, gap=0)

# 40-80 rows: 4-5 folds, test_size=2-4 quarters
TimeSeriesSplit(n_splits=4, test_size=4, gap=1)
```
Keep `n_splits` low — with 20 rows and 5 splits, each training fold has only ~3 rows.

### Time-Series Feature Engineering

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| feature-engine | >=1.8,<2.0 | Lag features, rolling window features, expanding window features — sklearn-compatible transformers | Current version is 1.9.4 (2025). Provides `LagFeatures`, `WindowFeatures`, and `ExpandingWindowFeatures` as sklearn-compatible transformers that fit into `Pipeline` and work with `cross_val_score`. The agent can insert these into the feature engineering step of train.py without breaking the evaluate() contract in prepare.py. |

**Why feature-engine over building from scratch:** The agent can certainly write `df['lag_1'] = df['revenue'].shift(1)` by hand. But feature-engine transformers: (1) handle the fit/transform split correctly (no leakage), (2) integrate with sklearn's TimeSeriesSplit via Pipeline, (3) handle NaN rows from lagging without manual dropna logic. For 20-80 rows, the transformer overhead is negligible.

**Why not tsfresh:** tsfresh extracts hundreds of statistical features automatically, which is excellent for large time series but catastrophically bad for 20-80 rows. With 20 samples and 200 extracted features, you get extreme high-dimensionality — guaranteed overfitting. For small-N quarterly forecasting, hand-chosen or agent-chosen lag/rolling features (5-15 features max) are the right approach. Tsfresh is wrong for this use case.

**Why not sktime or darts:** Both are forecasting-first frameworks with native time-series model APIs (ARIMA, Prophet, etc.). This project uses tabular ML (XGBoost, LightGBM) in a supervised regression framing — treating forecasting as "predict y from engineered features of past y." Sktime and Darts would require a paradigm shift away from the existing pipeline. Feature-engine fits naturally into the current sklearn-compatible architecture.

---

## New Additions: Metrics

Forecasting metrics do not require new dependencies. All needed metrics are available in scikit-learn (already installed) or implementable as one-liners using numpy (already installed).

| Metric | Source | Notes |
|--------|--------|-------|
| MAE | `sklearn.metrics.mean_absolute_error` | Already in METRIC_MAP as `"mae"` |
| RMSE | `sklearn.metrics.root_mean_squared_error` (sklearn>=1.4) | Already in METRIC_MAP as `"rmse"` |
| MAPE | `sklearn.metrics.mean_absolute_percentage_error` | Added in sklearn 0.24. Available in current stack. Add to METRIC_MAP as `"mape"`. |
| SMAPE | Not in sklearn — implement with numpy | 3-line function: `np.mean(2 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred)))`. Add as custom scorer. |

**Add to prepare.py METRIC_MAP:**
```python
"mape": ("neg_mean_absolute_percentage_error", "maximize"),  # sklearn negates error metrics
"smape": ("neg_smape", "maximize"),  # custom scorer — see below
```

**SMAPE as custom sklearn scorer:**
```python
from sklearn.metrics import make_scorer
import numpy as np

def smape_score(y_true, y_pred):
    """Symmetric Mean Absolute Percentage Error (lower is better)."""
    return np.mean(2.0 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred)))

neg_smape_scorer = make_scorer(smape_score, greater_is_better=False)
```

**Small-N regime warning on percentage metrics:** MAPE and SMAPE are undefined or extreme when actual values are near zero. For revenue forecasting of real companies, this is rarely a problem (revenue is always positive). If near-zero actuals occur, fall back to MAE.

---

## Updated pyproject.toml

```toml
[project]
name = "automl"
version = "2.0.0"
description = "Autonomous ML research framework for traditional tabular ML"
requires-python = ">=3.11"
dependencies = [
    "scikit-learn>=1.5",
    "pandas>=2.0",
    "numpy>=2.0",
    "xgboost",
    "lightgbm",
    "optuna>=4.0,<5.0",
    "feature-engine>=1.8,<2.0",
]

[project.scripts]
automl = "automl.cli:main"

[dependency-groups]
dev = [
    "pytest",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/automl"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (e.g. scaffold + run train.py)",
]
```

---

## Installation Commands

```bash
# Add new dependencies (uv handles resolution)
uv add "optuna>=4.0,<5.0"
uv add "feature-engine>=1.8,<2.0"

# Verify install
uv run python -c "import optuna; print(optuna.__version__)"
uv run python -c "import feature_engine; print(feature_engine.__version__)"
```

---

## Integration Points with Existing Code

### prepare.py (frozen — minimal changes)

`prepare.py` is the frozen data pipeline. Changes must be additive and backward-compatible.

**Required additions to prepare.py:**
1. Add `"mape"` and `"smape"` to `METRIC_MAP` and `_REGRESSION_METRICS`
2. Register `neg_smape_scorer` with sklearn's scorer registry so it works with `cross_val_score`
3. Add `walk_forward_split()` function (wraps `TimeSeriesSplit`) so agent can call it from train.py

**New function signature for prepare.py:**
```python
def walk_forward_split(
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = 3,
    test_size: int = 2,
    gap: int = 0,
) -> sklearn.model_selection.TimeSeriesSplit:
    """Return a configured TimeSeriesSplit for temporal validation.

    Use instead of evaluate() when data has a time ordering.
    Caller is responsible for ordering X/y by time before splitting.
    """
```

### train_template.py (mutable — agent replaces this per experiment)

The agent rewrites train.py each experiment. The v2.0 train.py template should demonstrate:
1. Importing `walk_forward_split` from prepare (alongside existing imports)
2. Time-ordering data before splitting: `X = X.sort_values('period')` or similar
3. Using `LagFeatures` from feature-engine inside the sklearn pipeline
4. Running an Optuna study as the hyperparameter search mechanism

**Key constraint:** Optuna's `study.optimize()` call must complete within `TIME_BUDGET` seconds. The agent should write `study.optimize(objective, n_trials=30, timeout=TIME_BUDGET - 10)` to leave buffer for logging.

### drafts.py (minor change)

Add forecasting-specific algorithm families for the draft phase:
- `XGBoostForecaster`: XGBoost with lag features
- `LightGBMForecaster`: LightGBM with rolling mean features
- `RidgeForecaster`: Ridge regression (strong baseline for small N)
- `ElasticNetForecaster`: ElasticNet (regularized, good for small N)

Drop SVM from regression families (poor for time series with lag features due to feature scaling sensitivity).

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| HPO library | optuna | FLAML | FLAML does algorithm selection too — conflicts with agent-driven model choice. Optuna is a pure optimizer. |
| HPO library | optuna | hyperopt | Hyperopt has older API, less actively maintained. Optuna's TPE is slightly better and has more sampling algorithms. |
| Time-series features | feature-engine | tsfresh | tsfresh generates 100s of features — catastrophically overfit at 20-80 rows. Wrong tool for small-N. |
| Time-series features | feature-engine | manual pandas | Manual `df.shift()` works but loses sklearn Pipeline compatibility, risks train-test leakage in feature creation. feature-engine's fit/transform handles this correctly. |
| Time-series CV | sklearn TimeSeriesSplit | tscv GapRollForward | tscv has `min_train_size` which is useful at larger N, but with 20-80 rows, sklearn's TimeSeriesSplit with explicit `n_splits=3` and `test_size=2` is sufficient. Avoid the extra dependency. |
| Forecasting framework | tabular ML + feature engineering | sktime | sktime would require replacing the entire modeling paradigm. Keep tabular ML approach — it generalizes. |
| Forecasting framework | tabular ML + feature engineering | darts | Same issue as sktime — paradigm mismatch. Also heavyweight (neuralprophet, torch dependencies). |
| SMAPE implementation | numpy one-liner | ts-metrics library | Any library providing SMAPE is a 3-line numpy implementation wrapped in a package. Not worth the dependency. |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| tsfresh | Extracts 700+ features. At 20-80 rows, this is pure overfitting. Curse of dimensionality. | feature-engine with 5-15 manually chosen lag/rolling features |
| sktime | Full forecasting framework — replaces sklearn, not extends it. Massive paradigm shift. | sklearn TimeSeriesSplit + feature-engine |
| prophet / neuralprophet | Neural/curve-fitting models. Out of scope (traditional ML only per PROJECT.md). | XGBoost/LightGBM with lag features |
| statsmodels (ARIMA, SARIMA) | Statistical forecasting models, not tabular ML. Out of scope. | XGBoost/LightGBM with lag features |
| optuna-dashboard | Web UI for optimization runs. Adds complexity, zero value for autonomous CLI operation. | Read trial results from study object directly |
| optuna-integration | Adds LightGBMTunerCV etc. Those tools replace the agent's role. Only needed if you want optuna to run its own CV internally. The agent writes the CV loop and calls optuna for sampling. | optuna core only |
| mlforecast | End-to-end time series ML framework (nixtla). Competes with agent-written pipelines. | Compose primitives manually inside agent-written train.py |
| ray tune | Distributed HPO. Single machine project. Massive overhead for 30-trial search. | optuna |

---

## Stack Patterns by Variant

**If N < 30 quarterly rows (very small):**
- Reduce to `n_splits=2` in TimeSeriesSplit — you cannot spare more rows for validation
- Reduce Optuna `n_trials` to 20 — with 3-fold CV, each trial trains 3 models
- Prefer Ridge/ElasticNet over XGBoost — fewer hyperparameters, less overfitting risk
- Use MAE or RMSE (not MAPE) — percentage metrics are noisy at small N

**If N >= 60 quarterly rows (comfortable):**
- Use `n_splits=5` in TimeSeriesSplit — enough data per fold
- Optuna `n_trials=50` is reasonable
- XGBoost/LightGBM are competitive
- MAPE and SMAPE are reliable

**If target has zero or near-zero values:**
- Never use MAPE (undefined at zero) or SMAPE (degenerate at zero)
- Use MAE or RMSE
- Add a guard in prepare.py: warn if min(y) < 1% of mean(y)

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| optuna>=4.0 | Python 3.9-3.13 | Confirmed in optuna-integration docs (supports 3.9-3.13) |
| optuna>=4.0 | xgboost>=2.0 | Integration verified via optuna-examples repo |
| optuna>=4.0 | lightgbm>=4.0 | LightGBMTunerCV in optuna-integration 4.6.0 |
| feature-engine>=1.8 | scikit-learn>=1.3 | Tested; feature-engine follows sklearn's API contracts |
| feature-engine>=1.8 | pandas>=2.0 | Confirmed (feature-engine 1.8.3 released Jan 2025) |
| sklearn TimeSeriesSplit | Already installed | gap parameter available since sklearn 0.24 |

---

## Sources

- [Optuna 4.7.0 official docs](https://optuna.readthedocs.io/en/stable/) — current stable version confirmed HIGH confidence
- [Optuna PyPI page](https://pypi.org/project/optuna/) — version 4.6+ confirmed Nov 2025
- [sklearn TimeSeriesSplit docs](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) — gap parameter, n_splits, test_size parameters confirmed HIGH confidence
- [sklearn MAPE](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_percentage_error.html) — built-in since sklearn 0.24 HIGH confidence
- [feature-engine PyPI](https://pypi.org/project/feature-engine/) — version 1.9.4 current (Jan 2025) MEDIUM confidence
- [feature-engine LagFeatures docs](https://feature-engine.trainindata.com/en/1.8.x/api_doc/timeseries/forecasting/LagFeatures.html) — sklearn Pipeline compatibility confirmed MEDIUM confidence
- [tscv GapRollForward](https://tscv.readthedocs.io/en/latest/generated/tscv.GapRollForward.html) — considered and rejected for small-N regime
- [Optuna TPE n_startup_trials](https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.TPESampler.html) — default 20, confirmed via search MEDIUM confidence
- FLAML vs Optuna comparison — FLAML 2.52% vs Optuna 1.96% improvement over random search (FLAIRS conference paper, WebSearch verified LOW-MEDIUM confidence)

---

*Stack research for: AutoML v2.0 Results-Driven Forecasting*
*Researched: 2026-03-14*
