"""Tests for automl.prepare -- frozen data pipeline (PIPE-01 through PIPE-07)."""

import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from sklearn.linear_model import LogisticRegression, Ridge

from automl.prepare import (
    load_data,
    split_data,
    evaluate,
    get_baselines,
    build_preprocessor,
    get_data_summary,
    validate_metric,
    METRIC_MAP,
)


# -- PIPE-01: load_data ---------------------------------------------------

class TestLoadData:
    def test_load_data_classification(self, sample_classification_csv):
        X, y, task = load_data(sample_classification_csv, "target")
        assert isinstance(X, pd.DataFrame)
        assert isinstance(y, pd.Series)
        assert task == "classification"
        assert "target" not in X.columns
        assert len(X) == 200

    def test_load_data_regression(self, sample_regression_csv):
        X, y, task = load_data(sample_regression_csv, "target")
        assert task == "regression"
        assert "target" not in X.columns

    def test_load_data_int_classification(self, tmp_path):
        """Integer target with <=20 unique values should be classification."""
        rng = np.random.RandomState(42)
        df = pd.DataFrame({
            "feat1": rng.randn(100),
            "feat2": rng.randn(100),
            "target": rng.choice([1, 2, 3, 4, 5], size=100),
        })
        csv_path = tmp_path / "int_class.csv"
        df.to_csv(csv_path, index=False)
        _, _, task = load_data(csv_path, "target")
        assert task == "classification"


# -- PIPE-02: split_data --------------------------------------------------

class TestSplitData:
    def test_split_data(self, sample_classification_csv):
        X, y, task = load_data(sample_classification_csv, "target")
        X_work, X_holdout, y_work, y_holdout = split_data(X, y, task)
        total = len(X_work) + len(X_holdout)
        assert total == 200
        holdout_frac = len(X_holdout) / total
        assert 0.10 <= holdout_frac <= 0.20  # ~15%

    def test_holdout_split_no_overlap(self, sample_classification_csv):
        """Holdout and working sets must have no index overlap."""
        X, y, task = load_data(sample_classification_csv, "target")
        X_work, X_holdout, y_work, y_holdout = split_data(X, y, task)
        overlap = set(X_work.index) & set(X_holdout.index)
        assert len(overlap) == 0


# -- PIPE-03: evaluate ----------------------------------------------------

class TestEvaluate:
    def test_evaluate_classification(self, sample_classification_csv):
        X, y, task = load_data(sample_classification_csv, "target")
        preprocessor = build_preprocessor(X)
        X_proc = preprocessor.transform(X)
        mean, std = evaluate(LogisticRegression(max_iter=1000), X_proc, y, "accuracy", task)
        assert isinstance(mean, float)
        assert isinstance(std, float)
        assert 0.0 <= mean <= 1.0

    def test_evaluate_regression(self, sample_regression_csv):
        X, y, task = load_data(sample_regression_csv, "target")
        preprocessor = build_preprocessor(X)
        X_proc = preprocessor.transform(X)
        mean, std = evaluate(Ridge(), X_proc, y, "r2", task)
        assert isinstance(mean, float)
        assert isinstance(std, float)


# -- PIPE-04: get_baselines -----------------------------------------------

class TestBaselines:
    def test_baselines_classification(self, sample_classification_csv):
        X, y, task = load_data(sample_classification_csv, "target")
        preprocessor = build_preprocessor(X)
        X_proc = preprocessor.transform(X)
        baselines = get_baselines(X_proc, y, "accuracy", task)
        assert "most_frequent" in baselines
        assert "stratified" in baselines
        for key in baselines:
            assert "score" in baselines[key]
            assert "std" in baselines[key]

    def test_baselines_regression(self, sample_regression_csv):
        X, y, task = load_data(sample_regression_csv, "target")
        preprocessor = build_preprocessor(X)
        X_proc = preprocessor.transform(X)
        baselines = get_baselines(X_proc, y, "neg_root_mean_squared_error", task)
        assert "mean" in baselines
        assert "median" in baselines


# -- PIPE-05: build_preprocessor ------------------------------------------

class TestPreprocessor:
    def test_preprocess_no_nan(self, sample_csv_with_missing):
        X, y, task = load_data(sample_csv_with_missing, "target")
        preprocessor = build_preprocessor(X)
        X_proc = preprocessor.transform(X)
        assert not np.isnan(X_proc).any()

    def test_preprocess_categorical_ordinal(self, sample_classification_csv):
        """Categorical columns should be ordinal-encoded (not one-hot), preserving column count."""
        X, y, task = load_data(sample_classification_csv, "target")
        preprocessor = build_preprocessor(X)
        X_proc = preprocessor.transform(X)
        # 5 numeric + 2 categorical = 7 output columns (ordinal, not one-hot)
        assert X_proc.shape[1] == 7


# -- PIPE-06: get_data_summary -------------------------------------------

class TestDataSummary:
    def test_data_summary_classification(self, sample_classification_csv):
        X, y, task = load_data(sample_classification_csv, "target")
        summary = get_data_summary(X, y, task)
        assert "shape" in summary
        assert "dtypes" in summary
        assert "missing" in summary
        assert "target_distribution" in summary
        assert summary["shape"] == (200, 7)

    def test_data_summary_regression(self, sample_regression_csv):
        X, y, task = load_data(sample_regression_csv, "target")
        summary = get_data_summary(X, y, task)
        dist = summary["target_distribution"]
        for key in ("mean", "std", "min", "max"):
            assert key in dist


# -- PIPE-07: validate_metric --------------------------------------------

class TestValidateMetric:
    def test_validate_metric_auc(self):
        scoring, direction = validate_metric("auc", "classification")
        assert scoring == "roc_auc"
        assert direction == "maximize"

    def test_validate_metric_rmse(self):
        scoring, direction = validate_metric("rmse", "regression")
        assert scoring == "neg_root_mean_squared_error"
        assert direction == "maximize"

    def test_validate_metric_mismatch(self):
        with pytest.raises(ValueError):
            validate_metric("auc", "regression")

    def test_metric_map_exists(self):
        assert isinstance(METRIC_MAP, dict)
        assert len(METRIC_MAP) >= 10
