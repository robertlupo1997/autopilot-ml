"""Tests for the diagnostics engine -- regression and classification error analysis."""

from __future__ import annotations

import numpy as np
import pytest

from mlforge.intelligence.diagnostics import diagnose_classification, diagnose_regression


# ── Regression diagnostics ────────────────────────────────────────


class TestDiagnoseRegression:
    def test_worst_predictions(self):
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.0, 2.0, 3.0, 4.0, 15.0])  # index 4 is worst
        result = diagnose_regression(y_true, y_pred, top_n=3)

        worst = result["worst_predictions"]
        assert len(worst) == 3
        assert worst[0]["index"] == 4
        assert worst[0]["abs_error"] == 10.0
        assert worst[0]["y_true"] == 5.0
        assert worst[0]["y_pred"] == 15.0

    def test_bias_over(self):
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([3.0, 4.0, 5.0])  # consistently over-predicting
        result = diagnose_regression(y_true, y_pred)

        assert result["bias"]["direction"] == "over"
        assert result["bias"]["magnitude"] == pytest.approx(2.0)

    def test_bias_under(self):
        y_true = np.array([5.0, 6.0, 7.0])
        y_pred = np.array([3.0, 4.0, 5.0])  # consistently under-predicting
        result = diagnose_regression(y_true, y_pred)

        assert result["bias"]["direction"] == "under"
        assert result["bias"]["magnitude"] == pytest.approx(-2.0)

    def test_bias_neutral(self):
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.0, 2.0, 3.0])  # perfect predictions
        result = diagnose_regression(y_true, y_pred)

        assert result["bias"]["direction"] == "neutral"
        assert result["bias"]["magnitude"] == pytest.approx(0.0)

    def test_feature_correlations(self):
        rng = np.random.default_rng(42)
        # Feature 0: positive values so abs_error = error = feature value
        feat0 = np.abs(rng.standard_normal(100)) + 0.1
        feat1 = rng.standard_normal(100)
        X = np.column_stack([feat0, feat1])
        y_true = np.zeros(100)
        # error = y_pred - y_true = feat0, abs_error = feat0
        y_pred = feat0
        result = diagnose_regression(
            y_true, y_pred, feature_names=["correlated", "random"], X=X
        )

        corrs = result["feature_error_correlations"]
        assert abs(corrs["correlated"]) > 0.9
        # Second feature should have low correlation
        assert abs(corrs["random"]) < 0.5

    def test_zero_std_feature_excluded(self):
        X = np.array([[1.0, 5.0], [1.0, 6.0], [1.0, 7.0]])  # col 0 is constant
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([2.0, 3.0, 4.0])
        result = diagnose_regression(
            y_true, y_pred, feature_names=["constant", "varying"], X=X
        )

        corrs = result["feature_error_correlations"]
        assert "constant" not in corrs
        assert "varying" in corrs

    def test_no_features_returns_empty_correlations(self):
        y_true = np.array([1.0, 2.0])
        y_pred = np.array([1.5, 2.5])
        result = diagnose_regression(y_true, y_pred)

        assert result["feature_error_correlations"] == {}


# ── Classification diagnostics ────────────────────────────────────


class TestDiagnoseClassification:
    def test_misclassified_samples(self):
        y_true = np.array([0, 1, 0, 1, 0])
        y_pred = np.array([0, 0, 0, 1, 1])  # indices 1, 4 wrong
        result = diagnose_classification(y_true, y_pred)

        indices = [s["index"] for s in result["misclassified_samples"]]
        assert set(indices) == {1, 4}

    def test_per_class_accuracy(self):
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_pred = np.array([0, 0, 1, 1, 1, 0])  # class 0: 2/3, class 1: 2/3
        result = diagnose_classification(y_true, y_pred)

        acc = result["per_class_accuracy"]
        assert acc[0] == pytest.approx(2.0 / 3.0)
        assert acc[1] == pytest.approx(2.0 / 3.0)

    def test_confused_pairs(self):
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([1, 1, 0, 0, 0, 2])  # (0->1)x2, (1->0)x2, (2->0)x1
        result = diagnose_classification(y_true, y_pred)

        pairs = result["confused_pairs"]
        # Top pair should have count 2
        assert pairs[0][2] == 2
        assert pairs[1][2] == 2
        assert pairs[2][2] == 1

    def test_with_proba_sorts_by_confidence(self):
        y_true = np.array([0, 1, 0])
        y_pred = np.array([1, 0, 1])  # all wrong
        # Sample 0: high confidence wrong (0.9 for class 1)
        # Sample 1: low confidence wrong (0.6 for class 0)
        # Sample 2: medium confidence wrong (0.7 for class 1)
        y_proba = np.array([
            [0.1, 0.9],   # index 0: 90% confident (wrong)
            [0.6, 0.4],   # index 1: 60% confident (wrong)
            [0.3, 0.7],   # index 2: 70% confident (wrong)
        ])
        result = diagnose_classification(y_true, y_pred, y_proba=y_proba)

        samples = result["misclassified_samples"]
        # Sorted by max predicted probability descending
        assert samples[0]["index"] == 0  # 0.9 confidence
        assert samples[1]["index"] == 2  # 0.7 confidence
        assert samples[2]["index"] == 1  # 0.6 confidence

    def test_class_names_used(self):
        y_true = np.array([0, 1])
        y_pred = np.array([0, 1])
        result = diagnose_classification(
            y_true, y_pred, class_names=["cat", "dog"]
        )

        acc = result["per_class_accuracy"]
        assert "cat" in acc
        assert "dog" in acc
