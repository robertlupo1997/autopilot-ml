# Phase 12: Forecast Template and Mutable Zone 2 - Research

**Researched:** 2026-03-14
**Domain:** Forecasting train template, lag/rolling feature engineering, Optuna hyperparameter optimization, frozen-file guard hook
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BASE-03b | Agent must beat both baselines to "keep" an experiment; failing to beat naive = auto-revert | Enforcement goes in `CLAUDE.md` protocol as numbered rule — `loop_helpers.should_keep()` signature is `(new_score, best_score)` only; dual-baseline gate must be documented as agent behavior, not code |
| FEAT-01 | `train.py` template includes starter features: lag_1, lag_4, YoY growth rate, rolling_mean_4q | All four features verified with pandas `.shift()` API; `.shift(1)` before `.rolling(4).mean()` is the correct leakage-free pattern; `dropna()` required after feature construction |
| FEAT-02 | Agent can add/modify feature engineering code in `train.py` (mutable zone 2 — no separate features.py) | `train_template_forecast.py` is the agent's mutable file; `engineer_features(df)` function is fully inside this mutable file — verified by architecture design |
| FEAT-03 | Feature count capped at 15 in `CLAUDE.md` guidance (small-N overfitting guard) | Must appear as an explicit numbered rule in the forecast CLAUDE.md template; not enforced in code |
| FEAT-04 | Guard hook updated to protect both `prepare.py` and `forecast.py` | `guard-frozen.sh` FROZEN_FILES already updated in Phase 11 (scaffold.py:203). Gap found: `settings.json` deny list only has `prepare.py` — must add `forecast.py` to the deny list in `scaffold.py:_dot_claude_settings()` |
| OPTA-01 | `train.py` template demonstrates optuna `create_study()` with `trial.suggest_*` for hyperparameters | Verified with optuna 4.7.0 (now in pyproject.toml); `create_study(direction='minimize')`, `suggest_float`, `suggest_int`, `suggest_categorical` all confirmed working |
| OPTA-02 | Trial budget capped at `min(50, 2 * n_rows)` in `CLAUDE.md` guidance | Formula verified: 40 rows → 50 trials (capped), 20 rows → 40 trials; must be documented as numbered rule |
| OPTA-03 | Optuna objective function calls frozen `walk_forward_evaluate()` — agent cannot write own validation loop | Verified pattern: `objective(trial)` calls `walk_forward_evaluate(model_fn, X, y, metric, n_splits)` from `automl.forecast`; this is enforced by CLAUDE.md rule, not code |
</phase_requirements>

---

## Summary

