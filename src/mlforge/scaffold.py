"""Experiment directory scaffolding.

Creates a complete experiment directory using the plugin system,
templates, and hook files.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from mlforge.config import Config
from mlforge.hooks import write_hook_files
from mlforge.plugins import get_plugin, register_plugin
from mlforge.templates import render_claude_md, render_experiments_md


def _serialize_config_toml(config: Config) -> str:
    """Serialize Config fields to TOML format using string formatting.

    Args:
        config: Config to serialize.

    Returns:
        TOML-formatted string.
    """
    lines = [
        f'domain = "{config.domain}"',
        "",
        "[metric]",
        f'name = "{config.metric}"',
        f'direction = "{config.direction}"',
        "",
        "[budget]",
        f"minutes = {config.budget_minutes}",
        f"experiments = {config.budget_experiments}",
        f"usd = {config.budget_usd}",
        f"per_experiment_timeout_sec = {config.per_experiment_timeout_sec}",
        f"per_experiment_budget_usd = {config.per_experiment_budget_usd}",
        f"max_turns = {config.max_turns_per_experiment}",
        "",
        "[files]",
        f"frozen = {config.frozen_files!r}",
        f"mutable = {config.mutable_files!r}",
    ]

    if config.model is not None:
        # Insert model at top level (after domain)
        lines.insert(1, f'model = "{config.model}"')

    return "\n".join(lines) + "\n"


def _ensure_tabular_registered() -> None:
    """Register the tabular plugin if not already registered."""
    try:
        get_plugin("tabular")
    except KeyError:
        from mlforge.tabular import TabularPlugin

        register_plugin(TabularPlugin())


def scaffold_experiment(
    config: Config,
    dataset_path: Path,
    target_dir: Path,
    run_id: str,
) -> Path:
    """Create a complete experiment directory.

    Uses the plugin system to generate domain-specific files, renders
    CLAUDE.md and experiments.md from templates, writes hook files for
    frozen file enforcement, copies the dataset, and writes config TOML.

    Args:
        config: Session configuration.
        dataset_path: Path to the dataset file.
        target_dir: Directory to create the experiment in.
        run_id: Unique identifier for this run.

    Returns:
        The target directory Path.

    Raises:
        FileNotFoundError: If dataset_path does not exist.
    """
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    # 1. Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)

    # 2. Ensure plugin is registered and get it
    _ensure_tabular_registered()
    plugin = get_plugin(config.domain)

    # 3. Plugin scaffolds domain-specific files (prepare.py, train.py)
    plugin.scaffold(target_dir, config)

    # 4. Render CLAUDE.md (or copy custom one for expert mode)
    if config.custom_claude_md_path is not None:
        custom_path = config.custom_claude_md_path
        if not custom_path.exists():
            raise FileNotFoundError(f"Custom CLAUDE.md not found: {custom_path}")
        import shutil as _shutil
        _shutil.copy2(custom_path, target_dir / "CLAUDE.md")
    else:
        claude_md = render_claude_md(plugin, config)
        (target_dir / "CLAUDE.md").write_text(claude_md)

    # 5. Render experiments.md journal template
    experiments_md = render_experiments_md(config, run_id)
    (target_dir / "experiments.md").write_text(experiments_md)

    # 6. Write hook files for frozen file enforcement
    frozen = config.custom_frozen if config.custom_frozen is not None else plugin.frozen_files
    write_hook_files(target_dir, frozen)

    # 7. Copy dataset to target directory
    shutil.copy2(dataset_path, target_dir / dataset_path.name)

    # 8. Apply custom frozen/mutable to config for TOML serialization
    if config.custom_frozen is not None:
        config.frozen_files = config.custom_frozen
    if config.custom_mutable is not None:
        config.mutable_files = config.custom_mutable

    # 9. Write mlforge.config.toml
    config_toml = _serialize_config_toml(config)
    (target_dir / "mlforge.config.toml").write_text(config_toml)

    return target_dir
