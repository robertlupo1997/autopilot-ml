# Architecture Patterns

**Domain:** Autonomous ML Framework — v2.0 Results-Driven Forecasting
**Researched:** 2026-03-14
**Confidence:** HIGH (based on direct codebase reading + verified research)

---

## Context: What Is Changing in v2.0

v1.0 architecture: `prepare.py` (frozen) owns everything from raw CSV to preprocessed numpy arrays. `train.py` (mutable) owns only model selection and hyperparameters.

v2.0 target: quarterly revenue forecasting from 20-80 rows of historical financials. Three things break the v1.0 architecture:

1. Random CV in `evaluate()` violates temporal ordering — using future quarters to predict past ones
2. Feature engineering (lags, rolling stats, growth rates) must happen between raw load and model training — it is too domain-specific to freeze
3. Forecasting metrics (MAPE, MAE) are not standard sklearn scorers and require custom implementation

The frozen/mutable boundary must shift. This document defines exactly how.

---

## System Overview: v2.0 Architecture

```
                         Human
                           |
                    program.md (domain context,
                    feature hints, leakage warnings)
                           |
                    Claude Code (Orchestrator)
                      /         \
              [FROZEN]          [MUTABLE]
              prepare.py         train.py
              forecast.py        (agent edits)
                |
          [RAW DATAFRAME]
          Not preprocessed arrays.
          Time index preserved.
          Temporal split enforced.
                |
           [EXECUTION]
           uv run train.py > run.log 2>&1
           grep "^metric_value:" run.log
```

The fundamental shift: `prepare.py` now hands `train.py` a **raw DataFrame with time index intact**, not preprocessed arrays. The agent engineers features inside `train.py`. The evaluation function moves to a new frozen module `forecast.py` which uses walk-forward validation instead of random CV.

---

## Component Boundaries

| Component | Responsibility | v1.0 | v2.0 Change |
|-----------|----------------|-------|-------------|
| `prepare.py` | Load CSV, temporal split, data summary, baselines | Frozen | Keep frozen, but radically simplified — strip `build_preprocessor`, `evaluate`, `split_data` |
| `forecast.py` | Walk-forward validation, forecasting metrics, forecasting baselines | Does not exist | NEW frozen module |
| `train.py` | Feature engineering + modeling + Optuna search | Model only (mutable) | Expanded mutable zone |
| `CLAUDE.md` | Agent loop instructions | One protocol | Update to describe v2 mutable zone |
| `program.md` | Domain expertise | Generic | Add forecasting-specific hints section |

---

## What Stays Frozen vs. What Becomes Mutable

### Frozen (agent cannot edit)

**`prepare.py` — simplified to three responsibilities:**

1. `load_data(csv_path, target_col, date_col)` — reads CSV, parses date column, returns raw `pd.DataFrame` with datetime index. Returns the full DataFrame; no split yet.
2. `temporal_split(df, target_col, holdout_fraction=0.15)` — splits by time, never randomly. Last N rows are holdout. Returns `(df_train, df_holdout, y_train, y_holdout)`.
3. `get_data_summary(df, target_col)` — row count, date range, missing values, target stats.

Remove from `prepare.py`: `build_preprocessor`, `evaluate`, `get_baselines`, `split_data`, `validate_metric`, `METRIC_MAP`. These either move to `forecast.py` or become the agent's responsibility.

**`forecast.py` — new frozen module with three responsibilities:**

1. `walk_forward_evaluate(model_fn, df_train, y_train, metric, n_splits)` — walk-forward cross-validation using `sklearn.model_selection.TimeSeriesSplit`. `model_fn` is a callable `(X_train_fold, y_train_fold) -> model` that the agent provides. The frozen module calls it, applies to test fold, computes metric. Agent cannot touch the split or metric logic.
2. `compute_metric(y_true, y_pred, metric_name)` — computes MAPE, MAE, RMSE, SMAPE. Returns a float where higher is always better (negated internally for error metrics, consistent with sklearn convention).
3. `get_forecasting_baselines(df_train, y_train, metric)` — computes naive forecast (last value), seasonal naive (same quarter last year), and exponential smoothing (statsmodels `SimpleExpSmoothing`) baselines using the same walk-forward evaluation. Provides the agent a meaningful reference point.

**Hook system** — `guard-frozen.sh` expands its deny list from `prepare.py` only to `prepare.py forecast.py`.

### Mutable (agent edits freely)

**`train.py` — the agent's full workspace, which in v2 must do:**

