"""Tests for deep learning baseline computation."""

from __future__ import annotations

import math

import numpy as np
import pytest


class TestDLComputeBaselinesClassification:
    """DL compute_baselines returns random + most_frequent for classification metrics."""

    def test_accuracy_returns_random_and_most_frequent(self):
        from mlforge.deeplearning.baselines import compute_baselines

        labels = np.array([0, 0, 0, 1, 1, 2])
        result = compute_baselines(labels, scoring="accuracy", task="image_classification")
        assert "random" in result
        assert "most_frequent" in result

    def test_accuracy_scores_have_score_and_std(self):
        from mlforge.deeplearning.baselines import compute_baselines

        labels = np.array([0, 0, 0, 1, 1, 2])
        result = compute_baselines(labels, scoring="accuracy", task="image_classification")
        for name, entry in result.items():
            assert "score" in entry
            assert "std" in entry
            assert isinstance(entry["score"], float)
            assert isinstance(entry["std"], float)

    def test_accuracy_scores_in_valid_range(self):
        from mlforge.deeplearning.baselines import compute_baselines

        labels = np.array([0, 0, 0, 1, 1, 2])
        result = compute_baselines(labels, scoring="accuracy", task="image_classification")
        for entry in result.values():
            assert 0 <= entry["score"] <= 1

    def test_binary_labels(self):
        from mlforge.deeplearning.baselines import compute_baselines

        labels = np.array([0, 0, 1, 1, 0, 1])
        result = compute_baselines(labels, scoring="accuracy", task="image_classification")
        assert "random" in result
        assert "most_frequent" in result
        # most_frequent should be ~0.5 for balanced binary
        assert 0.3 <= result["most_frequent"]["score"] <= 0.7

    def test_multiclass_most_frequent_approximates_majority_ratio(self):
        from mlforge.deeplearning.baselines import compute_baselines

        # 60% class 0, 20% class 1, 20% class 2
        labels = np.array([0] * 60 + [1] * 20 + [2] * 20)
        result = compute_baselines(labels, scoring="accuracy", task="image_classification")
        # most_frequent should approximate 0.6
        assert 0.5 <= result["most_frequent"]["score"] <= 0.7

    def test_f1_weighted_scoring(self):
        from mlforge.deeplearning.baselines import compute_baselines

        labels = np.array([0, 0, 0, 1, 1, 2])
        result = compute_baselines(labels, scoring="f1_weighted", task="text_classification")
        assert "random" in result
        assert "most_frequent" in result


class TestDLComputeBaselinesLoss:
    """DL compute_baselines returns theoretical values for loss metric."""

    def test_loss_returns_random_guess_and_uniform_prediction(self):
        from mlforge.deeplearning.baselines import compute_baselines

        labels = np.array([0, 1, 2])
        result = compute_baselines(labels, scoring="loss", task="image_classification")
        assert "random_guess" in result
        assert "uniform_prediction" in result

    def test_loss_random_guess_is_theoretical_cross_entropy(self):
        from mlforge.deeplearning.baselines import compute_baselines

        labels = np.array([0, 1, 2])
        result = compute_baselines(labels, scoring="loss", task="image_classification")
        expected = -math.log(1 / 3)
        assert abs(result["random_guess"]["score"] - expected) < 1e-6

    def test_loss_uniform_prediction_is_95_percent_of_random(self):
        from mlforge.deeplearning.baselines import compute_baselines

        labels = np.array([0, 1, 2])
        result = compute_baselines(labels, scoring="loss", task="image_classification")
        random_score = result["random_guess"]["score"]
        assert abs(result["uniform_prediction"]["score"] - 0.95 * random_score) < 1e-6

    def test_loss_baselines_have_zero_std(self):
        from mlforge.deeplearning.baselines import compute_baselines

        labels = np.array([0, 1, 2])
        result = compute_baselines(labels, scoring="loss", task="image_classification")
        for entry in result.values():
            assert entry["std"] == 0.0

    def test_loss_baselines_have_score_and_std(self):
        from mlforge.deeplearning.baselines import compute_baselines

        labels = np.array([0, 1, 2])
        result = compute_baselines(labels, scoring="loss", task="image_classification")
        for entry in result.values():
            assert "score" in entry
            assert "std" in entry
