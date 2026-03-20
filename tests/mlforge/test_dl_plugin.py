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


class TestPreparePyFunctions:
    """Tests for prepare.py functions with mocked heavy deps."""

    def test_prepare_contains_get_device_info(self):
        source = Path(__file__).parent.parent.parent / "src/mlforge/deeplearning/prepare.py"
        content = source.read_text()
        assert "def get_device_info" in content

    def test_prepare_contains_load_image_data(self):
        source = Path(__file__).parent.parent.parent / "src/mlforge/deeplearning/prepare.py"
        content = source.read_text()
        assert "def load_image_data" in content

    def test_prepare_contains_load_text_data(self):
        source = Path(__file__).parent.parent.parent / "src/mlforge/deeplearning/prepare.py"
        content = source.read_text()
        assert "def load_text_data" in content

    def test_get_device_info_returns_expected_keys(self):
        """Test get_device_info with mocked torch.cuda."""
        source = Path(__file__).parent.parent.parent / "src/mlforge/deeplearning/prepare.py"
        content = source.read_text()
        # Execute in isolated namespace with mocked torch
        ns = {}
        mock_torch = type(sys)("torch")
        mock_cuda = type(sys)("torch.cuda")
        mock_cuda.is_available = lambda: True
        mock_cuda.get_device_name = lambda x=0: "NVIDIA RTX 4090"
        mock_cuda.mem_get_info = lambda x=0: (20 * 1024**3, 24 * 1024**3)
        mock_torch.cuda = mock_cuda
        with patch.dict(sys.modules, {
            "torch": mock_torch,
            "torch.cuda": mock_cuda,
            "torchvision": type(sys)("torchvision"),
            "torchvision.transforms": type(sys)("torchvision.transforms"),
            "torchvision.datasets": type(sys)("torchvision.datasets"),
            "transformers": type(sys)("transformers"),
            "torch.utils": type(sys)("torch.utils"),
            "torch.utils.data": type(sys)("torch.utils.data"),
        }):
            exec(compile(content, str(source), "exec"), ns)
        result = ns["get_device_info"]()
        assert "device" in result
        assert "gpu_name" in result
        assert "vram_gb" in result
        assert result["device"] == "cuda"
        assert result["gpu_name"] == "NVIDIA RTX 4090"
        assert result["vram_gb"] == 24.0


class TestPyprojectOptionalDeps:
    """pyproject.toml has dl and ft optional dependency groups."""

    def test_dl_group_exists(self):
        toml_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        import tomllib
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        dl_deps = data.get("project", {}).get("optional-dependencies", {}).get("dl", [])
        assert len(dl_deps) > 0
        dep_names = [d.split(">")[0].split("<")[0].split("=")[0].strip() for d in dl_deps]
        assert "torch" in dep_names
        assert "torchvision" in dep_names
        assert "timm" in dep_names
        assert "transformers" in dep_names
        assert "datasets" in dep_names

    def test_ft_group_exists(self):
        toml_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        import tomllib
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        ft_deps = data.get("project", {}).get("optional-dependencies", {}).get("ft", [])
        assert len(ft_deps) > 0
        dep_names = [d.split(">")[0].split("<")[0].split("=")[0].strip() for d in ft_deps]
        assert "peft" in dep_names
        assert "trl" in dep_names
        assert "bitsandbytes" in dep_names
        assert "evaluate" in dep_names
        assert "rouge-score" in dep_names
        assert "transformers" in dep_names
        assert "datasets" in dep_names


class TestDLTrainTemplate:
    """dl_train.py.j2 renders valid Python with expected features."""

    def _render(self, task="image_classification", metric="accuracy"):
        from mlforge.templates import get_template_env

        env = get_template_env()
        template = env.get_template("dl_train.py.j2")
        return template.render(
            task=task,
            data_dir="data",
            data_path="data.csv",
            metric=metric,
            time_budget=3600,
            img_size=224,
            batch_size=32,
            model_name="resnet50" if task == "image_classification" else "distilbert-base-uncased",
        )

    def test_renders_valid_python_image(self):
        code = self._render(task="image_classification")
        compile(code, "<dl_train_image>", "exec")

    def test_renders_valid_python_text(self):
        code = self._render(task="text_classification")
        compile(code, "<dl_train_text>", "exec")

    def test_renders_valid_python_custom(self):
        code = self._render(task="custom")
        compile(code, "<dl_train_custom>", "exec")

    def test_contains_time_budget_sec(self):
        code = self._render()
        assert "TIME_BUDGET_SEC" in code

    def test_contains_early_stopping(self):
        code = self._render()
        assert "patience" in code.lower()
        assert "best_val_loss" in code

    def test_contains_gradient_clipping(self):
        code = self._render()
        assert "clip_grad_norm_" in code

    def test_contains_lr_scheduler(self):
        code = self._render()
        assert "ReduceLROnPlateau" in code

    def test_contains_wall_clock_check(self):
        code = self._render()
        assert "time.time()" in code or "TIME_BUDGET_SEC" in code
        # Verify time budget break logic
        assert "TIME_BUDGET_SEC" in code
        assert "break" in code

    def test_image_classification_uses_timm(self):
        code = self._render(task="image_classification")
        assert "timm" in code

    def test_text_classification_uses_transformers(self):
        code = self._render(task="text_classification")
        assert "AutoModelForSequenceClassification" in code

    def test_custom_has_todo_placeholder(self):
        code = self._render(task="custom")
        assert "TODO" in code

    def test_saves_best_model(self):
        code = self._render()
        assert "best_model.pt" in code

    def test_outputs_json_result(self):
        code = self._render()
        assert "json.dumps" in code


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
