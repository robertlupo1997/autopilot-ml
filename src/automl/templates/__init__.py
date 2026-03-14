"""Template rendering for experiment project files."""

from __future__ import annotations

import os

_TEMPLATE_DIR = os.path.dirname(__file__)


def render_program_md(
    dataset_name: str,
    goal_description: str,
    metric_name: str,
    direction: str,
    data_summary: str = "",
    baselines: str = "",
) -> str:
    """Render program.md from template with dataset-specific values."""
    with open(os.path.join(_TEMPLATE_DIR, "program.md.tmpl")) as f:
        template = f.read()
    return template.format(
        dataset_name=dataset_name,
        goal_description=goal_description,
        metric_name=metric_name,
        direction=direction,
        data_summary=data_summary or "(Run prepare.py to generate)",
        baselines=baselines or "(Run prepare.py to generate)",
    )


def render_claude_md() -> str:
    """Render CLAUDE.md loop protocol (no substitution needed -- it is static)."""
    with open(os.path.join(_TEMPLATE_DIR, "claude.md.tmpl")) as f:
        return f.read()


def render_claude_md_forecast() -> str:
    """Render forecast CLAUDE.md loop protocol (no substitution -- static file)."""
    with open(os.path.join(_TEMPLATE_DIR, "claude_forecast.md.tmpl")) as f:
        return f.read()


def render_swarm_claude_md(
    agent_id: int,
    n_agents: int,
    family_names: str,
    swarm_dir: str,
    metric: str,
) -> str:
    """Render swarm_claude.md coordination protocol for a specific agent."""
    with open(os.path.join(_TEMPLATE_DIR, "swarm_claude.md.tmpl")) as f:
        template = f.read()
    return template.format(
        agent_id=agent_id,
        n_agents=n_agents,
        family_names=family_names,
        swarm_dir=swarm_dir,
        metric=metric,
    )