1. Feature engineering: create lag features, rolling statistics, growth rates, quarter dummies, trend features — all from raw `df_train`
2. Preprocessing: scaling, imputation — fit on train fold only (agent is responsible for avoiding leakage)
3. Model definition with search space
4. Optuna hyperparameter search: `create_study()` calls `walk_forward_evaluate()` from `forecast.py` inside the objective function
5. Final model training on all `df_train` data with best params
6. Print structured output in the same format as v1 (the runner and parse logic do not change)

The agent writes `train.py` from scratch each iteration. There is no separate `features.py` — see the rationale below.

---

## Question 1: Feature Engineering — One File or Two?

**Decision: Keep feature engineering inside `train.py`. Do not create a separate `features.py`.**

Rationale:

- The v1 constraint "agent edits exactly one file" is the core of the architecture. It keeps changes attributable: every git diff shows exactly what changed and why the metric moved.
- If the agent edits both `train.py` and `features.py` per iteration, each commit involves two files. The keep/revert protocol (`git reset --hard HEAD~1`) still works, but the agent's reasoning about what changed becomes murkier.
- Feature engineering and modeling are tightly coupled for forecasting: the features the agent creates inform the model's assumptions (e.g., XGBoost handles raw lags differently than Ridge which needs scale-normalized growth rates). Separating them creates an artificial boundary that the agent would constantly fight.
- The "single mutable file" constraint comes from autoresearch, which found it essential for clean attribution. AIDE, despite being more complex, also enforces single-file experiments.

**What train.py structure looks like in v2:**

```python
# --- Configuration (agent edits these) ---
CSV_PATH = "data.csv"
TARGET_COLUMN = "revenue"
DATE_COLUMN = "quarter"
METRIC = "mape"
TIME_BUDGET = 120  # longer for Optuna

# --- Load raw data (frozen) ---
from prepare import load_data, temporal_split
from forecast import walk_forward_evaluate, compute_metric

df = load_data(CSV_PATH, TARGET_COLUMN, DATE_COLUMN)
df_train, df_holdout, y_train, y_holdout = temporal_split(df, TARGET_COLUMN)

# --- Feature engineering (agent edits this section) ---
def engineer_features(df):
    X = pd.DataFrame(index=df.index)
    X["lag_1"] = df[TARGET_COLUMN].shift(1)
    X["lag_4"] = df[TARGET_COLUMN].shift(4)       # same quarter last year
    X["rolling_mean_4"] = df[TARGET_COLUMN].shift(1).rolling(4).mean()
    X["yoy_growth"] = df[TARGET_COLUMN].pct_change(4)
    X["quarter"] = df.index.quarter
    return X.dropna()

# --- Model + Optuna search (agent edits this section) ---
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

def model_fn(X_train_fold, y_train_fold, params):
    from xgboost import XGBRegressor
    model = XGBRegressor(**params)
    model.fit(X_train_fold, y_train_fold)
    return model

def objective(trial):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 50, 300),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "max_depth": trial.suggest_int("max_depth", 2, 6),
    }
    X_train_fe = engineer_features(df_train)
    y_aligned = y_train.loc[X_train_fe.index]
    return walk_forward_evaluate(
        lambda Xtr, ytr: model_fn(Xtr, ytr, params),
        X_train_fe, y_aligned, METRIC, n_splits=3
    )

study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=30, timeout=TIME_BUDGET * 0.6)
best_params = study.best_params

# --- Final model on full train ---
X_fe = engineer_features(df_train)
y_aligned = y_train.loc[X_fe.index]
final_model = model_fn(X_fe, y_aligned, best_params)

# --- Holdout evaluation ---
X_holdout_fe = engineer_features(
    pd.concat([df_train, df_holdout])  # need history for lags
).loc[df_holdout.index]
y_pred = final_model.predict(X_holdout_fe)
score = compute_metric(y_holdout.loc[X_holdout_fe.index], y_pred, METRIC)

# --- Print structured output (unchanged from v1) ---
print(f"metric_name:  {METRIC}")
print(f"metric_value: {score:.6f}")
...
```

The agent writes this entire file. Feature engineering and model are co-located because they are co-designed.

---

## Question 2: Optuna Integration — Where Does It Live?

**Decision: Optuna runs inside `train.py`. No separate `optimize.py`.**

Rationale:
- Same single-file constraint as above. The agent defines the search space in `train.py` alongside the model that uses it.
- The agent calls `forecast.walk_forward_evaluate()` (frozen) as the objective. This is the critical integration point: the agent supplies the `model_fn`, the frozen module supplies the validation protocol.
- This prevents a key risk: the agent writing its own validation loop inside Optuna's objective and inadvertently leaking future data.

