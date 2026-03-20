"""Tabular ML domain plugin for mlforge.

Implements the DomainPlugin Protocol for classification and regression
on CSV/Parquet tabular data using scikit-learn, XGBoost, and LightGBM.
"""

from __future__ import annotations

from pathlib import Path

from mlforge.config import Config


class TabularPlugin:
    """Tabular ML plugin implementing DomainPlugin Protocol.

    Provides scaffolding for classification/regression experiments with
    frozen prepare.py (data pipeline) and mutable train.py (experiment script).
    """

    name: str = "tabular"
    frozen_files: list[str] = ["prepare.py"]

    _VALID_METRICS: set[str] = {
        "accuracy", "auc", "roc_auc", "f1", "f1_weighted",
        "precision", "recall", "log_loss",
        "rmse", "mae", "r2", "mse",
    }

    def scaffold(self, target_dir: Path, config: Config) -> None:
        """Create frozen prepare.py and mutable train.py in target_dir.

        prepare.py is copied from the mlforge.tabular.prepare source module.
        train.py is rendered from the tabular_train.py.j2 Jinja2 template.

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
        template = env.get_template("tabular_train.py.j2")
        train_content = template.render(
            csv_path=config.plugin_settings.get("csv_path", "data.csv"),
            target_column=config.plugin_settings.get("target_column", "target"),
            metric=config.metric,
            time_budget=config.plugin_settings.get("time_budget", 60),
            task=config.plugin_settings.get("task", "classification"),
            date_column=config.plugin_settings.get("date_column", ""),
        )
        (target_dir / "train.py").write_text(train_content)

    def template_context(self, config: Config) -> dict:
        """Return tabular-specific domain rules for CLAUDE.md rendering.

        Includes rules about dual-baseline gate, frozen prepare.py,
        sklearn compatibility, metric direction, and task-specific CV strategy.

        Args:
            config: Config with plugin_settings including 'task'.

        Returns:
            Dict with 'domain_rules' list and 'extra_sections' list.
        """
        task = config.plugin_settings.get("task", "classification")
        rules = [
            "Use scikit-learn compatible estimators (sklearn, xgboost, lightgbm)",
            "Do not modify prepare.py -- it is frozen infrastructure",
            "train.py is the ONLY mutable file -- all experiments go here",
            "Must beat BOTH baselines before keeping an experiment",
            "Commit before running -- enables clean revert on failure",
            "ALWAYS redirect output to run.log: > run.log 2>&1",
            "Read experiments.md before each iteration for accumulated knowledge",
            "Do NOT remove predictions.csv or best_model.joblib writes from train.py -- diagnostics and artifact export depend on these files",
        ]

        if task == "classification":
            rules.append(
                "Use StratifiedKFold for cross-validation to handle class imbalance"
            )
        else:
            rules.append(
                "Use KFold for cross-validation (regression does not need stratification)"
            )

        return {"domain_rules": rules, "extra_sections": []}

    def validate_config(self, config: Config) -> list[str]:
        """Validate tabular-specific config settings.

        Checks that the metric is in the known valid set.

        Args:
            config: Config to validate.

        Returns:
            List of error messages. Empty if valid.
        """
        errors = []
        if config.metric not in self._VALID_METRICS:
            errors.append(
                f"Unknown tabular metric: {config.metric}. "
                f"Valid: {sorted(self._VALID_METRICS)}"
            )
        return errors
