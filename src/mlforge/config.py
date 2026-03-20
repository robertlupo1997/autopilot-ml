"""Config dataclass with TOML loading.

Reads mlforge.config.toml using tomllib (stdlib). Falls back to sensible
defaults when the config file is missing or incomplete.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILENAME = "mlforge.config.toml"


@dataclass
class Config:
    """Configuration for an mlforge session."""

    domain: str = "tabular"
    metric: str = "accuracy"
    direction: str = "maximize"
    budget_minutes: int = 60
    budget_experiments: int = 50
    budget_usd: float = 5.0
    per_experiment_timeout_sec: int = 300
    per_experiment_budget_usd: float = 1.0
    max_turns_per_experiment: int = 30
    model: str | None = None
    frozen_files: list[str] = field(default_factory=lambda: ["prepare.py"])
    mutable_files: list[str] = field(default_factory=lambda: ["train.py"])
    plugin_settings: dict = field(default_factory=dict)
    custom_claude_md_path: Path | None = None
    custom_frozen: list[str] | None = None
    custom_mutable: list[str] | None = None
    enable_drafts: bool = False
    stagnation_threshold: int = 3

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        """Load config from a TOML file, falling back to defaults.

        Args:
            path: Path to the config file. If None, looks for
                  CONFIG_FILENAME in the current directory.

        Returns:
            Config instance with values from TOML merged over defaults.

        Raises:
            ValueError: If direction is not "maximize" or "minimize".
        """
        config_path = path or Path(CONFIG_FILENAME)
        if not config_path.exists():
            return cls()

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        config = cls(
            domain=data.get("domain", "tabular"),
            metric=data.get("metric", {}).get("name", "accuracy"),
            direction=data.get("metric", {}).get("direction", "maximize"),
            budget_minutes=data.get("budget", {}).get("minutes", 60),
            budget_experiments=data.get("budget", {}).get("experiments", 50),
            budget_usd=data.get("budget", {}).get("usd", 5.0),
            per_experiment_timeout_sec=data.get("budget", {}).get("per_experiment_timeout_sec", 300),
            per_experiment_budget_usd=data.get("budget", {}).get("per_experiment_budget_usd", 1.0),
            max_turns_per_experiment=data.get("budget", {}).get("max_turns", 30),
            model=data.get("model"),
            frozen_files=data.get("files", {}).get("frozen", ["prepare.py"]),
            mutable_files=data.get("files", {}).get("mutable", ["train.py"]),
            plugin_settings=data.get("plugin", {}),
            custom_claude_md_path=(
                Path(data["files"]["custom_claude_md"])
                if data.get("files", {}).get("custom_claude_md")
                else None
            ),
            custom_frozen=data.get("files", {}).get("custom_frozen"),
            custom_mutable=data.get("files", {}).get("custom_mutable"),
            enable_drafts=data.get("intelligence", {}).get("enable_drafts", False),
            stagnation_threshold=data.get("intelligence", {}).get("stagnation_threshold", 3),
        )

        if config.direction not in ("maximize", "minimize"):
            msg = f"direction must be 'maximize' or 'minimize', got '{config.direction}'"
            raise ValueError(msg)

        return config