**Optuna configuration for small-N regime (20-80 rows):**

The small-N regime constrains Optuna significantly. With 20-80 quarterly observations:
- `n_splits=3` for TimeSeriesSplit is the maximum that leaves enough training data per fold. With 60 rows and 3 splits, the first fold trains on ~30 rows and tests on ~10 rows.
- `n_trials=30` is appropriate. With 30 seconds per trial and a 120-second budget, this fits in the time budget. More trials do not help when each trial's signal is already noisy at this sample size.
- Use `TPESampler` (Optuna default) — it is well-calibrated for small trial counts. Do not use CMA-ES or NSGA-II which need 100+ trials to outperform random search.
- Search spaces must be narrow: 2-3 hyperparameters, modest ranges. Broad search spaces with small N and few trials yield random walk behavior.

**`forecast.py` interface for Optuna:**

```python
def walk_forward_evaluate(
    model_fn: Callable[[pd.DataFrame, pd.Series], Any],
    X: pd.DataFrame,
    y: pd.Series,
    metric: str,
    n_splits: int = 3,
) -> float:
    """Walk-forward cross-validation. Returns mean score (higher=better).

    model_fn must accept (X_train_fold, y_train_fold) and return a fitted
    model with a .predict(X_test_fold) method.

    Uses sklearn.model_selection.TimeSeriesSplit (expanding window).
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    scores = []
    for train_idx, test_idx in tscv.split(X):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
        model = model_fn(X_tr, y_tr)
        y_pred = model.predict(X_te)
        scores.append(compute_metric(y_te, y_pred, metric))
    return float(np.mean(scores))
```

The agent passes a lambda or closure into `model_fn`. The frozen module controls the split.

---

## Question 3: Walk-Forward Validation — How Does It Replace `evaluate()`?

**Decision: Replace `prepare.py`'s `evaluate()` (random KFold/StratifiedKFold) with `forecast.py`'s `walk_forward_evaluate()` (TimeSeriesSplit). The agent never calls the old `evaluate()`.**

v1.0 `evaluate()` uses `KFold(shuffle=True)` — this is categorically wrong for time series. Shuffling lets the model train on Q3-2020 while predicting Q1-2019, i.e., the model sees the future during training. For small datasets (20-80 rows), this inflates apparent performance significantly.

**Replacement architecture:**

```
v1.0: prepare.evaluate(model, X_processed, y, scoring, task)
       └── KFold(shuffle=True, n_splits=5)

v2.0: forecast.walk_forward_evaluate(model_fn, X_fe, y_aligned, metric, n_splits=3)
       └── TimeSeriesSplit(n_splits=3)  [expanding window, no shuffle]
```

**TimeSeriesSplit behavior at small N:**

With 60 quarterly rows, 15% holdout leaves 51 rows for training. With `n_splits=3`:
- Fold 1: train on rows 1-26, test on rows 27-38 (~12 rows test)
- Fold 2: train on rows 1-38, test on rows 39-51 (~12 rows test)
- Fold 3: implicit in the 3-split structure (varies by implementation)

This means the earliest fold trains on only ~26 rows. Models must be regularized enough not to overfit this. The agent should be told in `program.md` to prefer regularized models and small search spaces.

**Holdout policy:** The final 15% of rows (by time) are held out before any agent interaction begins — computed by `prepare.temporal_split()` during scaffolding. The agent never sees these rows during experimentation. Final holdout evaluation is printed in `train.py`'s structured output and logged to `results.tsv`.

---

## Question 4: Forecasting-Specific Baselines

**Decision: Implement three baselines in `forecast.py`, computed at scaffold time and printed in `program.md`.**

The three baselines, in order of increasing sophistication:

| Baseline | Implementation | Purpose |
|----------|----------------|---------|
| Naive forecast | `y_pred[t] = y_true[t-1]` | Floor: must beat last quarter |
| Seasonal naive | `y_pred[t] = y_true[t-4]` | Strong floor: same quarter last year |
| Exponential smoothing | `statsmodels.tsa.holtwinters.SimpleExpSmoothing` | Reasonable statistical baseline |

**Why these three:** For quarterly revenue, seasonal naive is often the hardest to beat — it captures the annual cycle. If an ML model cannot beat seasonal naive, the features are wrong or the model is overfit. Any ML system that beats all three is earning its complexity.

**Implementation in `forecast.py`:**

