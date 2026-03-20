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


# ---------------------------------------------------------------------------
# prepare.py: get_vram_info (mocked torch.cuda)
# ---------------------------------------------------------------------------


class TestGetVramInfo:
    """get_vram_info() returns VRAM details with quantization recommendation."""

    def test_returns_expected_keys_with_gpu(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "NVIDIA RTX 4090"
        mock_torch.cuda.get_device_properties.return_value = MagicMock(
            total_mem=24 * 1024**3  # 24 GB
        )
        with patch.dict("sys.modules", {"torch": mock_torch}):
            from mlforge.finetuning.prepare import get_vram_info

            info = get_vram_info()
        assert info["device"] == "cuda"
        assert info["gpu_name"] == "NVIDIA RTX 4090"
        assert abs(info["vram_gb"] - 24.0) < 0.1
        assert info["recommend_quantization"] is False

    def test_recommends_quantization_for_low_vram(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "NVIDIA RTX 3060"
        mock_torch.cuda.get_device_properties.return_value = MagicMock(
            total_mem=12 * 1024**3  # 12 GB
        )
        with patch.dict("sys.modules", {"torch": mock_torch}):
            from mlforge.finetuning.prepare import get_vram_info

            info = get_vram_info()
        assert info["recommend_quantization"] is True

    def test_cpu_fallback(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        with patch.dict("sys.modules", {"torch": mock_torch}):
            from mlforge.finetuning.prepare import get_vram_info

            info = get_vram_info()
        assert info["device"] == "cpu"
        assert info["gpu_name"] is None
        assert info["vram_gb"] == 0.0
        assert info["recommend_quantization"] is True


# ---------------------------------------------------------------------------
# prepare.py: format_dataset (mocked transformers/datasets)
# ---------------------------------------------------------------------------


class TestFormatDataset:
    """format_dataset() loads data and applies tokenizer."""

    def test_loads_json_and_tokenizes(self, tmp_dir: Path):
        import json

        # Create a small JSON dataset
        data = [
            {"instruction": "Say hello", "output": "Hello!"},
            {"instruction": "Say goodbye", "output": "Goodbye!"},
            {"instruction": "Count", "output": "1, 2, 3"},
            {"instruction": "Greet", "output": "Hi there"},
            {"instruction": "Farewell", "output": "See you"},
            {"instruction": "Sum", "output": "1+1=2"},
            {"instruction": "Name", "output": "I am AI"},
            {"instruction": "Help", "output": "Sure"},
            {"instruction": "Thanks", "output": "Welcome"},
            {"instruction": "Bye", "output": "Later"},
        ]
        data_path = tmp_dir / "data.json"
        data_path.write_text(json.dumps(data))

        # Mock tokenizer
        mock_tokenizer = MagicMock()
        mock_tokenizer.apply_chat_template.return_value = "formatted text"
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = "</s>"

        mock_auto_tokenizer = MagicMock()
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        mock_transformers = MagicMock()
        mock_transformers.AutoTokenizer = mock_auto_tokenizer

        with patch.dict("sys.modules", {"transformers": mock_transformers}):
            from mlforge.finetuning.prepare import format_dataset

            result = format_dataset(
                data_path=str(data_path),
                tokenizer_name="test-model",
                max_length=128,
            )

        assert "train" in result
        assert "eval" in result
        assert "num_samples" in result

    def test_loads_csv_data(self, tmp_dir: Path):
        import csv

        csv_path = tmp_dir / "data.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["instruction", "output"])
            writer.writeheader()
            for i in range(20):
                writer.writerow({"instruction": f"task {i}", "output": f"result {i}"})

        mock_tokenizer = MagicMock()
        mock_tokenizer.apply_chat_template.return_value = "formatted"
        mock_tokenizer.pad_token = "<pad>"

        mock_auto_tokenizer = MagicMock()
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        mock_transformers = MagicMock()
        mock_transformers.AutoTokenizer = mock_auto_tokenizer

        with patch.dict("sys.modules", {"transformers": mock_transformers}):
            from mlforge.finetuning.prepare import format_dataset

            result = format_dataset(
                data_path=str(csv_path),
                tokenizer_name="test-model",
            )

        assert len(result["train"]) + len(result["eval"]) == 20


# ---------------------------------------------------------------------------
# prepare.py: create_train_eval_split
# ---------------------------------------------------------------------------


class TestCreateTrainEvalSplit:
    """create_train_eval_split() returns 90/10 split with reproducible seed."""

    def test_default_90_10_split(self):
        from mlforge.finetuning.prepare import create_train_eval_split

        dataset = list(range(100))
        train, eval_ = create_train_eval_split(dataset)
        assert len(train) == 90
        assert len(eval_) == 10

    def test_custom_fraction(self):
        from mlforge.finetuning.prepare import create_train_eval_split

        dataset = list(range(100))
        train, eval_ = create_train_eval_split(dataset, eval_fraction=0.2)
        assert len(train) == 80
        assert len(eval_) == 20

    def test_reproducible(self):
        from mlforge.finetuning.prepare import create_train_eval_split

        dataset = list(range(50))
        train1, eval1 = create_train_eval_split(dataset)
        train2, eval2 = create_train_eval_split(dataset)
        assert train1 == train2
        assert eval1 == eval2

    def test_no_overlap(self):
        from mlforge.finetuning.prepare import create_train_eval_split

        dataset = list(range(100))
        train, eval_ = create_train_eval_split(dataset)
        assert set(train).isdisjoint(set(eval_))


# ---------------------------------------------------------------------------
# ft_train.py.j2 template rendering
# ---------------------------------------------------------------------------


class TestFtTrainTemplate:
    """ft_train.py.j2 renders valid Python with QLoRA, SFTTrainer, and evaluation."""

    @pytest.fixture
    def rendered_template(self):
        from mlforge.templates import get_template_env

        env = get_template_env()
        template = env.get_template("ft_train.py.j2")
        return template.render(
            model_name="meta-llama/Llama-3.2-1B",
            lora_r=16,
            lora_alpha=16,
            metric="perplexity",
            max_length=512,
            batch_size=4,
            learning_rate=2e-4,
            num_epochs=3,
            dataset_format="instruction",
        )

    def test_renders_valid_python(self, rendered_template):
        compile(rendered_template, "train.py", "exec")

    def test_contains_bitsandbytes_config(self, rendered_template):
        assert "BitsAndBytesConfig" in rendered_template
        assert "load_in_4bit=True" in rendered_template
        assert 'bnb_4bit_quant_type="nf4"' in rendered_template

    def test_contains_lora_config(self, rendered_template):
        assert "LoraConfig" in rendered_template
        # LoRA r and alpha are set via constants: LORA_R = 16, LORA_ALPHA = 16
        assert "LORA_R = 16" in rendered_template
        assert "LORA_ALPHA = 16" in rendered_template
        assert "r=LORA_R" in rendered_template
        assert "lora_alpha=LORA_ALPHA" in rendered_template

    def test_contains_sft_trainer(self, rendered_template):
        assert "SFTTrainer" in rendered_template

    def test_contains_perplexity_evaluation(self, rendered_template):
        assert "math.exp" in rendered_template

    def test_contains_rouge_evaluation(self, rendered_template):
        assert "rouge" in rendered_template.lower()

    def test_contains_save_pretrained(self, rendered_template):
        assert "save_pretrained" in rendered_template

    def test_contains_json_output(self, rendered_template):
        assert "json.dumps" in rendered_template

    def test_contains_gradient_checkpointing(self, rendered_template):
        assert "gradient_checkpointing_enable" in rendered_template

    def test_renders_with_different_model(self):
        from mlforge.templates import get_template_env

        env = get_template_env()
        template = env.get_template("ft_train.py.j2")
        content = template.render(
            model_name="mistralai/Mistral-7B-v0.3",
            lora_r=32,
            lora_alpha=64,
            metric="rouge1",
            max_length=1024,
            batch_size=2,
            learning_rate=1e-4,
            num_epochs=5,
            dataset_format="instruction",
        )
        compile(content, "train.py", "exec")
        assert "mistralai/Mistral-7B-v0.3" in content
        assert "LORA_R = 32" in content
