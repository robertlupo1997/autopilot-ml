"""Tests for FineTuningPlugin: scaffold, template_context, validate_config, and prepare utilities."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mlforge.config import Config
from mlforge.plugins import DomainPlugin, get_plugin, register_plugin


# ---------------------------------------------------------------------------
# FineTuningPlugin Protocol conformance
# ---------------------------------------------------------------------------


class TestFineTuningPluginProtocol:
    """FineTuningPlugin must satisfy DomainPlugin Protocol."""

    def test_isinstance_check(self):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        assert isinstance(plugin, DomainPlugin)

    def test_name_attribute(self):
        from mlforge.finetuning import FineTuningPlugin

        assert FineTuningPlugin().name == "finetuning"

    def test_frozen_files_attribute(self):
        from mlforge.finetuning import FineTuningPlugin

        assert FineTuningPlugin().frozen_files == ["prepare.py"]


# ---------------------------------------------------------------------------
# FineTuningPlugin.scaffold()
# ---------------------------------------------------------------------------


class TestFineTuningScaffold:
    """scaffold() must write prepare.py and train.py to target_dir."""

    def test_scaffold_creates_prepare_py(self, tmp_dir: Path):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        config = Config(
            domain="finetuning",
            metric="perplexity",
            direction="minimize",
            plugin_settings={"model_name": "meta-llama/Llama-3.2-1B"},
        )
        plugin.scaffold(tmp_dir, config)
        assert (tmp_dir / "prepare.py").exists()

    def test_scaffold_creates_train_py(self, tmp_dir: Path):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        config = Config(
            domain="finetuning",
            metric="perplexity",
            direction="minimize",
            plugin_settings={"model_name": "meta-llama/Llama-3.2-1B"},
        )
        plugin.scaffold(tmp_dir, config)
        assert (tmp_dir / "train.py").exists()


# ---------------------------------------------------------------------------
# FineTuningPlugin.validate_config()
# ---------------------------------------------------------------------------


class TestFineTuningValidateConfig:
    """validate_config() returns empty list for valid, error list for invalid."""

    @pytest.mark.parametrize(
        "metric",
        ["perplexity", "rouge1", "rougeL", "rouge2", "loss"],
    )
    def test_accepts_valid_ft_metrics(self, metric: str):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        config = Config(
            metric=metric,
            plugin_settings={"model_name": "meta-llama/Llama-3.2-1B"},
        )
        errors = plugin.validate_config(config)
        assert errors == []

    def test_rejects_unknown_metric(self):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        config = Config(
            metric="nonsense_metric",
            plugin_settings={"model_name": "meta-llama/Llama-3.2-1B"},
        )
        errors = plugin.validate_config(config)
        assert len(errors) > 0
        assert "nonsense_metric" in errors[0]

    def test_warns_missing_model_name(self):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        config = Config(metric="perplexity", plugin_settings={})
        errors = plugin.validate_config(config)
        assert any("model_name" in e for e in errors)


# ---------------------------------------------------------------------------
# FineTuningPlugin.template_context()
# ---------------------------------------------------------------------------


class TestFineTuningTemplateContext:
    """template_context() must return domain_rules with FT-specific rules."""

    def test_returns_domain_rules(self):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        config = Config(domain="finetuning", metric="perplexity")
        ctx = plugin.template_context(config)
        assert "domain_rules" in ctx
        assert isinstance(ctx["domain_rules"], list)
        assert len(ctx["domain_rules"]) > 0

    def test_returns_extra_sections(self):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        config = Config(domain="finetuning")
        ctx = plugin.template_context(config)
        assert "extra_sections" in ctx
        assert isinstance(ctx["extra_sections"], list)

    def test_rules_mention_lora(self):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        config = Config(domain="finetuning")
        ctx = plugin.template_context(config)
        rules_text = " ".join(ctx["domain_rules"]).lower()
        assert "lora" in rules_text

    def test_rules_mention_qlora(self):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        config = Config(domain="finetuning")
        ctx = plugin.template_context(config)
        rules_text = " ".join(ctx["domain_rules"]).lower()
        assert "qlora" in rules_text

    def test_rules_mention_vram(self):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        config = Config(domain="finetuning")
        ctx = plugin.template_context(config)
        rules_text = " ".join(ctx["domain_rules"]).lower()
        assert "vram" in rules_text

    def test_rules_mention_chat_template(self):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        config = Config(domain="finetuning")
        ctx = plugin.template_context(config)
        rules_text = " ".join(ctx["domain_rules"]).lower()
        assert "chat_template" in rules_text or "chat template" in rules_text

    def test_rules_mention_no_full_finetune(self):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        config = Config(domain="finetuning")
        ctx = plugin.template_context(config)
        rules_text = " ".join(ctx["domain_rules"]).lower()
        assert "never" in rules_text and "full" in rules_text


# ---------------------------------------------------------------------------
# Plugin registry integration
# ---------------------------------------------------------------------------


class TestFineTuningPluginRegistry:
    """FineTuningPlugin registers and retrieves via plugin registry."""

    def test_register_and_get(self):
        from mlforge.finetuning import FineTuningPlugin

        plugin = FineTuningPlugin()
        register_plugin(plugin)
        retrieved = get_plugin("finetuning")
        assert retrieved is plugin


# ---------------------------------------------------------------------------
# Lazy import verification
# ---------------------------------------------------------------------------


class TestFineTuningLazyImports:
    """Importing mlforge.finetuning must NOT import peft/trl/bitsandbytes."""

    def test_no_heavy_imports_at_module_level(self):
        # Remove mlforge.finetuning from cache to test fresh import
        mods_to_remove = [k for k in sys.modules if k.startswith("mlforge.finetuning")]
        saved = {}
        for mod in mods_to_remove:
            saved[mod] = sys.modules.pop(mod)

        # Block heavy deps -- if they get imported, it will raise ImportError
        blocked = {"peft": None, "trl": None, "bitsandbytes": None}
        with patch.dict("sys.modules", blocked):
            import importlib

            mod = importlib.import_module("mlforge.finetuning")
            assert hasattr(mod, "FineTuningPlugin")

        # Restore
        sys.modules.update(saved)
