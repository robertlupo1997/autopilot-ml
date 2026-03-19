"""Jinja2 template rendering for CLAUDE.md and experiments.md.

Uses PackageLoader to find templates in the mlforge/templates/ directory.
Merges plugin-provided context with config values for rendering.
"""

from __future__ import annotations

from jinja2 import Environment, PackageLoader

from mlforge.config import Config
from mlforge.plugins import DomainPlugin


def get_template_env() -> Environment:
    """Create a Jinja2 Environment loading from mlforge/templates/.

    Returns:
        Configured Jinja2 Environment.
    """
    return Environment(
        loader=PackageLoader("mlforge", "templates"),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_claude_md(plugin: DomainPlugin, config: Config) -> str:
    """Render CLAUDE.md using a plugin's template context and config.

    Args:
        plugin: DomainPlugin providing domain-specific template variables.
        config: Config with metric, frozen/mutable files, etc.

    Returns:
        Rendered CLAUDE.md content as a string.
    """
    env = get_template_env()
    template = env.get_template("base_claude.md.j2")

    # Start with config values
    context: dict = {
        "domain": config.domain,
        "metric_name": config.metric,
        "metric_direction": config.direction,
        "frozen_files": config.frozen_files,
        "mutable_files": config.mutable_files,
    }

    # Merge plugin context (domain_rules, extra_sections, etc.)
    plugin_ctx = plugin.template_context(config)
    context.update(plugin_ctx)

    return template.render(context)


def render_experiments_md(config: Config, run_id: str) -> str:
    """Render experiments.md template with config and run info.

    Args:
        config: Config with metric, budget, domain info.
        run_id: Unique identifier for this experiment run.

    Returns:
        Rendered experiments.md content as a string.
    """
    env = get_template_env()
    template = env.get_template("base_experiments.md.j2")

    context = {
        "run_id": run_id,
        "domain": config.domain,
        "metric_name": config.metric,
        "metric_direction": config.direction,
        "budget_experiments": config.budget_experiments,
        "budget_minutes": config.budget_minutes,
    }

    return template.render(context)
