"""Tests for program.md and CLAUDE.md template rendering."""

from __future__ import annotations

import os

import pytest

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "automl", "templates")


# ---------------------------------------------------------------------------
# program.md template tests
# ---------------------------------------------------------------------------

class TestProgramMdTemplate:
    """Tests for program.md.tmpl structure and rendering."""

    def test_program_md_template_exists(self):
        path = os.path.join(TEMPLATE_DIR, "program.md.tmpl")
        assert os.path.isfile(path), "program.md.tmpl should exist"

    def test_program_md_has_placeholders(self):
        path = os.path.join(TEMPLATE_DIR, "program.md.tmpl")
        content = open(path).read()
        for placeholder in ["{dataset_name}", "{goal_description}", "{metric_name}", "{direction}"]:
            assert placeholder in content, f"Missing placeholder: {placeholder}"

    def test_program_md_has_data_summary_placeholder(self):
        path = os.path.join(TEMPLATE_DIR, "program.md.tmpl")
        content = open(path).read()
        assert "{data_summary}" in content

    def test_program_md_has_baselines_placeholder(self):
        path = os.path.join(TEMPLATE_DIR, "program.md.tmpl")
        content = open(path).read()
        assert "{baselines}" in content

    def test_program_md_has_domain_section(self):
        path = os.path.join(TEMPLATE_DIR, "program.md.tmpl")
        content = open(path).read()
        assert "Domain" in content, "Should have a Domain Expertise section"


# ---------------------------------------------------------------------------
# CLAUDE.md template tests
# ---------------------------------------------------------------------------

class TestClaudeMdTemplate:
    """Tests for claude.md.tmpl structure -- the loop protocol."""

    def test_claude_md_template_exists(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        assert os.path.isfile(path), "claude.md.tmpl should exist"

    def test_claude_md_has_never_stop(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "NEVER STOP" in content

    def test_claude_md_has_loop_protocol(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "LOOP" in content, "Should contain LOOP instruction"

    def test_claude_md_references_program_md(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "program.md" in content

    def test_claude_md_has_run_log_redirect(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "run.log" in content

    def test_claude_md_has_grep_metric(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "grep" in content.lower() or "metric_value" in content

    def test_claude_md_has_keep_revert(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        content_lower = content.lower()
        assert "keep" in content_lower and "revert" in content_lower

    def test_claude_md_has_stagnation(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        content_lower = content.lower()
        assert "stagnation" in content_lower or "consecutive revert" in content_lower

    def test_claude_md_has_crash_recovery(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "crash" in content.lower() or "3" in content

    def test_claude_md_has_draft_phase(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        content_lower = content.lower()
        assert "draft" in content_lower or "multi-draft" in content_lower

    def test_claude_md_references_train_py_mutable(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "train.py" in content
        content_upper = content.upper()
        assert "MUTABLE" in content_upper or "ONLY file you edit" in content

    def test_claude_md_references_prepare_py_frozen(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "prepare.py" in content
        assert "FROZEN" in content.upper() or "Do not modify" in content


# ---------------------------------------------------------------------------
# Render function tests
# ---------------------------------------------------------------------------

class TestRenderFunctions:
    """Tests for render_program_md and render_claude_md."""

    def test_render_program_md(self):
        from automl.templates import render_program_md

        result = render_program_md(
            dataset_name="test-dataset",
            goal_description="Predict churn",
            metric_name="roc_auc",
            direction="maximize",
            data_summary="1000 rows, 10 features",
            baselines="LogisticRegression: 0.75",
        )
        assert "test-dataset" in result
        assert "Predict churn" in result
        assert "roc_auc" in result
        assert "maximize" in result
        assert "1000 rows" in result
        assert "LogisticRegression: 0.75" in result
        # No raw placeholders should remain
        assert "{dataset_name}" not in result
        assert "{goal_description}" not in result

    def test_render_program_md_defaults(self):
        from automl.templates import render_program_md

        result = render_program_md(
            dataset_name="ds",
            goal_description="goal",
            metric_name="accuracy",
            direction="maximize",
        )
        # Default data_summary and baselines
        assert "prepare.py" in result.lower() or "(Run prepare.py" in result

    def test_render_claude_md(self):
        from automl.templates import render_claude_md

        result = render_claude_md()
        assert isinstance(result, str)
        assert len(result) > 100, "CLAUDE.md should be a substantial document"
        assert "NEVER STOP" in result