```python
def get_forecasting_baselines(
    y_train: pd.Series,
    metric: str,
    n_splits: int = 3,
) -> dict[str, dict[str, float]]:
    """Compute naive, seasonal naive, and ETS baselines via walk-forward CV.

    Returns {baseline_name: {"score": float, "std": float}}.
    """
    results = {}
    tscv = TimeSeriesSplit(n_splits=n_splits)

    for name, pred_fn in [
        ("naive", _naive_pred),
        ("seasonal_naive", _seasonal_naive_pred),
        ("exp_smoothing", _exp_smoothing_pred),
    ]:
        fold_scores = []
        for train_idx, test_idx in tscv.split(y_train):
            y_tr = y_train.iloc[train_idx]
            y_te = y_train.iloc[test_idx]
            y_pred = pred_fn(y_tr, len(y_te))
            fold_scores.append(compute_metric(y_te, y_pred, metric))
        results[name] = {
            "score": float(np.mean(fold_scores)),
            "std": float(np.std(fold_scores)),
        }
    return results
```

`statsmodels` is a new dependency. It is lightweight and CPU-only, consistent with the existing constraint.

---

## Question 5: Frozen vs. Mutable Boundary — Complete Specification

### Frozen Files (agent cannot edit)

```
prepare.py      — load_data, temporal_split, get_data_summary
forecast.py     — walk_forward_evaluate, compute_metric, get_forecasting_baselines
                  METRIC_MAP (extended with mape, smape, mae, rmse)
                  validate_metric (updated for forecasting metrics)
```

### Mutable Files (agent edits)

```
train.py        — EVERYTHING the agent experiments with:
                  - Feature engineering functions
                  - Preprocessing (scaler, imputer) — fit on train only
                  - Model selection
                  - Optuna search space and study configuration
                  - Final model training
                  - Holdout evaluation (calls frozen compute_metric)
                  - Structured output printing (format unchanged)
```

### Hook System Update

`guard-frozen.sh` deny list expands from `prepare.py` to `prepare.py forecast.py`:

```bash
FROZEN_FILES="prepare.py forecast.py"
```

Both `settings.json` deny rules and the shell hook must be updated:

```json
"deny": [
    "Edit(prepare.py)",
    "Write(prepare.py)",
    "Edit(forecast.py)",
    "Write(forecast.py)"
]
```

### What Completely Goes Away

- `prepare.py`: `build_preprocessor`, `evaluate`, `get_baselines`, `split_data`, `validate_metric`, `METRIC_MAP` — these either move to `forecast.py` or become the agent's responsibility
- The agent no longer receives preprocessed numpy arrays. It receives a raw `pd.DataFrame`.
- `train.py` no longer calls `build_preprocessor()`. The agent handles all preprocessing.

### What the Agent Receives at Startup

When `train.py` is first scaffolded, the configuration section provides:

```python
CSV_PATH = "revenue.csv"
TARGET_COLUMN = "revenue"
DATE_COLUMN = "quarter"    # NEW: explicit date column
METRIC = "mape"
TIME_BUDGET = 120
```

And `program.md` tells the agent:
- The date range (e.g., "Q1 2010 to Q4 2024, 60 quarters")
- The forecasting baselines and their scores (from `get_forecasting_baselines`)
- Which quarter to forecast (horizon = 1 quarter ahead for v2)
- Feature engineering hints specific to quarterly revenue

---

## New Component: `forecast.py` — Full Specification

```
src/automl/forecast.py

FORE-01: METRIC_MAP — forecasting metrics (mape, smape, mae, rmse)
FORE-02: validate_metric — same contract as prepare.validate_metric
FORE-03: compute_metric — MAPE, SMAPE, MAE, RMSE, all return higher-is-better float
FORE-04: walk_forward_evaluate — TimeSeriesSplit-based CV, accepts model_fn callable
FORE-05: get_forecasting_baselines — naive, seasonal naive, exp smoothing
```

**MAPE implementation note:** `sklearn.metrics.mean_absolute_percentage_error` exists (confirmed in sklearn 1.8.0 docs) but returns a raw ratio (0.5 = 50% MAPE). The frozen module negates it so higher is better: `score = -sklearn_mape(y_true, y_pred)`. SMAPE is not in sklearn; implement manually.

**SMAPE formula (for near-zero revenue avoidance):**
```python
def _smape(y_true, y_pred):
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2
    # Avoid division by zero when both are zero
    mask = denom > 0
    return -np.mean(np.abs(y_true[mask] - y_pred[mask]) / denom[mask])
```

