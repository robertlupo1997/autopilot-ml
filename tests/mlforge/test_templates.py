"""Tests for Jinja2 template rendering."""

from __future__ import annotations

import pytest

from mlforge.config import Config
from mlforge.templates import get_template_env, render_claude_md, render_experiments_md


# Re-use the mock plugin from test_plugins
from tests.mlforge.test_plugins import MockTabularPlugin


class TestTemplateEnv:
    """Verify Jinja2 environment setup."""

    def test_template_env_loads(self):
        env = get_template_env()
        template = env.get_template("base_claude.md.j2")
        assert template is not None

    def test_template_env_loads_experiments(self):
        env = get_template_env()
        template = env.get_template("base_experiments.md.j2")
        assert template is not None


class TestRenderClaudeMd:
    """Verify CLAUDE.md rendering with plugin context."""

    @pytest.fixture()
    def plugin(self):
        return MockTabularPlugin()

    @pytest.fixture()
    def config(self):
        return Config(
            domain="tabular",
            metric="accuracy",
            direction="maximize",
            frozen_files=["prepare.py"],
            mutable_files=["train.py"],
        )

    def test_render_claude_md_contains_domain(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "tabular" in output

    def test_render_claude_md_contains_metric(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "accuracy" in output
        assert "maximize" in output

    def test_render_claude_md_contains_frozen_files(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "prepare.py" in output

    def test_render_claude_md_contains_mutable_files(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "train.py" in output

    def test_render_claude_md_contains_domain_rules(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "Use scikit-learn for modeling" in output
        assert "Do not modify prepare.py" in output

    def test_render_claude_md_has_header(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "# CLAUDE.md" in output


class TestRenderExperimentsMd:
    """Verify experiments.md rendering."""

    def test_render_experiments_md_contains_header(self):
        config = Config(
            domain="tabular",
            metric="accuracy",
            direction="maximize",
            budget_experiments=50,
            budget_minutes=60,
        )
        output = render_experiments_md(config, run_id="run-001")
        assert "run-001" in output
        assert "accuracy" in output
        assert "maximize" in output

    def test_render_experiments_md_contains_table_header(self):
        config = Config()
        output = render_experiments_md(config, run_id="run-002")
        assert "| # |" in output
        assert "Status" in output
