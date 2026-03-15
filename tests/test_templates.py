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

    def test_claude_md_has_graceful_shutdown(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "Graceful Shutdown" in content, "Template must have a Graceful Shutdown section"

    def test_claude_md_shutdown_mentions_git_reset(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "git reset --hard HEAD" in content, "Shutdown section must include git reset --hard HEAD"

    def test_claude_md_shutdown_mentions_results_tsv(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "results.tsv" in content, "Shutdown section must reference results.tsv"

    def test_journal_read_write_rule(self):
        """KNOW-02: experiments.md must be listed in Files with read and update instructions."""
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "experiments.md" in content, "experiments.md must appear in the template"
        # Find the position of experiments.md and check that read/update appear nearby
        idx = content.find("experiments.md")
        surrounding = content[max(0, idx - 200) : idx + 500]
        assert "read" in surrounding.lower() or "Read" in surrounding, (
            "'read' must appear near experiments.md mention"
        )
        assert "update" in surrounding.lower() or "Update" in surrounding, (
            "'update' must appear near experiments.md mention"
        )

    def test_diff_aware_rule(self):
        """PROT-01: Template must instruct git diff HEAD~1 and git log --oneline."""
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "git diff HEAD~1" in content, (
            "'git diff HEAD~1' missing — template must instruct diff-aware iteration"
        )
        assert "git log --oneline" in content, (
            "'git log --oneline' missing — template must instruct trajectory review"
        )

    def test_hypothesis_commit_rule(self):
        """PROT-02: Template must require a Hypothesis section in commit messages."""
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "Hypothesis" in content, (
            "'Hypothesis' missing — template must require hypothesis sections in commits"
        )
        # "commit message" must appear near "Hypothesis"
        idx = content.find("Hypothesis")
        surrounding = content[max(0, idx - 300) : idx + 300]
        assert "commit" in surrounding.lower(), (
            "'commit' must appear near 'Hypothesis' instruction"
        )

    def test_experiments_md_in_files_section(self):
        """PROT-03: experiments.md must appear in the Files section."""
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        files_section_start = content.find("## Files")
        files_section_end = content.find("##", files_section_start + 1)
        files_section = content[files_section_start:files_section_end]
        assert "experiments.md" in files_section, (
            "experiments.md must be listed in the ## Files section"
        )

    def test_best_result_tracking_on_keep(self):
        """EXPL-01: KEEP step must instruct agent to update Best Result with git rev-parse HEAD."""
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "Best Result" in content, "Best Result section reference missing from KEEP step"
        assert "Best commit" in content, "Best commit field missing from KEEP tracking instructions"
        assert "git rev-parse HEAD" in content, "git rev-parse HEAD missing — agent needs this to record the commit hash"

    def test_stagnation_triggers_exploration_branch(self):
        """EXPL-02 + EXPL-03: Stagnation must trigger at 3 reverts and create explore- branch."""
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        assert "3 consecutive reverts" in content, "Stagnation threshold must be 3 consecutive reverts"
        assert "explore-" in content, "explore- branch prefix missing from stagnation step"
        assert "git checkout -b explore-" in content, "git checkout -b explore- command missing from stagnation step"

    def test_exploration_branch_uses_best_commit(self):
        """EXPL-03: Exploration branch must branch from best-ever commit (Best Result section)."""
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        content = open(path).read()
        # The stagnation step must reference Best Result to get the best commit hash
        stagnation_pos = content.find("3 consecutive reverts")
        assert stagnation_pos != -1, "Stagnation trigger not found"
        surrounding = content[stagnation_pos: stagnation_pos + 600]
        assert "Best Result" in surrounding or "best_commit" in surrounding, (
            "Stagnation step must reference Best Result or best_commit for exploration branching"
        )


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
        assert "Graceful Shutdown" in result, "render_claude_md() output must include Graceful Shutdown"


# ---------------------------------------------------------------------------
# Resume Protocol section tests
# ---------------------------------------------------------------------------

class TestClaudeMdResumeSection:
    """Tests for the Session Resume Check section in claude.md.tmpl."""

    def _get_content(self):
        path = os.path.join(TEMPLATE_DIR, "claude.md.tmpl")
        return open(path).read()

    def test_resume_section_exists(self):
        """CLAUDE.md template contains '## Session Resume Check' heading."""
        content = self._get_content()
        assert "## Session Resume Check" in content

    def test_resume_section_before_phase_1(self):
        """'Session Resume Check' section appears before '## Phase 1'."""
        content = self._get_content()
        resume_pos = content.find("## Session Resume Check")
        phase1_pos = content.find("## Phase 1")
        assert resume_pos != -1, "Session Resume Check section not found"
        assert phase1_pos != -1, "Phase 1 section not found"
        assert resume_pos < phase1_pos, (
            "Session Resume Check must appear before Phase 1, "
            f"but found at pos {resume_pos} vs {phase1_pos}"
        )

    def test_resume_section_references_checkpoint_json(self):
        """Resume section references 'checkpoint.json'."""
        content = self._get_content()
        assert "checkpoint.json" in content

    def test_resume_section_references_automl_checkpoint(self):
        """Resume section references 'automl.checkpoint' for save calls."""
        content = self._get_content()
        assert "automl.checkpoint" in content

    def test_resume_section_distinguishes_draft_vs_iteration(self):
        """Resume section handles both loop_phase='draft' and 'iteration'."""
        content = self._get_content()
        assert "draft" in content
        assert "iteration" in content

    def test_resume_section_instructs_checkpoint_update(self):
        """Resume section instructs updating checkpoint after keep/revert."""
        content = self._get_content()
        content_lower = content.lower()
        # Should mention updating checkpoint after keep/revert decisions
        assert "keep" in content_lower and "revert" in content_lower
        # Checkpoint update instruction
        assert "save_checkpoint" in content or "checkpoint" in content_lower

    def test_render_claude_md_contains_resume_section(self):
        """render_claude_md() output contains 'Session Resume Check'."""
        from automl.templates import render_claude_md

        result = render_claude_md()
        assert "## Session Resume Check" in result

    def test_render_claude_md_resume_before_phase1(self):
        """render_claude_md() output: Session Resume Check before Phase 1."""
        from automl.templates import render_claude_md

        result = render_claude_md()
        resume_pos = result.find("## Session Resume Check")
        phase1_pos = result.find("## Phase 1")
        assert resume_pos != -1, "Session Resume Check not in render_claude_md() output"
        assert phase1_pos != -1, "Phase 1 not in render_claude_md() output"
        assert resume_pos < phase1_pos
