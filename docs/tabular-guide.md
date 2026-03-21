# Tabular ML Domain Guide

The default domain for classification and regression on structured CSV or Parquet data.

---

## Overview

The tabular domain handles traditional machine learning on structured datasets. mlforge loads your data, detects whether the task is classification or regression, scaffolds a research workspace, and hands control to Claude Code acting as an autonomous ML researcher.

Supported model libraries: **scikit-learn**, **XGBoost**, **LightGBM**, and **Optuna** for hyperparameter search.

---

## Task Detection

mlforge auto-detects the task type from the target column:

| Condition | Task | Default Metric |
|---|---|---|
| Target has 20 or fewer unique values | Classification | `f1` |
| Target has more than 20 unique values | Regression | `rmse` |

Override with `--metric` and `--direction` flags.

---

## Supported Metrics

### Classification

| Metric | Direction | Notes |
|---|---|---|
| `accuracy` | maximize | Overall correctness |
| `auc` | maximize | Area under ROC curve |
| `roc_auc` | maximize | Alias for `auc` |
| `f1` | maximize | Harmonic mean of precision and recall |
| `f1_weighted` | maximize | Class-weighted F1 |
| `precision` | maximize | Positive predictive value |
| `recall` | maximize | Sensitivity / true positive rate |
| `log_loss` | minimize | Logarithmic loss |

### Regression

| Metric | Direction | Notes |
|---|---|---|
| `rmse` | minimize | Root mean squared error |
| `mae` | minimize | Mean absolute error |
| `mse` | minimize | Mean squared error |
| `r2` | maximize | Coefficient of determination |

---

## Scaffolded Files

### prepare.py -- FROZEN

The evaluation harness. Loads data, splits train/test, computes metrics. The agent **cannot modify** this file. This guarantees that metric computation is consistent across all experiments.

### train.py -- MUTABLE

The agent's workspace. Starts from a baseline template and evolves through experiments. Each improvement is committed to git; each failure is reverted.

### CLAUDE.md -- Protocol Rules

The instruction file that governs agent behavior: dual-baseline gate, cross-validation rules, output format, experiment journaling, and diagnostic recording.

---

## Dual-Baseline Gate

Every experiment must beat **both** baselines to count as an improvement.

### Classification Baselines

| Baseline | Strategy |
|---|---|
| `most_frequent` | Always predicts the majority class |
| `stratified` | Random predictions preserving class distribution |

### Regression Baselines

| Baseline | Strategy |
|---|---|
| `mean` | Always predicts the training set mean |
| `median` | Always predicts the training set median |

Both baselines are computed using scikit-learn's `DummyClassifier` and `DummyRegressor`. The agent cannot claim improvement unless it beats both.

---

## Multi-Draft Mode

Enabled with `--enable-drafts`. The agent generates 3-5 diverse initial solutions:

1. **Linear models** -- LogisticRegression (classification) or Ridge (regression)
2. **Random Forest** -- ensemble of decision trees
3. **XGBoost** -- gradient boosted trees
4. **LightGBM** -- gradient boosted trees (histogram-based)
5. **SVM** -- support vector machines

mlforge evaluates all drafts, selects the best, and iterates linearly from there.

---

## Branch-on-Stagnation

After 3 consecutive reverts (configurable via `stagnation_threshold`), mlforge branches from the best-ever commit to try a different model family.

1. Agent experiments. No improvement. Reverted. (count: 1)
2. Agent tries again. No improvement. Reverted. (count: 2)
3. Third attempt. No improvement. Reverted. (count: 3)
4. Stagnation detected. mlforge creates `explore-{family}` branch from best-ever commit.
5. Agent switches to a different model family and resumes iteration.

---

## Diagnostics

After each experiment, the agent receives diagnostic feedback:

- **Worst predictions** -- specific samples with the highest error
- **Bias direction** -- systematic over-prediction or under-prediction
- **Feature-error correlations** -- which features correlate with model errors

Diagnostics are recorded in `experiments.md` for reference across iterations.

---

## Example Workflows

```bash
# Auto-detect everything
mlforge housing.csv "predict price"

# Explicit regression with multi-draft
mlforge housing.csv "predict price" --metric rmse --direction minimize --enable-drafts

# High-budget swarm for fraud detection
mlforge fraud.csv "detect fraud" --metric f1 --budget-usd 20 --swarm --n-agents 3

# Custom protocol and frozen module
mlforge data.csv "predict churn" --custom-claude-md my_rules.md --custom-frozen feature_eng.py

# Budget-constrained session
mlforge sales.csv "predict revenue" --budget-minutes 30 --budget-experiments 15
```

---

## Output Files

| File | Description |
|---|---|
| `train.py` | Best model code, committed to git |
| `predictions.csv` | Test set predictions from the best model |
| `best_model.joblib` | Serialized model artifact |
| `experiments.md` | Experiment journal with metrics and diagnostics |
| `RETROSPECTIVE.md` | Session summary: what worked, what didn't |
