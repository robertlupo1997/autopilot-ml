"""
AutoML experiment script. The agent modifies this file to try different
models, hyperparameters, and ensemble strategies.
Usage: python train.py
"""
import time
import signal
import sys

# --- Configuration (agent edits these) ---
CSV_PATH = "data.csv"
TARGET_COLUMN = "target"
METRIC = "accuracy"           # user-facing metric name
TIME_BUDGET = 60              # seconds

# --- Timeout enforcement ---
def _timeout_handler(signum, frame):
    raise TimeoutError(f"Experiment exceeded {TIME_BUDGET}s time budget")
signal.signal(signal.SIGALRM, _timeout_handler)
signal.alarm(TIME_BUDGET)

t_start = time.time()

# --- Load and preprocess ---
from prepare import load_data, build_preprocessor, evaluate, validate_metric

X, y, task = load_data(CSV_PATH, TARGET_COLUMN)
sklearn_metric, direction = validate_metric(METRIC, task)
preprocessor = build_preprocessor(X)
X_processed = preprocessor.transform(X)

# --- Model (agent edits this section) ---
from sklearn.linear_model import LogisticRegression
model = LogisticRegression(max_iter=1000)

# --- Evaluate ---
score_mean, score_std = evaluate(model, X_processed, y, sklearn_metric, task)

# --- Print structured output ---
elapsed = time.time() - t_start
signal.alarm(0)  # cancel timeout

print("---")
print(f"metric_name:  {METRIC}")
print(f"metric_value: {score_mean:.6f}")
print(f"metric_std:   {score_std:.6f}")
print(f"direction:    {direction}")
print(f"elapsed_sec:  {elapsed:.1f}")
print(f"model:        {type(model).__name__}")