**Zero-revenue protection:** Quarterly revenue can be near-zero for early-stage companies. MAPE blows up when `y_true` approaches 0. The frozen module should detect this during baseline computation and warn in `program.md`. Prefer SMAPE or MAE for near-zero targets.

---

## Data Flow: v2.0 End-to-End

```
SCAFFOLD TIME (once, run by user):

  user: uv run automl revenue.csv revenue quarter mape
          |
          v
  cli.py:
    X, y, task = load_data(csv_path, target_col, date_col)   # from new prepare.py
    df_train, df_holdout, y_train, y_holdout = temporal_split(df, target_col)
    baselines = get_forecasting_baselines(y_train, metric)
    summary = get_data_summary(df, target_col)
    -- scaffold experiment directory --
    -- copy prepare.py (frozen) --
    -- copy forecast.py (frozen) --        # NEW
    -- generate train.py from template --
    -- render program.md with baselines --
    -- render CLAUDE.md with v2 protocol --
    -- write .claude/settings.json with expanded deny list --
    -- write guard-frozen.sh with expanded FROZEN_FILES --

AGENT TIME (indefinitely, run by Claude Code):

  CLAUDE.md instructs agent to:
    Phase 1 (multi-draft):
      - Try 3-5 draft train.py variants (different algorithms + feature sets)
      - Each draft calls walk_forward_evaluate() from forecast.py
      - Select best draft
    Phase 2 (iterate):
      - Read program.md for feature hints and baseline scores
      - Edit train.py (feature engineering + Optuna + model)
      - git commit
      - uv run train.py > run.log 2>&1
      - grep "^metric_value:" run.log
      - keep if > best, revert if not
```

---

## Scaffold Changes: What `scaffold.py` Must Do Differently

`scaffold.py` currently:
1. Copies `prepare.py` (byte-identical from installed source)
2. Generates `train.py` from `train_template.py` with string substitution
3. Builds preprocessor and computes baselines for `program.md`

v2 changes:
1. Copy `prepare.py` (simplified version) — same mechanism
2. Copy `forecast.py` (new frozen module) — same mechanism as prepare.py
3. Generate `train.py` from new `train_template_forecast.py` — adds `DATE_COLUMN` config
4. Compute forecasting baselines via `forecast.get_forecasting_baselines()` instead of `prepare.get_baselines()`
5. Add `date_column` parameter to `scaffold_experiment()` signature
6. Expand `_dot_claude_settings()` deny list
7. Expand `_guard_frozen_hook_content()` frozen file list
8. Add `statsmodels` to `pyproject.toml` dependencies
9. Add `optuna` to `pyproject.toml` dependencies

The `render_program_md()` template call needs a new `date_range` and `baselines` format section for forecasting context.

---

## Template Changes: CLAUDE.md and program.md

### CLAUDE.md updates for v2

The existing CLAUDE.md says: "train.py is the ONLY mutable file. All your changes go here."

This remains true in v2, but the scope of what goes in `train.py` expands. The CLAUDE.md must:
- Explain that the agent now engineers features (not just selects models)
- Warn explicitly about temporal leakage: "fit scalers and imputers only on `X_train_fold`, never on the full dataset"
- Explain Optuna integration: "use `walk_forward_evaluate()` from `forecast.py` as your Optuna objective"
- Add forecasting-specific stagnation recovery: "if stuck, try different lag combinations, not just different model hyperparameters"
- Update the forbidden file list: "NEVER modify `prepare.py` or `forecast.py`"

### program.md updates for v2

The template gains a forecasting-specific section:

```
## Forecasting Context

- **Date range:** {date_range}
- **Frequency:** Quarterly
- **Horizon:** 1 quarter ahead
- **Minimum training size:** {min_train_size} quarters (earliest walk-forward fold)

## Baselines (walk-forward CV, n_splits=3)

{baselines}

Beat seasonal_naive first. Beat exp_smoothing to be production-ready.

## Feature Engineering Hints

- **Lag features:** lag_1, lag_2, lag_4 (same quarter last year)
- **Rolling stats:** rolling mean/std over 2, 4, 8 quarters (shift by 1 before rolling)
- **Growth rates:** QoQ growth (pct_change(1)), YoY growth (pct_change(4))
- **Calendar:** quarter of year (1-4), fiscal year
- **Leakage warning:** ALWAYS shift by at least 1 before computing rolling features.
  X["rolling_mean_4"] = df[target].shift(1).rolling(4).mean()  # CORRECT
  X["rolling_mean_4"] = df[target].rolling(4).mean()           # LEAKS
```

---

