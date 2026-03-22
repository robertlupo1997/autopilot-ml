"""Tests for mlforge.profiler -- dataset profiling and auto-detection."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mlforge.profiler import _detect_date_columns, profile_dataset


class TestRegressionDetection:
    """Numeric target with >20 unique values detected as regression."""

    def test_numeric_target_many_unique_is_regression(self):
        df = pd.DataFrame({
            "feature1": range(100),
            "feature2": np.random.randn(100),
            "target": np.random.randn(100),
        })
        profile = profile_dataset(df, "target")
        assert profile.task == "regression"

    def test_regression_metric_is_r2(self):
        df = pd.DataFrame({
            "feature1": range(100),
            "target": np.random.randn(100),
        })
        profile = profile_dataset(df, "target")
        assert profile.metric == "r2"

    def test_regression_direction_is_maximize(self):
        df = pd.DataFrame({
            "feature1": range(100),
            "target": np.random.randn(100),
        })
        profile = profile_dataset(df, "target")
        assert profile.direction == "maximize"


class TestClassificationDetection:
    """String/categorical or low-cardinality numeric targets -> classification."""

    def test_string_target_is_classification(self):
        df = pd.DataFrame({
            "feature1": range(50),
            "target": ["cat", "dog"] * 25,
        })
        profile = profile_dataset(df, "target")
        assert profile.task == "classification"

    def test_binary_classification_metric_is_accuracy(self):
        df = pd.DataFrame({
            "feature1": range(50),
            "target": ["cat", "dog"] * 25,
        })
        profile = profile_dataset(df, "target")
        assert profile.metric == "accuracy"

    def test_multiclass_metric_is_f1_weighted(self):
        df = pd.DataFrame({
            "feature1": range(60),
            "target": ["cat", "dog", "bird"] * 20,
        })
        profile = profile_dataset(df, "target")
        assert profile.metric == "f1_weighted"

    def test_numeric_low_cardinality_is_classification(self):
        df = pd.DataFrame({
            "feature1": range(100),
            "target": np.random.choice([0, 1, 2], size=100),
        })
        profile = profile_dataset(df, "target")
        assert profile.task == "classification"

    def test_numeric_exactly_20_unique_is_classification(self):
        df = pd.DataFrame({
            "feature1": range(100),
            "target": [i % 20 for i in range(100)],
        })
        profile = profile_dataset(df, "target")
        assert profile.task == "classification"


class TestDateColumnDetection:
    """Date columns detected from dtype or parseable string columns."""

    def test_datetime64_column_detected(self):
        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=30),
            "target": range(30),
        })
        result = _detect_date_columns(df, ["date"])
        assert "date" in result

    def test_iso_string_column_detected(self):
        dates = [f"2020-01-{i:02d}" for i in range(1, 21)]
        df = pd.DataFrame({
            "date_str": dates,
            "target": range(20),
        })
        result = _detect_date_columns(df, ["date_str"])
        assert "date_str" in result

    def test_non_date_string_not_detected(self):
        df = pd.DataFrame({
            "name": ["alice", "bob", "charlie"] * 10,
            "target": range(30),
        })
        result = _detect_date_columns(df, ["name"])
        assert "name" not in result

    def test_profile_includes_detected_date_columns(self):
        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=50),
            "feature": range(50),
            "target": np.random.randn(50),
        })
        profile = profile_dataset(df, "target")
        assert "date" in profile.date_columns


class TestProfileStatistics:
    """Profile reports correct data characteristics."""

    def test_n_rows_correct(self):
        df = pd.DataFrame({
            "a": range(42),
            "b": range(42),
            "target": np.random.randn(42),
        })
        profile = profile_dataset(df, "target")
        assert profile.n_rows == 42

    def test_n_features_excludes_target(self):
        df = pd.DataFrame({
            "a": range(10),
            "b": range(10),
            "c": ["x"] * 10,
            "target": range(10),
        })
        profile = profile_dataset(df, "target")
        assert profile.n_features == 3

    def test_numeric_features_identified(self):
        df = pd.DataFrame({
            "num1": [1.0, 2.0, 3.0],
            "num2": [4, 5, 6],
            "cat": ["a", "b", "c"],
            "target": [0, 1, 0],
        })
        profile = profile_dataset(df, "target")
        assert "num1" in profile.numeric_features
        assert "num2" in profile.numeric_features
        assert "cat" not in profile.numeric_features

    def test_categorical_features_identified(self):
        df = pd.DataFrame({
            "num": [1.0, 2.0, 3.0],
            "cat": ["a", "b", "c"],
            "target": [0, 1, 0],
        })
        profile = profile_dataset(df, "target")
        assert "cat" in profile.categorical_features
        assert "num" not in profile.categorical_features

    def test_missing_pct_calculated(self):
        df = pd.DataFrame({
            "a": [1, None, 3, None],
            "b": [1, 2, 3, 4],
            "target": [0, 1, 0, 1],
        })
        profile = profile_dataset(df, "target")
        # 2 missing out of 12 total cells = ~16.67%
        assert 16.0 < profile.missing_pct < 17.0

    def test_regression_target_stats(self):
        df = pd.DataFrame({
            "a": range(100),
            "target": np.random.randn(100),
        })
        profile = profile_dataset(df, "target")
        assert profile.target_stats["type"] == "regression"
        assert "mean" in profile.target_stats
        assert "std" in profile.target_stats

    def test_classification_target_stats(self):
        df = pd.DataFrame({
            "a": range(50),
            "target": ["cat", "dog"] * 25,
        })
        profile = profile_dataset(df, "target")
        assert profile.target_stats["type"] == "classification"
        assert profile.target_stats["n_classes"] == 2
        assert "distribution" in profile.target_stats


class TestLeakageWarnings:
    """Leakage warnings populated by profile_dataset when leaky columns exist."""

    def test_name_based_leakage_detected(self):
        """Column containing target name triggers leakage warning."""
        df = pd.DataFrame({
            "feature1": np.random.randn(50),
            "price_encoded": np.random.randn(50),
            "price": np.random.randn(50),
        })
        profile = profile_dataset(df, "price")
        assert len(profile.leakage_warnings) > 0
        assert any("price_encoded" in w for w in profile.leakage_warnings)

    def test_high_correlation_leakage_detected(self):
        """Column with >0.99 correlation to target triggers leakage warning."""
        rng = np.random.default_rng(42)
        target = rng.normal(100, 10, size=50)
        df = pd.DataFrame({
            "feature1": rng.normal(0, 1, size=50),
            "leaky_col": target * 1.0001,
            "target": target,
        })
        profile = profile_dataset(df, "target")
        assert len(profile.leakage_warnings) > 0
        assert any("correlation" in w for w in profile.leakage_warnings)

    def test_clean_data_no_false_positives(self):
        """Clean dataset returns empty leakage_warnings."""
        rng = np.random.default_rng(99)
        df = pd.DataFrame({
            "feature1": rng.normal(0, 1, size=50),
            "feature2": rng.normal(5, 2, size=50),
            "target": rng.normal(10, 3, size=50),
        })
        profile = profile_dataset(df, "target")
        assert profile.leakage_warnings == []


class TestInputValidation:
    """profile_dataset validates inputs and raises ValueError for bad data."""

    def test_empty_df_raises(self):
        df = pd.DataFrame({"a": pd.Series(dtype=float), "target": pd.Series(dtype=float)})
        with pytest.raises(ValueError, match="empty"):
            profile_dataset(df, "target")

    def test_missing_target_column_raises(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        with pytest.raises(ValueError, match="not found"):
            profile_dataset(df, "nonexistent")

    def test_all_nan_target_raises(self):
        df = pd.DataFrame({"a": [1, 2, 3], "target": [float("nan")] * 3})
        with pytest.raises(ValueError, match="entirely NaN"):
            profile_dataset(df, "target")

    def test_single_column_raises(self):
        df = pd.DataFrame({"target": [1, 2, 3]})
        with pytest.raises(ValueError, match="only one column"):
            profile_dataset(df, "target")

    def test_all_nan_features_raises(self):
        df = pd.DataFrame({
            "a": [float("nan")] * 3,
            "b": [float("nan")] * 3,
            "target": [1, 2, 3],
        })
        with pytest.raises(ValueError, match="entirely NaN"):
            profile_dataset(df, "target")

    def test_valid_df_does_not_raise(self):
        df = pd.DataFrame({"a": [1, 2, 3], "target": [0, 1, 0]})
        profile = profile_dataset(df, "target")
        assert profile.n_rows == 3
