"""Multi-draft initialization: generate diverse train.py variants.

Provides algorithm family definitions, draft generation from templates,
and best-draft selection logic. The agent generates 3-5 diverse train.py
variants using different algorithm families, evaluates all, and selects
the best as the starting point for iterative improvement.

DRAFT-01: Algorithm families (5 classification + 5 regression)
DRAFT-02: Draft generation via template swap
DRAFT-03: Best draft selection
DRAFT-04: DraftResult with draft-keep/draft-discard status
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Algorithm families for diverse drafts
# ---------------------------------------------------------------------------
# Each family represents a fundamentally different modeling approach.
# Keyed by task type ("classification" or "regression").

ALGORITHM_FAMILIES: dict[str, list[dict[str, str]]] = {
    "classification": [
        {
            "name": "LogisticRegression",
            "imports": "from sklearn.linear_model import LogisticRegression",
            "model_line": "model = LogisticRegression(max_iter=1000)",
        },
        {
            "name": "RandomForest",
            "imports": "from sklearn.ensemble import RandomForestClassifier",
            "model_line": "model = RandomForestClassifier(n_estimators=100, random_state=42)",
        },
        {
            "name": "XGBoost",
            "imports": "from xgboost import XGBClassifier",
            "model_line": "model = XGBClassifier(n_estimators=100, random_state=42, verbosity=0)",
        },
        {
            "name": "LightGBM",
            "imports": "from lightgbm import LGBMClassifier",
            "model_line": "model = LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)",
        },
        {
            "name": "SVM",
            "imports": "from sklearn.svm import SVC",
            "model_line": "model = SVC(probability=True, random_state=42)",
        },
    ],
    "regression": [
        {
            "name": "Ridge",
            "imports": "from sklearn.linear_model import Ridge",
            "model_line": "model = Ridge()",
        },
        {
            "name": "RandomForest",
            "imports": "from sklearn.ensemble import RandomForestRegressor",
            "model_line": "model = RandomForestRegressor(n_estimators=100, random_state=42)",
        },
        {
            "name": "XGBoost",
            "imports": "from xgboost import XGBRegressor",
            "model_line": "model = XGBRegressor(n_estimators=100, random_state=42, verbosity=0)",
        },
        {
            "name": "LightGBM",
            "imports": "from lightgbm import LGBMRegressor",
            "model_line": "model = LGBMRegressor(n_estimators=100, random_state=42, verbose=-1)",
        },
        {
            "name": "ElasticNet",
            "imports": "from sklearn.linear_model import ElasticNet",
            "model_line": "model = ElasticNet(random_state=42)",
        },
    ],
}


# ---------------------------------------------------------------------------
# DraftResult dataclass
# ---------------------------------------------------------------------------

@dataclass
class DraftResult:
    """Result of a single draft evaluation.

    Attributes
    ----------
    name : str
        Algorithm name (e.g. "XGBoost").
    metric_value : float or None
        Cross-validation score (None if crashed/timed out).
    status : str
        One of "draft-keep" (winner) or "draft-discard" (others).
        Set by the caller after selection, not by select_best_draft.
    commit_hash : str
        Git commit hash for this draft.
    description : str
        Human-readable description of the draft result.
    """

    name: str
    metric_value: float | None
    status: str
    commit_hash: str
    description: str


# ---------------------------------------------------------------------------
# Draft generation
# ---------------------------------------------------------------------------

def generate_draft_train_py(template_content: str, algorithm: dict) -> str:
    """Swap the model section in a train_template.py content string.

    Takes the template CONTENT (string, not path) and an algorithm dict.
    Replaces content between the ``# --- Model`` marker and the
    ``# --- Evaluate`` marker with the algorithm's imports and model line.

    Parameters
    ----------
    template_content : str
        Full content of the train_template.py file.
    algorithm : dict
        Must have keys "imports" and "model_line".

    Returns
    -------
    str
        Modified template content with the new algorithm.
    """
    new_model_section = f"{algorithm['imports']}\n{algorithm['model_line']}"
    pattern = r"(# --- Model.*?---\n).*?(\n# --- Evaluate)"
    replacement = rf"\g<1>{new_model_section}\g<2>"
    return re.sub(pattern, replacement, template_content, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Best draft selection
# ---------------------------------------------------------------------------

def select_best_draft(results: list[DraftResult]) -> DraftResult | None:
    """Select the draft with the highest metric_value.

    Filters out drafts where metric_value is None (crashes/timeouts).
    Returns None if no successful drafts exist.

    This function does NOT set statuses -- the caller marks the winner
    as "draft-keep" and others as "draft-discard".

    Parameters
    ----------
    results : list[DraftResult]
        List of draft evaluation results.

    Returns
    -------
    DraftResult or None
        The best-performing draft, or None if all failed.
    """
    valid = [r for r in results if r.metric_value is not None]
    if not valid:
        return None
    return max(valid, key=lambda r: r.metric_value)  # type: ignore[arg-type]
