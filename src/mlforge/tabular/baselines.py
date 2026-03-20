"""Baseline computation and dual-baseline gate for tabular ML.

Computes naive and domain-specific baselines using sklearn dummy models.
The dual-baseline gate rejects experiments that do not beat ALL baselines.
"""

from __future__ import annotations

import numpy as np
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score


def compute_baselines(
    X: np.ndarray,
    y: np.ndarray,
    scoring: str,
    task: str,
) -> dict[str, dict[str, float]]:
    """Compute baseline scores using dummy models.

    For classification: most_frequent and stratified strategies.
    For regression: mean and median strategies.

    Args:
        X: Feature matrix.
        y: Target values.
        scoring: Sklearn scoring string.
        task: Either 'classification' or 'regression'.

    Returns:
        Dict mapping strategy name to dict with 'score' and 'std'.
    """
    if task == "classification":
        strategies = {
            "most_frequent": DummyClassifier(strategy="most_frequent"),
            "stratified": DummyClassifier(strategy="stratified", random_state=42),
        }
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    else:
        strategies = {
            "mean": DummyRegressor(strategy="mean"),
            "median": DummyRegressor(strategy="median"),
        }
        cv = KFold(n_splits=5, shuffle=True, random_state=42)

    baselines = {}
    for name, model in strategies.items():
        scores = cross_val_score(model, X, y, scoring=scoring, cv=cv)
        baselines[name] = {"score": float(scores.mean()), "std": float(scores.std())}

    return baselines


def passes_baseline_gate(
    metric_value: float,
    baselines: dict[str, dict[str, float]],
    direction: str,
) -> bool:
    """Check if a metric value beats ALL baselines.

    Args:
        metric_value: The metric value to check.
        baselines: Dict from compute_baselines() output.
        direction: 'maximize' or 'minimize'.

    Returns:
        True only if metric strictly beats every baseline score.
    """
    for baseline_info in baselines.values():
        baseline_score = baseline_info["score"]
        if direction == "maximize" and metric_value <= baseline_score:
            return False
        if direction == "minimize" and metric_value >= baseline_score:
            return False
    return True
