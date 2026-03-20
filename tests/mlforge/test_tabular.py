"""Tests for TabularPlugin: scaffold, template_context, validate_config, and data utilities."""

from __future__ import annotations

import pytest
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.datasets import make_classification, make_regression

from mlforge.config import Config
from mlforge.plugins import DomainPlugin


# ---------------------------------------------------------------------------
# TabularPlugin Protocol conformance
# ---------------------------------------------------------------------------


class TestTabularPluginProtocol:
    """TabularPlugin must satisfy DomainPlugin Protocol."""

    def test_isinstance_check(self):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        assert isinstance(plugin, DomainPlugin)

    def test_name_attribute(self):
        from mlforge.tabular import TabularPlugin

        assert TabularPlugin().name == "tabular"

    def test_frozen_files_attribute(self):
        from mlforge.tabular import TabularPlugin

        assert TabularPlugin().frozen_files == ["prepare.py"]


# ---------------------------------------------------------------------------
# TabularPlugin.scaffold()
# ---------------------------------------------------------------------------


class TestScaffold:
    """scaffold() must write prepare.py and train.py to target_dir."""

    def test_scaffold_creates_prepare_py(self, tmp_dir: Path):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config(plugin_settings={"csv_path": "data.csv", "target_column": "y"})
        plugin.scaffold(tmp_dir, config)
        assert (tmp_dir / "prepare.py").exists()

    def test_scaffold_creates_train_py(self, tmp_dir: Path):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config(plugin_settings={"csv_path": "data.csv", "target_column": "y"})
        plugin.scaffold(tmp_dir, config)
        assert (tmp_dir / "train.py").exists()

    def test_scaffold_train_py_is_valid_python(self, tmp_dir: Path):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config(plugin_settings={"csv_path": "data.csv", "target_column": "y"})
        plugin.scaffold(tmp_dir, config)
        content = (tmp_dir / "train.py").read_text()
        compile(content, "train.py", "exec")  # Raises SyntaxError if invalid

    def test_scaffold_prepare_py_has_load_data(self, tmp_dir: Path):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config()
        plugin.scaffold(tmp_dir, config)
        content = (tmp_dir / "prepare.py").read_text()
        assert "def load_data" in content

    def test_scaffold_train_py_has_optuna(self, tmp_dir: Path):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config(plugin_settings={"csv_path": "data.csv", "target_column": "y"})
        plugin.scaffold(tmp_dir, config)
        content = (tmp_dir / "train.py").read_text()
        assert "optuna" in content


# ---------------------------------------------------------------------------
# TabularPlugin.template_context()
# ---------------------------------------------------------------------------


class TestTemplateContext:
    """template_context() must return domain_rules and extra_sections."""

    def test_returns_domain_rules(self):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config()
        ctx = plugin.template_context(config)
        assert "domain_rules" in ctx
        assert isinstance(ctx["domain_rules"], list)
        assert len(ctx["domain_rules"]) > 0

    def test_returns_extra_sections(self):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config()
        ctx = plugin.template_context(config)
        assert "extra_sections" in ctx
        assert isinstance(ctx["extra_sections"], list)

    def test_has_dual_baseline_rule(self):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config()
        ctx = plugin.template_context(config)
        rules_text = " ".join(ctx["domain_rules"]).lower()
        assert "baseline" in rules_text

    def test_has_frozen_prepare_rule(self):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config()
        ctx = plugin.template_context(config)
        rules_text = " ".join(ctx["domain_rules"]).lower()
        assert "prepare.py" in rules_text

    def test_classification_uses_stratifiedkfold(self):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config(plugin_settings={"task": "classification"})
        ctx = plugin.template_context(config)
        rules_text = " ".join(ctx["domain_rules"]).lower()
        assert "stratifiedkfold" in rules_text.replace(" ", "").lower() or "stratified" in rules_text

    def test_regression_uses_kfold(self):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config(plugin_settings={"task": "regression"})
        ctx = plugin.template_context(config)
        rules_text = " ".join(ctx["domain_rules"])
        # Should mention KFold but not StratifiedKFold
        assert "KFold" in rules_text


# ---------------------------------------------------------------------------
# TabularPlugin.validate_config()
# ---------------------------------------------------------------------------


class TestValidateConfig:
    """validate_config() returns empty list for valid, error list for invalid."""

    @pytest.mark.parametrize(
        "metric",
        ["accuracy", "rmse", "r2", "f1", "auc", "roc_auc", "f1_weighted", "mae", "mse", "precision", "recall", "log_loss"],
    )
    def test_accepts_valid_metrics(self, metric: str):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config(metric=metric)
        errors = plugin.validate_config(config)
        assert errors == []

    def test_rejects_unknown_metric(self):
        from mlforge.tabular import TabularPlugin

        plugin = TabularPlugin()
        config = Config(metric="nonsense_metric")
        errors = plugin.validate_config(config)
        assert len(errors) > 0
        assert "nonsense_metric" in errors[0]


# ---------------------------------------------------------------------------
# prepare.py: load_data
# ---------------------------------------------------------------------------


class TestLoadData:
    """load_data() reads CSV and Parquet files."""

    def test_load_csv(self, tmp_dir: Path):
        from mlforge.tabular.prepare import load_data

        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        csv_path = tmp_dir / "test.csv"
        df.to_csv(csv_path, index=False)
        result = load_data(csv_path)
        assert result.shape == (3, 2)

    def test_load_parquet(self, tmp_dir: Path):
        from mlforge.tabular.prepare import load_data

        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        pq_path = tmp_dir / "test.parquet"
        df.to_parquet(pq_path, index=False)
        result = load_data(pq_path)
        assert result.shape == (3, 2)

    def test_load_pq_suffix(self, tmp_dir: Path):
        from mlforge.tabular.prepare import load_data

        df = pd.DataFrame({"x": [10, 20]})
        pq_path = tmp_dir / "data.pq"
        df.to_parquet(pq_path, index=False)
        result = load_data(pq_path)
        assert result.shape == (2, 1)