## Recommended Architecture: Experiment Directory Structure (v2)

```
experiment-revenue/
  prepare.py             # FROZEN: load_data, temporal_split, get_data_summary
  forecast.py            # FROZEN: walk_forward_evaluate, compute_metric, baselines
  train.py               # MUTABLE: features + model + Optuna (agent edits)
  revenue.csv            # Raw data (immutable)
  program.md             # Domain context + baselines + feature hints
  CLAUDE.md              # Agent loop protocol (updated for v2)
  results.tsv            # Experiment log (untracked)
  run.log                # Last run output (untracked)
  pyproject.toml         # scikit-learn, xgboost, lightgbm, optuna, statsmodels
  .gitignore
  .claude/
    settings.json        # deny list: prepare.py, forecast.py
    hooks/
      guard-frozen.sh    # FROZEN_FILES="prepare.py forecast.py"
```

---

## Patterns to Follow

### Pattern 1: Callable model_fn Interface

The interface between mutable `train.py` and frozen `forecast.py` is a callable:

```python
model_fn: Callable[[pd.DataFrame, pd.Series], Any]
```

The agent wraps its model in a lambda or closure and passes it to `walk_forward_evaluate()`. The frozen module calls it with fold data. This keeps the split protocol frozen while letting the agent define any model it wants.

**Why callable over sklearn estimator:** Sklearn's cross_val_score requires unfitted estimators. But the agent may want to do preprocessing inside the fit (e.g., fit a StandardScaler on each fold's training data separately). A callable gives the agent full control of what happens inside each fold without exposing the fold indices.

### Pattern 2: Feature Engineering With Temporal Safety

The agent must compute features without touching future data. The rule:

```
Any rolling or lag feature must shift by >= forecast horizon before aggregating.
Forecast horizon = 1 quarter = 1 row.
```

This is an agent protocol rule (in CLAUDE.md and program.md), not an enforced constraint. Enforcement would require AST analysis of train.py, which is out of scope for v2.

### Pattern 3: Optuna Inside Time Budget

Optuna's `study.optimize(n_trials=N, timeout=seconds)` respects both limits. The agent should use timeout to cap Optuna at ~60% of `TIME_BUDGET`, leaving room for final model fitting and holdout evaluation:

```python
study.optimize(objective, n_trials=50, timeout=TIME_BUDGET * 0.6)
```

### Pattern 4: Expanding Window, Not Rolling Window

Use `TimeSeriesSplit` (expanding window) not a rolling window for quarterly revenue. With only 20-80 rows, a rolling window throws away early data. Expanding window uses all available history in each fold, which is the right choice when data is scarce.

### Pattern 5: Minimal Optuna for Draft Phase

During multi-draft (Phase 1), agents should NOT run full Optuna — just evaluate default hyperparameters quickly to identify the best algorithm family. Save Optuna for Phase 2 iteration. Otherwise, the draft phase takes too long (30 trials x 5 algorithms = 150 Optuna trials before the loop even starts).

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Random Shuffle in Validation

**What people do:** Use `KFold(shuffle=True)` or `train_test_split(shuffle=True)` for time series.
**Why it's wrong:** Future quarters leak into training. Validation scores are inflated. The model appears to generalize but doesn't. The v1.0 `evaluate()` function does this. Do not carry it into v2.
**Instead:** `TimeSeriesSplit(n_splits=3)` in `forecast.walk_forward_evaluate()`.

### Anti-Pattern 2: Feature Leakage via Rolling Stats

**What people do:** `df["rolling_mean_4"] = df["revenue"].rolling(4).mean()`. This includes the current row's value in the mean for that row.
**Why it's wrong:** At prediction time, you don't have the current row's target value. The feature is constructed with future information.
**Instead:** Always shift before rolling: `df["revenue"].shift(1).rolling(4).mean()`.

### Anti-Pattern 3: Fitting Preprocessors on Full Train Set Before CV

**What people do:** Fit a `StandardScaler` on all of `df_train` before passing folds to `walk_forward_evaluate()`.
**Why it's wrong:** The scaler has seen future fold data, leaking distribution information across the temporal boundary.
**Instead:** Fit scaler inside `model_fn`, on `X_train_fold` only. Apply transform to `X_test_fold`.

### Anti-Pattern 4: Too Many Optuna Trials for Small N

**What people do:** `study.optimize(objective, n_trials=500)` with 60 data points.
**Why it's wrong:** Each trial evaluates the same noisy validation signal. With 60 rows and 3 folds, each fold has ~10 test points. MAPE on 10 points is highly variable. 500 trials will overfit the hyperparameter search to noise.
**Instead:** 20-50 trials with narrow search spaces. Wider search spaces need more trials to explore, but with noisy signal, more trials just find noise minima.

