"""Tests for the DeepLearningPlugin domain plugin.

Covers DomainPlugin Protocol conformance, config validation,
template context, scaffold, lazy imports, and prepare.py functions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from mlforge.config import Config
from mlforge.plugins import DomainPlugin, get_plugin, register_plugin


class TestDeepLearningPluginProtocol:
    """DomainPlugin Protocol conformance and basic attributes."""

    def test_satisfies_domain_plugin_protocol(self):
        from mlforge.deeplearning import DeepLearningPlugin

        plugin = DeepLearningPlugin()
        assert isinstance(plugin, DomainPlugin)

    def test_name_is_deeplearning(self):
        from mlforge.deeplearning import DeepLearningPlugin

        plugin = DeepLearningPlugin()
        assert plugin.name == "deeplearning"

    def test_frozen_files_is_prepare(self):
        from mlforge.deeplearning import DeepLearningPlugin

        plugin = DeepLearningPlugin()
        assert plugin.frozen_files == ["prepare.py"]


class TestDeepLearningPluginScaffold:
    """scaffold() creates prepare.py and train.py."""

    def test_scaffold_creates_prepare_and_train(self, tmp_path):
        from mlforge.deeplearning import DeepLearningPlugin

        plugin = DeepLearningPlugin()
        config = Config(
            domain="deeplearning",
            metric="accuracy",
            plugin_settings={"task": "image_classification"},
        )
        plugin.scaffold(tmp_path, config)
        assert (tmp_path / "prepare.py").exists()
        assert (tmp_path / "train.py").exists()


class TestDeepLearningPluginValidateConfig:
    """validate_config() checks metrics and task types."""

    def _make_config(self, metric="accuracy", task=None):
        settings = {}
        if task is not None:
            settings["task"] = task
        return Config(domain="deeplearning", metric=metric, plugin_settings=settings)

    @pytest.mark.parametrize("metric", ["accuracy", "f1", "f1_weighted", "loss"])
    def test_valid_metrics_return_no_errors(self, metric):
        from mlforge.deeplearning import DeepLearningPlugin

        plugin = DeepLearningPlugin()
        errors = plugin.validate_config(self._make_config(metric=metric))
        assert errors == []

    def test_unknown_metric_returns_error(self):
        from mlforge.deeplearning import DeepLearningPlugin

        plugin = DeepLearningPlugin()
        errors = plugin.validate_config(self._make_config(metric="rmse"))
        assert len(errors) == 1
        assert "rmse" in errors[0].lower()

    @pytest.mark.parametrize(
        "task", ["image_classification", "text_classification", "custom"]
    )
    def test_valid_tasks_return_no_errors(self, task):
        from mlforge.deeplearning import DeepLearningPlugin

        plugin = DeepLearningPlugin()
        errors = plugin.validate_config(self._make_config(task=task))
        assert errors == []

    def test_unknown_task_returns_error(self):
        from mlforge.deeplearning import DeepLearningPlugin

        plugin = DeepLearningPlugin()
        errors = plugin.validate_config(self._make_config(task="foo"))
        assert len(errors) == 1
        assert "foo" in errors[0].lower()


class TestDeepLearningPluginTemplateContext:
    """template_context() returns DL-specific domain rules."""

    def test_returns_domain_rules_list(self):
        from mlforge.deeplearning import DeepLearningPlugin

        plugin = DeepLearningPlugin()
        config = Config(domain="deeplearning", metric="accuracy")
        ctx = plugin.template_context(config)
        assert "domain_rules" in ctx
        assert isinstance(ctx["domain_rules"], list)
        assert len(ctx["domain_rules"]) > 0

    def test_rules_mention_key_concepts(self):
        from mlforge.deeplearning import DeepLearningPlugin

        plugin = DeepLearningPlugin()
        config = Config(domain="deeplearning", metric="accuracy")
        ctx = plugin.template_context(config)
        rules_text = " ".join(ctx["domain_rules"]).lower()
        assert "timm" in rules_text
        assert "transformers" in rules_text
        assert "frozen" in rules_text or "prepare.py" in rules_text
        assert "mixed precision" in rules_text
        assert "early stopping" in rules_text
        assert "gradient clipping" in rules_text or "clip_grad_norm" in rules_text


class TestDeepLearningPluginRegistry:
    """register_plugin + get_plugin integration."""

    def test_register_and_get(self):
        from mlforge.deeplearning import DeepLearningPlugin

        plugin = DeepLearningPlugin()
        register_plugin(plugin)
        retrieved = get_plugin("deeplearning")
        assert retrieved is plugin


class TestDeepLearningLazyImports:
    """Importing mlforge.deeplearning must NOT import torch."""

    def test_import_without_torch(self):
        # Remove cached module if already imported
        mods_to_remove = [
            k for k in sys.modules if k.startswith("mlforge.deeplearning")
        ]
        for m in mods_to_remove:
            del sys.modules[m]

        # Block torch from being imported
        with patch.dict(sys.modules, {"torch": None}):
            # This import must succeed because no module-level torch import
            import importlib

            mod = importlib.import_module("mlforge.deeplearning")
            assert hasattr(mod, "DeepLearningPlugin")
