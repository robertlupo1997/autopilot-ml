"""Multi-draft generation and selection.

Defines algorithm families for diverse initial solutions and provides
selection logic to pick the best draft before linear iteration.
"""

from __future__ import annotations

from dataclasses import dataclass


ALGORITHM_FAMILIES: dict[str, dict[str, str]] = {
    "linear": {
        "description": "Linear models (Ridge/LogisticRegression)",
        "classification": "LogisticRegression",
        "regression": "Ridge",
    },
    "random_forest": {
        "description": "Random forest ensemble",
        "classification": "RandomForestClassifier",
        "regression": "RandomForestRegressor",
    },
    "xgboost": {
        "description": "XGBoost gradient boosting",
        "classification": "XGBClassifier",
        "regression": "XGBRegressor",
    },
    "lightgbm": {
        "description": "LightGBM gradient boosting",
        "classification": "LGBMClassifier",
        "regression": "LGBMRegressor",
    },
    "svm": {
        "description": "Support vector machines",
        "classification": "SVC",
        "regression": "SVR",
    },
}


@dataclass
class DraftResult:
    """Result from a single draft experiment.

    Attributes:
        name: Algorithm family name (e.g. "linear", "xgboost").
        metric_value: Evaluation metric or None if the draft failed.
        status: "draft-keep" or "draft-discard".
        commit_hash: Git commit hash for this draft's code.
        description: Human-readable description of what was tried.
    """

    name: str
    metric_value: float | None
    status: str
    commit_hash: str
    description: str


def select_best_draft(
    results: list[DraftResult],
    direction: str = "maximize",
) -> DraftResult | None:
    """Select the best draft from a list of results.

    Args:
        results: List of DraftResult objects from draft experiments.
        direction: "maximize" or "minimize" -- which direction is better.

    Returns:
        The DraftResult with the best metric, or None if no valid results.
    """
    valid = [r for r in results if r.metric_value is not None]
    if not valid:
        return None

    if direction == "minimize":
        return min(valid, key=lambda r: r.metric_value)  # type: ignore[arg-type]
    return max(valid, key=lambda r: r.metric_value)  # type: ignore[arg-type]