### Anti-Pattern 5: Separate features.py

**What people do:** Create a separate `features.py` mutable file so feature engineering is "organized."
**Why it's wrong:** Breaks the single-mutable-file constraint. Complicates the keep/revert protocol. The agent can no longer attribute metric changes to a single atomic edit.
**Instead:** Feature engineering functions live in `train.py`. A well-structured `engineer_features()` function is readable enough.

---

## Integration Points

### Internal Module Boundaries

| Boundary | v1.0 | v2.0 |
|----------|-------|-------|
| `scaffold.py` → `prepare.py` | Calls `build_preprocessor`, `get_baselines`, `load_data` | Calls `load_data`, `temporal_split`, `get_data_summary` only |
| `scaffold.py` → `forecast.py` | Does not exist | Calls `get_forecasting_baselines`, `validate_metric` |
| `train.py` → `prepare.py` | Calls `load_data`, `build_preprocessor`, `evaluate`, `validate_metric` | Calls `load_data`, `temporal_split` only |
| `train.py` → `forecast.py` | Does not exist | Calls `walk_forward_evaluate`, `compute_metric` |
| `runner.py` → `train.py` | Subprocess, parses structured output | Unchanged — same output format |
| `loop_helpers.py` | Keep/revert decisions | Unchanged — all metrics still higher-is-better |

### External Dependencies (New)

| Library | Version | Use | Why |
|---------|---------|-----|-----|
| `optuna` | >=3.0 | Hyperparameter optimization in `train.py` | TPE sampler, timeout support, clean API |
| `statsmodels` | >=0.14 | Exponential smoothing baseline in `forecast.py` | `SimpleExpSmoothing` for ETS baseline |

Both are CPU-only and fast for small datasets. No GPU, no distributed compute.

---

## Build Order: v2.0 Implementation Phases

Dependencies determine order. Each layer builds on the previous.

### Layer 1: New Frozen Module (no dependencies)

**Build first: `src/automl/forecast.py`**

- `METRIC_MAP` (forecasting metrics: mape, smape, mae, rmse)
- `validate_metric()` — updated for forecasting metrics
- `compute_metric()` — MAPE, SMAPE, MAE, RMSE, all higher-is-better
- `walk_forward_evaluate()` — TimeSeriesSplit, callable model_fn interface
- `get_forecasting_baselines()` — naive, seasonal naive, exp smoothing

Tests: unit tests for each function. Verify walk_forward_evaluate rejects shuffle. Verify compute_metric returns higher-is-better for all metrics. Verify baselines compute correctly on synthetic quarterly data.

**Simultaneously: simplify `src/automl/prepare.py`**

- Keep: `load_data()` — update signature to accept `date_col`, parse datetime index
- Add: `temporal_split()` — time-ordered split, no shuffle
- Keep: `get_data_summary()` — update to include date range
- Remove: `build_preprocessor`, `evaluate`, `get_baselines`, `split_data`, `validate_metric`, `METRIC_MAP`

Tests: verify existing test suite still passes for functions kept. Add tests for `temporal_split` — confirm test set is always later than train set. Confirm `load_data` with `date_col=None` still works for non-time-series use (backward compatibility if needed).

### Layer 2: New Template (depends on Layer 1)

**Build: `src/automl/train_template_forecast.py`**

The v2 equivalent of `train_template.py`. Contains:
- `DATE_COLUMN` config constant
- `load_data` + `temporal_split` from `prepare`
- `walk_forward_evaluate` + `compute_metric` from `forecast`
- Stub `engineer_features()` function (agent fills this out)
- Stub Optuna study (agent fills in search space)
- Final model training + holdout evaluation + structured output

This is what the agent starts with for forecasting experiments.

### Layer 3: Scaffold Updates (depends on Layers 1-2)

**Modify: `src/automl/scaffold.py`**

- Add `date_column` parameter to `scaffold_experiment()`
- Add `mode` parameter: `"classification" | "regression" | "forecast"` (or detect automatically)
- Copy `forecast.py` into experiment directory (same mechanism as prepare.py)
- Replace `build_preprocessor` + `get_baselines` calls with `get_forecasting_baselines` call when mode is forecast
- Expand `_dot_claude_settings()` deny list
- Expand `_guard_frozen_hook_content()` frozen file list
- Use `train_template_forecast.py` instead of `train_template.py` when mode is forecast
- Add `statsmodels` and `optuna` to `_pyproject_content()`

