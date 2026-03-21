"""LLM fine-tuning domain plugin for mlforge.

Implements the DomainPlugin Protocol for LoRA/QLoRA fine-tuning of
open language models via PEFT/TRL. All heavy dependencies (peft, trl,
bitsandbytes, transformers) are lazy-imported inside methods to avoid
requiring them at import time.
"""

from __future__ import annotations

from pathlib import Path

from mlforge.config import Config


class FineTuningPlugin:
    """Fine-tuning plugin implementing DomainPlugin Protocol.

    Provides scaffolding for LLM fine-tuning experiments with frozen
    prepare.py (dataset formatting, VRAM info) and mutable train.py
    (QLoRA training script).
    """

    name: str = "finetuning"
    frozen_files: list[str] = ["prepare.py"]

    _VALID_METRICS: set[str] = {
        "perplexity", "rouge1", "rougeL", "rouge2", "loss",
    }

    def scaffold(self, target_dir: Path, config: Config) -> None:
        """Create frozen prepare.py and mutable train.py in target_dir.

        prepare.py is copied from the mlforge.finetuning.prepare source module.
        train.py is rendered from the ft_train.py.j2 Jinja2 template.

        Args:
            target_dir: Directory to write files into.
            config: Config with plugin_settings for template rendering.
        """
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Copy frozen prepare.py from source module
        prepare_source = Path(__file__).parent / "prepare.py"
        (target_dir / "prepare.py").write_text(prepare_source.read_text())

        # 2. Render mutable train.py from Jinja2 template
        from mlforge.templates import get_template_env

        env = get_template_env()
        template = env.get_template("ft_train.py.j2")

        settings = config.plugin_settings
        train_content = template.render(
            model_name=settings.get("model_name", "meta-llama/Llama-3.2-1B"),
            lora_r=settings.get("lora_r", 16),
            lora_alpha=settings.get("lora_alpha", 16),
            metric=config.metric,
            max_length=settings.get("max_length", 512),
            batch_size=settings.get("batch_size", 4),
            learning_rate=settings.get("learning_rate", 2e-4),
            num_epochs=settings.get("num_epochs", 3),
            dataset_format=settings.get("dataset_format", "instruction"),
        )
        (target_dir / "train.py").write_text(train_content)

    def template_context(self, config: Config) -> dict:
        """Return fine-tuning-specific domain rules for CLAUDE.md rendering.

        Includes rules about LoRA/QLoRA, VRAM management, chat templates,
        frozen prepare.py, adapter saving, and SFTTrainer usage.

        Args:
            config: Config with plugin_settings.

        Returns:
            Dict with 'domain_rules' list and 'extra_sections' list.
        """
        rules = [
            "Use LoRA/QLoRA adapters via peft -- NEVER do full fine-tuning",
            "Check VRAM before loading model: if <16GB, use 4-bit quantization (QLoRA)",
            "Always use tokenizer.apply_chat_template() for formatting -- never hand-construct prompts",
            "Do not modify prepare.py -- it is frozen infrastructure",
            "train.py is the ONLY mutable file -- all experiments go here",
            "Save adapter weights only (not full model) via model.save_pretrained()",
            "Use SFTTrainer from trl for training -- handles PEFT integration automatically",
            "Evaluate with perplexity on held-out set after training",
            "Monitor VRAM usage -- if >90% utilization, reduce batch size or max_length",
            "Use gradient checkpointing to reduce memory: model.gradient_checkpointing_enable()",
            "Do NOT remove predictions.csv or best_adapter save from train.py -- diagnostics and artifact export depend on these files",
        ]
        return {"domain_rules": rules, "extra_sections": []}

    def validate_config(self, config: Config) -> list[str]:
        """Validate fine-tuning-specific config settings.

        Checks that the metric is in the known valid set and that
        model_name is specified in plugin_settings.

        Args:
            config: Config to validate.

        Returns:
            List of error messages. Empty if valid.
        """
        errors = []
        if config.metric not in self._VALID_METRICS:
            errors.append(
                f"Unknown fine-tuning metric: {config.metric}. "
                f"Valid: {sorted(self._VALID_METRICS)}"
            )
        if not config.plugin_settings.get("model_name"):
            errors.append(
                "plugin_settings missing 'model_name' -- required for fine-tuning "
                "(e.g., 'meta-llama/Llama-3.2-1B')"
            )
        return errors