# ---------------------------------------------------------------------------
# prepare.py: split_data
# ---------------------------------------------------------------------------


class TestSplitData:
    """split_data() returns correctly shaped train/test splits."""

    def test_split_shapes(self):
        from mlforge.tabular.prepare import split_data

        df = pd.DataFrame({"a": range(100), "b": range(100), "target": range(100)})
        X_train, X_test, y_train, y_test = split_data(df, "target", test_size=0.2)
        assert len(X_train) == 80
        assert len(X_test) == 20
        assert len(y_train) == 80
        assert len(y_test) == 20

    def test_split_excludes_target(self):
        from mlforge.tabular.prepare import split_data

        df = pd.DataFrame({"a": range(10), "target": range(10)})
        X_train, X_test, y_train, y_test = split_data(df, "target")
        assert "target" not in X_train.columns


# ---------------------------------------------------------------------------
# prepare.py: build_preprocessor
# ---------------------------------------------------------------------------


class TestBuildPreprocessor:
    """build_preprocessor() returns a ColumnTransformer."""

    def test_returns_column_transformer(self):
        from sklearn.compose import ColumnTransformer

        from mlforge.tabular.prepare import build_preprocessor

        X = pd.DataFrame({"num": [1.0, 2.0, 3.0], "cat": ["a", "b", "a"]})
        preprocessor = build_preprocessor(X)
        assert isinstance(preprocessor, ColumnTransformer)

    def test_preprocessor_fits_and_transforms(self):
        from mlforge.tabular.prepare import build_preprocessor

        X = pd.DataFrame({"num": [1.0, 2.0, 3.0, 4.0], "cat": ["a", "b", "a", "b"]})
        preprocessor = build_preprocessor(X)
        result = preprocessor.fit_transform(X)
        assert result.shape[0] == 4


# ---------------------------------------------------------------------------
# prepare.py: evaluate
# ---------------------------------------------------------------------------


class TestEvaluate:
    """evaluate() scores a model using cross-validation."""

    def test_evaluate_classification(self):
        from sklearn.linear_model import LogisticRegression

        from mlforge.tabular.prepare import evaluate

        X, y = make_classification(n_samples=100, n_features=5, random_state=42)
        X = pd.DataFrame(X)
        model = LogisticRegression(max_iter=200)
        result = evaluate(model, X, y, scoring="accuracy", task="classification")
        assert "mean" in result
        assert "std" in result
        assert 0 <= result["mean"] <= 1

    def test_evaluate_regression(self):
        from sklearn.linear_model import Ridge

        from mlforge.tabular.prepare import evaluate

        X, y = make_regression(n_samples=100, n_features=5, random_state=42)
        X = pd.DataFrame(X)
        model = Ridge()
        result = evaluate(model, X, y, scoring="r2", task="regression")
        assert "mean" in result
        assert "std" in result


# ---------------------------------------------------------------------------
# prepare.py: get_data_summary
# ---------------------------------------------------------------------------


class TestGetDataSummary:
    """get_data_summary() returns shape, dtypes, and target info."""

    def test_summary_has_shape(self):
        from mlforge.tabular.prepare import get_data_summary

        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"], "target": [0, 1]})
        summary = get_data_summary(df, "target")
        assert "shape" in summary
        assert summary["shape"] == (2, 3)

    def test_summary_has_feature_types(self):
        from mlforge.tabular.prepare import get_data_summary

        df = pd.DataFrame({"a": [1.0, 2.0], "b": ["x", "y"], "target": [0, 1]})
        summary = get_data_summary(df, "target")
        assert "feature_types" in summary


# ---------------------------------------------------------------------------
# prepare.py: temporal_split
# ---------------------------------------------------------------------------


class TestTemporalSplit:
    """temporal_split() produces walk-forward CV splits respecting time order."""

    def test_splits_respect_time_order(self):
        from mlforge.tabular.prepare import temporal_split

        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=100),
            "value": range(100),
        })
        splits = temporal_split(df, "date", n_splits=3)
        assert len(splits) == 3
        for train_idx, test_idx in splits:
            # All train indices should be before all test indices
            assert max(train_idx) < min(test_idx)

    def test_no_shuffle(self):
        from mlforge.tabular.prepare import temporal_split

        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=50),
            "value": range(50),
        })
        splits = temporal_split(df, "date", n_splits=2)
        for train_idx, test_idx in splits:
            # Train and test should be contiguous and ordered
            assert list(train_idx) == sorted(train_idx)
            assert list(test_idx) == sorted(test_idx)


# ---------------------------------------------------------------------------
# prepare.py: validate_no_leakage
# ---------------------------------------------------------------------------


class TestValidateNoLeakage:
    """validate_no_leakage() checks for potential leakage indicators."""

    def test_detects_target_in_features(self):
        from mlforge.tabular.prepare import validate_no_leakage

        df = pd.DataFrame({"target": [1, 2, 3], "target_encoded": [0.5, 0.8, 0.3], "x": [1, 2, 3]})
        warnings = validate_no_leakage(df, "target")
        assert len(warnings) > 0

    def test_clean_data_no_warnings(self):
        from mlforge.tabular.prepare import validate_no_leakage

        df = pd.DataFrame({"feature_a": [1, 2, 3], "feature_b": [4, 5, 6], "target": [0, 1, 0]})
        warnings = validate_no_leakage(df, "target")
        assert len(warnings) == 0