### Layer 4: Template Updates (depends on Layer 3)

**Modify: `src/automl/templates/program.md.tmpl`**

Add forecasting-specific section (date range, baselines format, feature hints, leakage warnings). Use `{mode}` conditional or create `program.md.forecast.tmpl` as a separate template.

**Modify: `src/automl/templates/claude.md.tmpl`**

Add v2 mutable zone description. Add leakage warnings. Update forbidden file list. Add Optuna protocol. Add forecasting stagnation recovery hints.

### Layer 5: CLI Update (depends on Layer 3)

**Modify: `src/automl/cli.py`**

Add `--date-column` flag. Pass through to `scaffold_experiment()`. The CLI auto-detects forecast mode when `date_column` is provided.

### Layer 6: Tests (depends on Layers 1-5)

- Unit tests for `forecast.py` (all 5 functions)
- Updated unit tests for `prepare.py` (new `temporal_split`, updated `load_data`)
- Updated scaffold tests (new parameters, new deny list, forecast directory structure)
- Integration test: scaffold a synthetic 60-row quarterly dataset, run one iteration of `train.py`, confirm metric parses correctly

---

## Small-N Regime: Design Constraints

The 20-80 row target creates specific constraints the architecture must respect:

| Constraint | Implication |
|------------|-------------|
| 20 rows minimum | With 15% holdout, only 17 rows for training. `n_splits=2` maximum. Agent should detect this and warn. |
| 80 rows typical | With 15% holdout, 68 rows for training. `n_splits=3` is safe. |
| Lag features consume rows | `lag_4` (4-quarter lag) loses the first 4 rows. With 20 rows total, this leaves 16. With 80 rows, 76. The agent must check that enough rows remain after feature engineering. |
| Noisy CV signal | With 10-15 rows per test fold, MAPE on a single fold is very noisy. Walk-forward mean across 3 folds reduces noise but does not eliminate it. The agent should not over-optimize Optuna. |
| Few hyperparameter trials | 30 trials is the practical maximum before Optuna's overhead exceeds signal. |

**Minimum viable data check:** Add to `scaffold_experiment()`:

```python
if len(df_train) < 20:
    warnings.warn(
        f"Training set has only {len(df_train)} rows after holdout. "
        "Walk-forward validation with n_splits=3 may not be reliable. "
        "Consider reducing holdout_fraction or n_splits."
    )
```

---

## Scalability Considerations

This system is intentionally not designed for scale. The target is a single financial analyst running 200-500 experiments overnight on one laptop.

| Concern | Implication for v2 |
|---------|---------------------|
| Experiment time per run | Optuna + walk-forward adds overhead. Expect 60-180s per experiment (up from ~30s in v1). Overnight run yields ~200-400 experiments instead of ~1000. |
| Context window | `train.py` in v2 is longer (~80-120 lines vs ~60 lines in v1). Still well within Claude's context budget. |
| Git history | Same as v1. No concern. |
| Swarm compatibility | Swarm (Phase 10) works unchanged. Each worktree contains its own `prepare.py`, `forecast.py`, `train.py`. Scoreboard protocol unchanged. |

---

## Sources

- `src/automl/prepare.py` — direct reading, HIGH confidence
- `src/automl/train_template.py` — direct reading, HIGH confidence
- `src/automl/scaffold.py` — direct reading, HIGH confidence
- `src/automl/templates/claude.md.tmpl` — direct reading, HIGH confidence
- `.planning/research/multi-agent-swarm-research.md` — direct reading, HIGH confidence
- sklearn TimeSeriesSplit docs (v1.8.0): [https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) — HIGH confidence
- sklearn MAPE docs: [https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_percentage_error.html](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_percentage_error.html) — HIGH confidence
- statsmodels exponential smoothing: [https://www.statsmodels.org/dev/examples/notebooks/generated/exponential_smoothing.html](https://www.statsmodels.org/dev/examples/notebooks/generated/exponential_smoothing.html) — HIGH confidence
- Optuna framework: [https://optuna.org/](https://optuna.org/) — HIGH confidence
- Walk-forward + Optuna pattern: arXiv:2601.08896v1 (XGBoost forecasting with walk-forward) — MEDIUM confidence
- Small-N Optuna trial recommendations: training data synthesis from Optuna docs examples (n_trials=10-50 for small problems) — MEDIUM confidence

---

*Architecture research for: v2.0 Results-Driven Forecasting*
*Researched: 2026-03-14*
