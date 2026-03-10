"""Tests for the multi-draft initialization system (drafts.py).

Covers algorithm family definitions, draft generation from template,
DraftResult dataclass, and best-draft selection logic.
"""

from __future__ import annotations

import textwrap

import pytest

from automl.drafts import (
    ALGORITHM_FAMILIES,
    DraftResult,
    generate_draft_train_py,
    select_best_draft,
)


# ---- Template fixture ----

TEMPLATE_CONTENT = textwrap.dedent("""\
    import time
    import signal
    import sys

    CSV_PATH = "data.csv"
    TARGET_COLUMN = "target"
    METRIC = "accuracy"
    TIME_BUDGET = 60

    t_start = time.time()

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

    elapsed = time.time() - t_start
    print(f"metric_value: {score_mean:.6f}")
""")


# ---- Algorithm family tests ----

class TestAlgorithmFamilies:
    def test_classification_families(self):
        families = ALGORITHM_FAMILIES["classification"]
        assert len(families) == 5
        for algo in families:
            assert "name" in algo
            assert "imports" in algo
            assert "model_line" in algo

    def test_regression_families(self):
        families = ALGORITHM_FAMILIES["regression"]
        assert len(families) == 5
        for algo in families:
            assert "name" in algo
            assert "imports" in algo
            assert "model_line" in algo


# ---- Draft generation tests ----

class TestGenerateDraft:
    def test_generate_draft_replaces_model(self):
        xgb_algo = {
            "name": "XGBoost",
            "imports": "from xgboost import XGBClassifier",
            "model_line": "model = XGBClassifier(n_estimators=200, verbosity=0)",
        }
        result = generate_draft_train_py(TEMPLATE_CONTENT, xgb_algo)
        assert "XGBClassifier" in result
        assert "LogisticRegression" not in result

    def test_generate_draft_preserves_structure(self):
        xgb_algo = {
            "name": "XGBoost",
            "imports": "from xgboost import XGBClassifier",
            "model_line": "model = XGBClassifier(n_estimators=200, verbosity=0)",
        }
        result = generate_draft_train_py(TEMPLATE_CONTENT, xgb_algo)
        assert "from prepare import" in result
        assert "evaluate(" in result
        assert "metric_value:" in result


# ---- DraftResult tests ----

class TestDraftResult:
    def test_draft_result_dataclass(self):
        dr = DraftResult(
            name="XGBoost",
            metric_value=0.85,
            status="success",
            commit_hash="abc1234",
            description="XGBoost: accuracy=0.850000",
        )
        assert dr.name == "XGBoost"
        assert dr.metric_value == 0.85
        assert dr.status == "success"
        assert dr.commit_hash == "abc1234"
        assert dr.description == "XGBoost: accuracy=0.850000"


# ---- Selection tests ----

class TestSelectBestDraft:
    def test_select_best_draft(self):
        results = [
            DraftResult("A", 0.75, "draft-discard", "aaa", "A"),
            DraftResult("B", 0.90, "draft-discard", "bbb", "B"),
            DraftResult("C", 0.82, "draft-discard", "ccc", "C"),
        ]
        best = select_best_draft(results)
        assert best is not None
        assert best.name == "B"
        assert best.metric_value == 0.90

    def test_select_best_draft_empty(self):
        assert select_best_draft([]) is None

    def test_select_best_draft_all_crashed(self):
        results = [
            DraftResult("A", None, "draft-discard", "aaa", "crashed"),
            DraftResult("B", None, "draft-discard", "bbb", "crashed"),
        ]
        assert select_best_draft(results) is None

    def test_select_best_draft_some_crashed(self):
        results = [
            DraftResult("A", None, "draft-discard", "aaa", "crashed"),
            DraftResult("B", 0.80, "draft-discard", "bbb", "B"),
            DraftResult("C", None, "draft-discard", "ccc", "crashed"),
            DraftResult("D", 0.70, "draft-discard", "ddd", "D"),
        ]
        best = select_best_draft(results)
        assert best is not None
        assert best.name == "B"
        assert best.metric_value == 0.80

    def test_draft_status_strings(self):
        keep = DraftResult("Winner", 0.95, "draft-keep", "abc", "winner")
        discard = DraftResult("Loser", 0.50, "draft-discard", "def", "loser")
        assert keep.status == "draft-keep"
        assert discard.status == "draft-discard"
