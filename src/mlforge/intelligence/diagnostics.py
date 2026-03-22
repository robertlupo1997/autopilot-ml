"""Diagnostics engine for regression and classification error analysis.

Provides actionable diagnostics telling the agent WHERE the model fails:
worst predictions, bias direction, feature-error correlations (regression),
misclassified samples, per-class accuracy, confused class pairs (classification).
"""

from __future__ import annotations

from collections import Counter

import numpy as np
from numpy.typing import ArrayLike


def diagnose_regression(
    y_true: ArrayLike,
    y_pred: ArrayLike,
    feature_names: list[str] | None = None,
    X: ArrayLike | None = None,
    top_n: int = 5,
) -> dict:
    """Analyze regression prediction errors.

    Args:
        y_true: Ground truth values.
        y_pred: Predicted values.
        feature_names: Optional feature names for correlation analysis.
        X: Optional feature matrix (n_samples, n_features) for correlation.
        top_n: Number of worst predictions to return.

    Returns:
        Dict with keys: worst_predictions, bias, feature_error_correlations.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    error = y_pred - y_true
    abs_error = np.abs(error)

    # Worst predictions (highest absolute error)
    sorted_idx = np.argsort(abs_error)[::-1][:top_n]
    worst_predictions = [
        {
            "index": int(i),
            "y_true": float(y_true[i]),
            "y_pred": float(y_pred[i]),
            "abs_error": float(abs_error[i]),
        }
        for i in sorted_idx
    ]

    # Bias analysis
    mean_error = float(np.mean(error))
    if mean_error > 0:
        direction = "over"
    elif mean_error < 0:
        direction = "under"
    else:
        direction = "neutral"

    bias = {"direction": direction, "magnitude": mean_error}

    # Feature-error correlations
    feature_error_correlations: dict[str, float] = {}
    if X is not None and feature_names is not None:
        X = np.asarray(X, dtype=float)
        for j, name in enumerate(feature_names):
            col = X[:, j]
            if np.std(col) == 0:
                continue  # skip constant features
            corr = np.corrcoef(col, abs_error)[0, 1]
            feature_error_correlations[name] = float(corr)

    return {
        "worst_predictions": worst_predictions,
        "bias": bias,
        "feature_error_correlations": feature_error_correlations,
    }


def diagnose_classification(
    y_true: ArrayLike,
    y_pred: ArrayLike,
    class_names: list[str] | None = None,
    y_proba: ArrayLike | None = None,
    top_n: int = 5,
) -> dict:
    """Analyze classification prediction errors.

    Args:
        y_true: Ground truth labels.
        y_pred: Predicted labels.
        class_names: Optional mapping from label index to name.
        y_proba: Optional prediction probabilities (n_samples, n_classes).
        top_n: Number of misclassified samples to return.

    Returns:
        Dict with keys: misclassified_samples, per_class_accuracy, confused_pairs.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    # Misclassified samples
    wrong_mask = y_true != y_pred
    wrong_indices = np.where(wrong_mask)[0]

    if y_proba is not None:
        y_proba = np.asarray(y_proba, dtype=float)
        # Sort by max predicted probability (highest confidence wrong first)
        max_proba = np.max(y_proba[wrong_indices], axis=1)
        sorted_order = np.argsort(max_proba)[::-1]
        wrong_indices = wrong_indices[sorted_order]

    misclassified_samples = [
        {
            "index": int(i),
            "y_true": y_true[i].item() if hasattr(y_true[i], "item") else y_true[i],
            "y_pred": y_pred[i].item() if hasattr(y_pred[i], "item") else y_pred[i],
        }
        for i in wrong_indices[:top_n]
    ]

    # Per-class accuracy
    classes = np.unique(y_true)
    per_class_accuracy: dict = {}
    for cls in classes:
        mask = y_true == cls
        correct = np.sum(y_pred[mask] == cls)
        total = np.sum(mask)
        key = cls
        if class_names is not None:
            key = class_names[int(cls)]
        else:
            key = cls.item() if hasattr(cls, "item") else cls
        per_class_accuracy[key] = float(correct / total) if total > 0 else 0.0

    # Confused pairs: (true_class, predicted_class, count) sorted by count desc
    pair_counts: Counter = Counter()
    for t, p in zip(y_true[wrong_mask], y_pred[wrong_mask], strict=True):
        t_key = t.item() if hasattr(t, "item") else t
        p_key = p.item() if hasattr(p, "item") else p
        if class_names is not None:
            t_key = class_names[int(t)]
            p_key = class_names[int(p)]
        pair_counts[(t_key, p_key)] += 1

    confused_pairs = [
        (pair[0], pair[1], count)
        for pair, count in pair_counts.most_common(top_n)
    ]

    return {
        "misclassified_samples": misclassified_samples,
        "per_class_accuracy": per_class_accuracy,
        "confused_pairs": confused_pairs,
    }
