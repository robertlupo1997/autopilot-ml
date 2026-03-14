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
def engineer_features(y_array: np.ndarray) -> tuple:
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
    if len(X_train_feat) < 2:
        return np.full(len(X_test_raw), y_train_raw[-1])
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