Phase 12 delivers three new artifacts and two targeted patches to existing files. The new artifacts are: `train_template_forecast.py` (the agent's mutable starting template for forecasting experiments), a forecast-specific `CLAUDE.md` template (`claude_forecast.md.tmpl`), and tests covering these artifacts. The patches are: (1) add `forecast.py` to the `settings.json` deny list in `scaffold.py._dot_claude_settings()` and (2) add `optuna` to the experiment `pyproject.toml` template in `scaffold._pyproject_content()`.

The core technical challenge is designing `train_template_forecast.py` such that feature engineering is computed inside each CV fold, not before the split. This is the primary leakage risk: if `engineer_features(df)` is called on the full dataset before `walk_forward_evaluate()`, lag and rolling features computed on test data "look back" into training-set rows — but this isn't leakage in the classical sense for pre-computed features. The real risk is that `walk_forward_evaluate()` expects `model_fn(X_train, y_train, X_test)` to receive pre-sliced arrays, so `engineer_features` must be called inside `model_fn` on each fold's data only. The template must make this pattern explicit.

The second challenge is Optuna integration that calls the frozen `walk_forward_evaluate`. The `objective(trial)` function must construct a `model_fn` closure using trial-suggested hyperparameters and then call `walk_forward_evaluate(model_fn, X, y, ...)`. The agent must never write its own CV loop. This constraint is enforced via CLAUDE.md rules, not code guards.

**Primary recommendation:** Create `train_template_forecast.py` with `engineer_features(df)` called inside `model_fn`, `objective(trial)` calling `walk_forward_evaluate`, and a structured output block identical to the existing `train_template.py`. Write a focused forecast `CLAUDE.md` template with the four numbered guard rules. Patch `scaffold.py` to add `forecast.py` to the deny list and `optuna` to the experiment `pyproject.toml`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| optuna | 4.7.0 (installed, in pyproject.toml) | Hyperparameter search via TPE | Better than grid search on small-N data; frozen since Phase 12 decided Optuna |
| automl.forecast | Phase 11 (frozen) | walk_forward_evaluate, get_forecasting_baselines, compute_metric | Project-specific frozen module; must be called by template, never re-implemented |
| automl.prepare | Phase 11 (extended) | load_data with date_col, temporal_split | Frozen data loading; forecast template uses load_data(date_col=...) |
| pandas Series.shift | pandas 3.0.1 (installed) | Lag feature creation without leakage | `.shift(1)` is standard time-series lag; `shift(n).rolling(m).mean()` is leakage-free rolling |
| scikit-learn Ridge/RandomForest | 1.8.0 (installed) | Starter model in template | Template uses Ridge as default; agent can switch |

### Optuna API (verified with 4.7.0)

```python
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)  # suppress [I] logs from run.log

study = optuna.create_study(direction="minimize")  # MAPE is minimize
study.optimize(objective, n_trials=N_TRIALS)       # N_TRIALS = min(50, 2*n_rows)

# Inside objective(trial):
n_estimators = trial.suggest_int("n_estimators", 10, 200)
learning_rate = trial.suggest_float("learning_rate", 1e-4, 0.3, log=True)
alpha = trial.suggest_float("alpha", 0.01, 10.0, log=True)
algorithm = trial.suggest_categorical("algorithm", ["ridge", "lasso", "elastic_net"])
```

### Logging suppression (verified)

Setting `optuna.logging.set_verbosity(optuna.logging.WARNING)` completely suppresses `[I 2026...]` progress lines to stderr — output is clean for `run.log` parsing.

### Not Needed

| Library | Reason Excluded |
|---------|----------------|
| feature-engine | Manual shift() is sufficient; tsfresh/feature-engine add complexity not warranted at N=40 |
| statsmodels | Seasonal naive uses index arithmetic (Phase 11 decision); no ARIMA needed |
| skopt/hyperopt | Optuna is the locked decision per STATE.md roadmap |

**Installation:** Optuna is already in pyproject.toml (added during research). No additional installs needed.

---

## Architecture Patterns

### Recommended File Structure

```
src/automl/
├── train_template_forecast.py    # NEW: forecast mutable template (agent edits this)
└── templates/
    ├── claude.md.tmpl            # EXISTING: classification/regression CLAUDE.md
    └── claude_forecast.md.tmpl  # NEW: forecast-specific CLAUDE.md template

tests/
├── test_train_template_forecast.py  # NEW: structural tests for the template
└── (existing tests unchanged)
```

### Pattern 1: engineer_features Inside model_fn (Leakage-Free)

**What:** Feature engineering must execute inside each CV fold, using only the train portion of data, then applied to test data with lag context from training rows.

**Why critical:** `walk_forward_evaluate` slices `X[train_idx]` and `X[test_idx]` before calling `model_fn`. If features were pre-computed on the full dataset, the sliced arrays still contain values that "peeked" at future training rows. The correct pattern passes raw `y` values as `X` and computes features inside `model_fn`.

**Verified pattern:**
```python
# Source: verified experimentally — see research execution
import numpy as np
import pandas as pd
from automl.forecast import walk_forward_evaluate

def engineer_features(y_array: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Build lag/rolling features from a 1-D revenue array.

    SHIFT-FIRST RULE: Always call .shift(1) before .rolling().
    Returns (X, y_aligned) after dropping NaN rows.
    """
    s = pd.Series(y_array)
    df = pd.DataFrame({
        "lag_1":         s.shift(1),
        "lag_4":         s.shift(4),
        "yoy_growth":    s.shift(1) / s.shift(5) - 1,   # YoY % growth
        "rolling_mean_4q": s.shift(1).rolling(4).mean(),  # shift FIRST
    })
    df["target"] = s
    df = df.dropna()
    X = df.drop(columns=["target"]).values
    y_aligned = df["target"].values
    return X, y_aligned


def model_fn(X_train_raw, y_train_raw, X_test_raw):
    """model_fn receives raw y values as X; features built inside the fold."""
    from sklearn.linear_model import Ridge

    # y_train_raw is the fold's training revenue values
    X_train_feat, y_train_feat = engineer_features(y_train_raw)
    if len(X_train_feat) < 2:
        return np.full(len(y_train_raw), y_train_raw[-1])

    model = Ridge(alpha=1.0)
    model.fit(X_train_feat, y_train_feat)

    # For test: append y_train context to compute lag features on test rows
    y_context = np.concatenate([y_train_raw, X_test_raw.flatten()])
    X_ctx_feat, _ = engineer_features(y_context)
    X_test_feat = X_ctx_feat[-len(X_test_raw):]

    return model.predict(X_test_feat)


# Template usage
y_raw = load_data(CSV_PATH, TARGET_COLUMN, date_col=DATE_COLUMN)[1].values
X_raw = y_raw.reshape(-1, 1)  # raw y as X; features built inside model_fn

scores = walk_forward_evaluate(model_fn, X_raw, y_raw, metric=METRIC, n_splits=5)
```

### Pattern 2: Optuna Objective Calling walk_forward_evaluate

**What:** The Optuna `objective(trial)` builds a `model_fn` closure with trial hyperparameters, then calls `walk_forward_evaluate` from the frozen module.

**Key rule (OPTA-03):** The agent NEVER writes a CV loop. `walk_forward_evaluate` IS the CV.

**Verified pattern:**
```python
# Source: verified with optuna 4.7.0 + automl.forecast
import optuna
from automl.forecast import walk_forward_evaluate

optuna.logging.set_verbosity(optuna.logging.WARNING)

N_TRIALS = min(50, 2 * len(y_raw))

def objective(trial):
    alpha = trial.suggest_float("alpha", 0.01, 10.0, log=True)

    def model_fn(X_train_raw, y_train_raw, X_test_raw):
        X_train_feat, y_train_feat = engineer_features(y_train_raw)
        model = Ridge(alpha=alpha)
        model.fit(X_train_feat, y_train_feat)
        y_context = np.concatenate([y_train_raw, X_test_raw.flatten()])
        X_ctx_feat, _ = engineer_features(y_context)
        X_test_feat = X_ctx_feat[-len(X_test_raw):]
        return model.predict(X_test_feat)

    scores = walk_forward_evaluate(model_fn, X_raw, y_raw, metric=METRIC, n_splits=5)
    return float(np.mean(scores))

study = optuna.create_study(direction="minimize")  # MAPE is minimize
study.optimize(objective, n_trials=N_TRIALS)

best_alpha = study.best_params["alpha"]
```

### Pattern 3: Dual-Baseline Gate in CLAUDE.md Protocol

**What:** After every experiment, the agent compares its MAPE against both the naive and seasonal-naive baselines computed by `get_forecasting_baselines()`. Both must be beaten to keep.

**Enforcement mechanism:** CLAUDE.md numbered rule (not code). `loop_helpers.should_keep()` remains unchanged — it takes `(new_score, best_score)` only. The agent must call `get_forecasting_baselines()` and check both before deciding to keep.

```python
# Pattern for agent to follow (documented in CLAUDE.md):
from automl.forecast import get_forecasting_baselines
baselines = get_forecasting_baselines(y_raw, n_splits=5, period=4)
# MAPE is minimize — lower is better
beats_naive = mean_score < baselines["naive"]
beats_seasonal = mean_score < baselines["seasonal_naive"]
if not (beats_naive and beats_seasonal):
    # auto-revert: git reset --hard HEAD~1
```

### Pattern 4: Structured Output Block (consistent with train_template.py)

The forecast template must print the same structured output as the existing template so `parse_run_result.py` can extract results without modification:

```python
# Identical to train_template.py output format
print("---")
print(f"metric_name:  {METRIC}")
print(f"metric_value: {mean_score:.6f}")
print(f"metric_std:   {score_std:.6f}")
print(f"direction:    minimize")  # MAPE is always minimize
print(f"elapsed_sec:  {elapsed:.1f}")
print(f"model:        {type(model).__name__}")
import json as _json
_result = { ... }
print(f"json_output: {_json.dumps(_result)}")
```

### Anti-Patterns to Avoid

- **Rolling before shift:** `df['col'].rolling(4).mean()` — leaks current quarter's value into the rolling average. Always `df['col'].shift(1).rolling(4).mean()`.
- **Custom CV loop in Optuna objective:** Writing `for fold in KFold(...).split(X)` inside `objective()` violates OPTA-03. Use `walk_forward_evaluate`.
- **Pre-computing features before split:** Calling `engineer_features(df_full)` before passing to `walk_forward_evaluate` risks leakage when `model_fn` processes the fold's training slice. Features must be recomputed inside `model_fn`.
- **Importing from automl package inside template:** `train_template_forecast.py` (which becomes `train.py` in the experiment dir) must import from the local `forecast.py` copy, not `automl.forecast`. Use `from forecast import ...`.
- **Forgetting optuna in experiment pyproject.toml:** The scaffold's `_pyproject_content()` does not include optuna — Phase 12 must add it for the experiment to be able to run the forecast template.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Walk-forward CV | Custom fold loop in objective() | `walk_forward_evaluate()` from frozen `forecast.py` | Frozen module guarantees no future leakage; custom loops risk index errors |
| Hyperparameter search | Manual grid or random loops | `optuna.create_study()` | TPE sampler is more efficient than grid/random on small trial budgets |
| Baseline computation | Computing naive/seasonal-naive in template | `get_forecasting_baselines()` from frozen `forecast.py` | Ensures baselines use identical fold boundaries as model evaluation |
| MAPE computation | `mean(abs(y-yhat)/y)` in template | `compute_metric("mape", ...)` from frozen `forecast.py` | Consistent decimal convention (0.05=5%), edge cases handled |

**Key insight:** The frozen `forecast.py` module IS the evaluation infrastructure. Any code in `train.py` that reimplements CV or metrics undermines the correctness guarantees the frozen module provides.

---

## Common Pitfalls

### Pitfall 1: Rolling Window Leakage (shift-after instead of shift-first)
**What goes wrong:** `df['revenue'].rolling(4).mean()` at row t includes revenue at row t in the rolling average. When this feature is used to predict t, it's using the current period's value.
**Why it happens:** Intuitive mistake — "I want a 4-quarter moving average" seems like `rolling(4)`.
**How to avoid:** Always `df['revenue'].shift(1).rolling(4).mean()`. The shift ensures the rolling window only sees data up through t-1.
**Warning signs:** rolling_mean_4q feature correlates suspiciously well with target; MAPE implausibly low.

### Pitfall 2: YoY Growth Rate with Wrong Lookback
**What goes wrong:** `df['revenue'] / df['revenue'].shift(4) - 1` — numerator uses current quarter (leaks t into feature at t).
**How to avoid:** `df['revenue'].shift(1) / df['revenue'].shift(5) - 1` — both values are fully in the past at prediction time.
**Warning signs:** YoY growth feature appears to perfectly predict direction.

### Pitfall 3: feature engineer on Full Dataset Before walk_forward_evaluate
**What goes wrong:** Calling `engineer_features(df_full)` on the entire 40-row dataset, then passing the resulting X to `walk_forward_evaluate`. The fold splits are applied to already-computed features — but the rolling mean on row 30 used rows 26-29, which are in the "training" portion for the last fold. This is NOT leakage (training data contributes to training features), but it IS wrong for the test fold: test fold features at row 35 would have used rows 31-34 in the rolling window, which are "training" rows for that fold. This is fine for lag features but requires care with rolling features that span the fold boundary.
**The safe pattern:** Compute features inside `model_fn` for each fold separately.
**Warning signs:** Results look too good; fold-by-fold scores don't degrade as expected.

### Pitfall 4: Wrong Import Path in Experiment Template
**What goes wrong:** `from automl.forecast import walk_forward_evaluate` — fails in experiment directory because `automl` package is not installed there.
**Why it happens:** Template is developed in the package context; experiment runs as a standalone directory.
**How to avoid:** Use `from forecast import walk_forward_evaluate` in the template. Scaffold copies `forecast.py` into the experiment directory alongside `train.py`.

**CRITICAL GAP:** Current scaffold.py does NOT copy `forecast.py` into the experiment directory. It only copies `prepare.py`. Phase 12 must add `forecast.py` copy logic to `scaffold_experiment()`.

### Pitfall 5: Optuna [I] Log Spam Flooding run.log
**What goes wrong:** Optuna by default prints `[I 2026-03-14 10:00:00,000] Trial 0 finished with value: 0.12...` — thousands of lines flooding `run.log` and making metric extraction fragile.
**How to avoid:** `optuna.logging.set_verbosity(optuna.logging.WARNING)` at top of script (before `create_study`). Verified: completely suppresses all `[I]` lines.

### Pitfall 6: MAPE Direction Confusion
**What goes wrong:** `walk_forward_evaluate` returns per-fold MAPE values (lower = better). The existing `loop_helpers.should_keep(new_score, best_score)` returns True when `new_score > best_score` (higher = better). Direct use of MAPE as the score would cause keep/revert to be inverted.
**How to avoid:** In the forecast template, track improvement as `new_mape < best_mape`. Do NOT pass MAPE directly to `should_keep`. CLAUDE.md protocol must explicitly state: "For MAPE, lower is better — keep if new_mape < best_mape."

### Pitfall 7: forecast.py Missing from Experiment settings.json Deny List
**What goes wrong:** scaffold.py's `_dot_claude_settings()` currently only has `"Edit(prepare.py)"` and `"Write(prepare.py)"` in the deny list. `forecast.py` is in `guard-frozen.sh` FROZEN_FILES (Phase 11 fixed that) but NOT in settings.json deny list.
**Success criterion FEAT-04:** "verified by running the guard hook against a simulated write to `forecast.py`" — this will pass (guard hook catches it), but the settings.json deny list is an additional layer that must also be updated.
**How to avoid:** Add `"Edit(forecast.py)"` and `"Write(forecast.py)"` to the deny list in `_dot_claude_settings()`.

---

## Code Examples

Verified patterns from research:

### Full train_template_forecast.py Structure

```python
"""
AutoML forecasting experiment script. The agent modifies this file to try different
models, hyperparameters, and feature engineering strategies.

MUTABLE ZONES:
  Zone 1: Model hyperparameters (always mutable)
  Zone 2: engineer_features() function (add/remove/modify features here)

FROZEN:
  prepare.py   -- data loading, temporal split (DO NOT MODIFY)
  forecast.py  -- walk_forward_evaluate, baselines, metrics (DO NOT MODIFY)
"""
import time
import signal
import sys
import numpy as np
import pandas as pd

# --- Configuration (agent edits these) ---
CSV_PATH = "data.csv"
TARGET_COLUMN = "target"
DATE_COLUMN = "date"
METRIC = "mape"           # lower is better for MAPE
TIME_BUDGET = 120         # seconds (longer for Optuna)

# --- Timeout enforcement ---
def _timeout_handler(signum, frame):
    raise TimeoutError(f"Experiment exceeded {TIME_BUDGET}s time budget")
signal.signal(signal.SIGALRM, _timeout_handler)
signal.alarm(TIME_BUDGET)

t_start = time.time()

# --- Frozen imports (DO NOT CHANGE THESE IMPORTS) ---
from prepare import load_data, temporal_split
from forecast import walk_forward_evaluate, get_forecasting_baselines, compute_metric

# --- Load data ---
X_raw, y, task = load_data(CSV_PATH, TARGET_COLUMN, date_col=DATE_COLUMN)
y_raw = y.values  # numpy array in dollar scale
X_input = y_raw.reshape(-1, 1)  # raw y as X; features built inside model_fn

# --- Compute baselines ONCE (frozen, never re-implement) ---
baselines = get_forecasting_baselines(y_raw, n_splits=5, period=4)

# ============================================================
# MUTABLE ZONE 2: Feature Engineering (agent edits this)
# ============================================================
def engineer_features(y_array: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Build lag/rolling features from revenue array.

    RULES:
    1. Always call .shift(1) BEFORE .rolling() — prevents look-ahead leakage.
    2. Cap total features at 15 (small-N overfitting guard).
    3. Call dropna() at the end; return (X_features, y_aligned).
    """
    s = pd.Series(y_array)
    df = pd.DataFrame({
        "lag_1":           s.shift(1),
        "lag_4":           s.shift(4),
        "yoy_growth":      s.shift(1) / s.shift(5) - 1,
        "rolling_mean_4q": s.shift(1).rolling(4).mean(),
    })
    df["target"] = s
    df = df.dropna()
    X = df.drop(columns=["target"]).values
    y_aligned = df["target"].values
    return X, y_aligned

# ============================================================
# MUTABLE ZONE 1: Model + Hyperparameter Optimization
# ============================================================
import optuna
from sklearn.linear_model import Ridge

optuna.logging.set_verbosity(optuna.logging.WARNING)

N_TRIALS = min(50, 2 * len(y_raw))

def objective(trial):
    """Optuna objective — calls walk_forward_evaluate (NEVER write own CV loop)."""
    alpha = trial.suggest_float("alpha", 0.01, 10.0, log=True)

    def model_fn(X_train_raw, y_train_raw, X_test_raw):
        X_train_feat, y_train_feat = engineer_features(y_train_raw)
        if len(X_train_feat) < 2:
            return np.full(len(X_test_raw), y_train_raw[-1])
        model = Ridge(alpha=alpha)
        model.fit(X_train_feat, y_train_feat)
        # Build test features using training context for lag lookback
        y_context = np.concatenate([y_train_raw, X_test_raw.flatten()])
        X_ctx_feat, _ = engineer_features(y_context)
        X_test_feat = X_ctx_feat[-len(X_test_raw):]
        return model.predict(X_test_feat)

    scores = walk_forward_evaluate(model_fn, X_input, y_raw, metric=METRIC, n_splits=5)
    return float(np.mean(scores))

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=N_TRIALS)

best_alpha = study.best_params["alpha"]

# --- Final model evaluation with best hyperparameters ---
def best_model_fn(X_train_raw, y_train_raw, X_test_raw):
    X_train_feat, y_train_feat = engineer_features(y_train_raw)
    model = Ridge(alpha=best_alpha)
    model.fit(X_train_feat, y_train_feat)
    y_context = np.concatenate([y_train_raw, X_test_raw.flatten()])
    X_ctx_feat, _ = engineer_features(y_context)
    X_test_feat = X_ctx_feat[-len(X_test_raw):]
    return model.predict(X_test_feat)

fold_scores = walk_forward_evaluate(best_model_fn, X_input, y_raw, metric=METRIC, n_splits=5)
score_mean = float(np.mean(fold_scores))
score_std = float(np.std(fold_scores))

# --- Print structured output (DO NOT MODIFY THIS BLOCK) ---
elapsed = time.time() - t_start
signal.alarm(0)

print("---")
print(f"metric_name:  {METRIC}")
print(f"metric_value: {score_mean:.6f}")
print(f"metric_std:   {score_std:.6f}")
print(f"direction:    minimize")
print(f"elapsed_sec:  {elapsed:.1f}")
print(f"model:        {type(Ridge()).__name__}")
import json as _json
_result = {
    "metric_name": METRIC,
    "metric_value": round(score_mean, 6),
    "metric_std": round(score_std, 6),
    "direction": "minimize",
    "elapsed_sec": round(elapsed, 1),
    "model": "Ridge",
    "baselines": baselines,
    "beats_naive": score_mean < baselines["naive"],
    "beats_seasonal_naive": score_mean < baselines["seasonal_naive"],
}
print(f"json_output: {_json.dumps(_result)}")
```

### Forecast CLAUDE.md Rules Section

```markdown
## Rules

1. **NEVER STOP.** Run experiments indefinitely until manually interrupted.
2. **NEVER modify `prepare.py` or `forecast.py`.** Both are FROZEN. You will be denied if you try.
3. **`train.py` is the ONLY mutable file.** All changes go here.
4. **SHIFT-FIRST for rolling stats.** Always `.shift(1).rolling(N).mean()`, never `.rolling(N).mean()` directly. Violating this creates look-ahead leakage.
5. **Feature count cap: 15.** Do not create more than 15 features. N=40 rows with 15+ features = guaranteed overfitting.
6. **Trial budget: `min(50, 2 * n_rows)`.** Do not exceed this in `study.optimize(n_trials=...)`.
7. **NEVER write your own CV loop.** Call `walk_forward_evaluate()` from frozen `forecast.py`. This is non-negotiable.
8. **Dual-baseline gate.** To KEEP an experiment: new MAPE must be LOWER than your best AND lower than both `baselines["naive"]` and `baselines["seasonal_naive"]`. Failing to beat either baseline = auto-revert regardless of improvement over prior best.
9. **MAPE direction: lower is better.** Keep if `new_mape < best_mape`. Do NOT use `should_keep()` directly with MAPE scores.
10. **ALWAYS redirect output** to `run.log`. Use `> run.log 2>&1` on every run.
```

### settings.json Deny List Patch (scaffold.py)

```python
# In _dot_claude_settings():
"deny": [
    "Edit(prepare.py)",
    "Write(prepare.py)",
    "Edit(forecast.py)",    # ADD: forecast.py is frozen
    "Write(forecast.py)",   # ADD: forecast.py is frozen
],
```

### Experiment pyproject.toml with Optuna (scaffold.py)

```python
# In _pyproject_content():
dependencies = [
    "scikit-learn>=1.5",
    "pandas>=2.0",
    "numpy>=2.0",
    "xgboost",
    "lightgbm",
    "optuna>=4.0",    # ADD: required for train_template_forecast.py
]
```

### scaffold_experiment: Copy forecast.py (scaffold.py)

```python
# After copying prepare.py, also copy forecast.py:
import automl.forecast as _forecast_module
forecast_source = inspect.getfile(_forecast_module)
shutil.copy2(forecast_source, out / "forecast.py")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No time-series support (v1.0) | Frozen forecast.py with walk-forward CV | Phase 11 | Leakage-free evaluation |
| Manual grid search | Optuna TPE sampler | Phase 12 (this phase) | 2-3x more efficient on small trial budgets |
| Single baseline (dummy regressor) | Dual baselines: naive + seasonal-naive | Phase 11 | Harder keep gate prevents false improvements |
| features.py as separate file | engineer_features() inside train.py | PROJECT.md decision | Preserves single-mutable-file constraint |

**Deprecated/outdated:**
- `mean_squared_error(squared=False)`: replaced by `root_mean_squared_error` in sklearn 1.8.0 — already handled in forecast.py
- Optuna `trial.suggest_uniform` / `trial.suggest_loguniform`: deprecated; use `trial.suggest_float(..., log=True)` — verified in 4.7.0

---

## Open Questions

1. **Should the forecast template copy `forecast.py` from the automl package or assume it's already in the experiment dir?**
   - What we know: scaffold.py copies `prepare.py`; the template imports `from forecast import ...` (local import)
   - What's unclear: scaffold.py does NOT currently copy forecast.py — this gap was found in research
   - Recommendation: Add `shutil.copy2(forecast_source, out / "forecast.py")` to `scaffold_experiment()` and add it to the Phase 12 plan as a required patch

2. **Should `train_template_forecast.py` be used by the current scaffold or only in Phase 13 (when `--date-column` flag is added)?**
   - What we know: Phase 13 handles SCAF-01/02/03 (CLI `--date-column` flag and forecast scaffold)
   - What's unclear: Phase 12 creates the template file itself; Phase 13 wires it into the CLI
   - Recommendation: Phase 12 creates the template as a standalone file; scaffold integration deferred to Phase 13 per REQUIREMENTS.md traceability. Phase 12 tests validate the file structure by inspection, not by calling scaffold.

3. **How many test files for Phase 12?**
   - What we know: The main new artifacts are `train_template_forecast.py` and `claude_forecast.md.tmpl`
   - What's unclear: structural tests vs. execution tests (running the template is slow/noisy)
   - Recommendation: One `test_train_template_forecast.py` with inspection-based tests (parse AST/text) for structure; no execution test (that's Phase 14's E2E). Tests check: `engineer_features` function exists, uses `.shift(1)`, has `rolling`, Optuna import present, `walk_forward_evaluate` called in objective.

---

## Validation Architecture

Nyquist validation is enabled (config.json has `nyquist_validation: true`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (installed) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_train_template_forecast.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BASE-03b | CLAUDE.md template contains dual-baseline rule | unit (text inspection) | `uv run pytest tests/test_train_template_forecast.py::test_claude_forecast_dual_baseline_rule -x` | Wave 0 |
| FEAT-01 | `engineer_features` has lag_1, lag_4, yoy_growth, rolling_mean_4q | unit (AST/text inspection) | `uv run pytest tests/test_train_template_forecast.py::test_engineer_features_starter_features -x` | Wave 0 |
| FEAT-01 | shift(1) appears before rolling in the function | unit (text inspection) | `uv run pytest tests/test_train_template_forecast.py::test_shift_before_rolling -x` | Wave 0 |
| FEAT-02 | `engineer_features` is in `train_template_forecast.py` (mutable zone 2) | unit (file existence + text) | `uv run pytest tests/test_train_template_forecast.py::test_engineer_features_in_template -x` | Wave 0 |
| FEAT-03 | CLAUDE.md template states 15-feature cap | unit (text inspection) | `uv run pytest tests/test_train_template_forecast.py::test_claude_forecast_feature_cap -x` | Wave 0 |
| FEAT-04 | scaffold.py settings.json deny list includes forecast.py | unit (string match in scaffold.py) | `uv run pytest tests/test_scaffold.py::test_settings_deny_forecast -x` | Wave 0 |
| FEAT-04 | guard-frozen.sh FROZEN_FILES includes forecast.py | unit (string match in scaffold.py) | `uv run pytest tests/test_scaffold.py::test_guard_hook_frozen_forecast -x` | Existing (Phase 11) |
| OPTA-01 | `objective(trial)` uses `trial.suggest_*` calls | unit (text inspection) | `uv run pytest tests/test_train_template_forecast.py::test_optuna_suggest_calls -x` | Wave 0 |
| OPTA-02 | CLAUDE.md template states min(50, 2*n_rows) budget cap | unit (text inspection) | `uv run pytest tests/test_train_template_forecast.py::test_claude_forecast_trial_budget_cap -x` | Wave 0 |
| OPTA-03 | `walk_forward_evaluate` is called inside `objective` | unit (text inspection) | `uv run pytest tests/test_train_template_forecast.py::test_objective_calls_walk_forward -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_train_template_forecast.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_train_template_forecast.py` — covers BASE-03b, FEAT-01..04, OPTA-01..03 (text/AST inspection tests)
- [ ] `src/automl/train_template_forecast.py` — the main deliverable
- [ ] `src/automl/templates/claude_forecast.md.tmpl` — forecast-specific CLAUDE.md

*(Existing `tests/test_scaffold.py` will need new test for `test_settings_deny_forecast` — check if it exists before adding)*

---

## Sources

### Primary (HIGH confidence)

- `src/automl/forecast.py` — verified API: `walk_forward_evaluate(model_fn, X, y, metric, n_splits, gap)`, `get_forecasting_baselines(y, n_splits, gap, period)`, confirmed signature and behavior
- `src/automl/scaffold.py` — confirmed deny list gap (only `prepare.py`, missing `forecast.py`) at lines 240-242
- `src/automl/loop_helpers.py` — confirmed `should_keep(new_score, best_score)` signature; does not support baseline gate
- optuna 4.7.0 (installed, verified) — `create_study(direction='minimize')`, `suggest_float`, `suggest_int`, `suggest_categorical`, logging suppression all verified
- pandas 3.0.1 (installed) — `.shift(1).rolling(4).mean()` pattern verified

### Secondary (MEDIUM confidence)

- `.planning/STATE.md` — locked decisions: Optuna locked, feature engineering inside train.py (not separate file), shift-first mandate
- `.planning/REQUIREMENTS.md` — requirement definitions and traceability table
- Phase 11 VERIFICATION.md — confirms what's already done vs. what Phase 12 must do

### Tertiary (LOW confidence)

None — all findings verified from code inspection or live execution.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — optuna 4.7.0 verified installed; all APIs tested live
- Architecture: HIGH — patterns verified experimentally; import paths confirmed
- Pitfalls: HIGH — shift-before-rolling verified; import path pitfall confirmed by scaffold inspection; MAPE direction confirmed by forecast.py

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable domain; optuna API unlikely to change in patch releases)
