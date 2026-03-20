"""Deep learning domain plugin for mlforge.

Implements the DomainPlugin Protocol for image classification,
text classification, and custom architectures using PyTorch.

All heavy dependencies (torch, timm, transformers) are lazy-imported
inside methods to avoid requiring GPU/DL deps at import time.
"""

from __future__ import annotations

from pathlib import Path

from mlforge.config import Config


class DeepLearningPlugin:
    """Deep learning plugin implementing DomainPlugin Protocol.

    Provides scaffolding for PyTorch-based experiments with frozen
    prepare.py (GPU info + data loading) and mutable train.py
    (time-budgeted training with early stopping and gradient clipping).
    """

    name: str = "deeplearning"
    frozen_files: list[str] = ["prepare.py"]

    _VALID_METRICS: set[str] = {"accuracy", "f1", "f1_weighted", "loss"}

    _VALID_TASKS: set[str] = {
        "image_classification",
        "text_classification",
        "custom",
    }

    def scaffold(self, target_dir: Path, config: Config) -> None:
        """Create frozen prepare.py and mutable train.py in target_dir.

        prepare.py is copied from the mlforge.deeplearning.prepare source.
        train.py is rendered from the dl_train.py.j2 Jinja2 template.

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
        template = env.get_template("dl_train.py.j2")

        task = config.plugin_settings.get("task", "image_classification")
        train_content = template.render(
            task=task,
            data_dir=config.plugin_settings.get("data_dir", "data"),
            data_path=config.plugin_settings.get("data_path", "data.csv"),
            metric=config.metric,
            time_budget=config.budget_minutes * 60,
            img_size=config.plugin_settings.get("img_size", 224),
            batch_size=config.plugin_settings.get("batch_size", 32),
            model_name=config.plugin_settings.get(
                "model_name",
                "resnet50" if task == "image_classification" else "distilbert-base-uncased",
            ),
        )
        (target_dir / "train.py").write_text(train_content)

    def template_context(self, config: Config) -> dict:
        """Return DL-specific domain rules for CLAUDE.md rendering.

        Includes rules about timm, transformers, frozen prepare.py,
        mixed precision, early stopping, and gradient clipping.

        Args:
            config: Config with plugin_settings.

        Returns:
            Dict with 'domain_rules' list and 'extra_sections' list.
        """
        rules = [
            "Use timm pretrained models for image classification",
            "Use transformers AutoModel for text classification",
            "Do not modify prepare.py -- it is frozen infrastructure",
            "train.py is the ONLY mutable file -- all experiments go here",
            "Check GPU memory before loading model: torch.cuda.mem_get_info()",
            "Use mixed precision (torch.amp) for memory efficiency",
            "Stop training when time budget expires (check wall clock between epochs)",
            "Use early stopping with patience=5 on validation loss",
            "Apply gradient clipping: torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)",
            "Use ReduceLROnPlateau scheduler for adaptive learning rate",
        ]
        return {"domain_rules": rules, "extra_sections": []}

    def validate_config(self, config: Config) -> list[str]:
        """Validate DL-specific config settings.

        Checks that the metric is valid and the task type (if provided)
        is one of image_classification, text_classification, or custom.

        Args:
            config: Config to validate.

        Returns:
            List of error messages. Empty if valid.
        """
        errors = []

        if config.metric not in self._VALID_METRICS:
            errors.append(
                f"Unknown deeplearning metric: {config.metric}. "
                f"Valid: {sorted(self._VALID_METRICS)}"
            )

        task = config.plugin_settings.get("task")
        if task is not None and task not in self._VALID_TASKS:
            errors.append(
                f"Unknown deeplearning task: {task}. "
                f"Valid: {sorted(self._VALID_TASKS)}"
            )

        return errors
