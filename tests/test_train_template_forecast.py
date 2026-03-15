"""
Structural inspection tests for train_template_forecast.py and claude_forecast.md.tmpl.

These tests read source files as text and assert structural properties.
No execution of the template is performed.
"""
import pathlib
import importlib.util

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _template_text() -> str:
    """Return the text of train_template_forecast.py."""
    spec = importlib.util.find_spec("automl.train_template_forecast")
    assert spec is not None, (
        "automl.train_template_forecast not found — file does not exist yet"
    )
    return pathlib.Path(spec.origin).read_text()


def _claude_forecast_text() -> str:
    """Return the text of claude_forecast.md.tmpl."""
    # Locate templates directory relative to the automl package
    automl_spec = importlib.util.find_spec("automl")
    assert automl_spec is not None, "automl package not found"
    automl_dir = pathlib.Path(automl_spec.origin).parent
    tmpl_path = automl_dir / "templates" / "claude_forecast.md.tmpl"
    assert tmpl_path.exists(), f"claude_forecast.md.tmpl not found at {tmpl_path}"
    return tmpl_path.read_text()


# ---------------------------------------------------------------------------
# TestTrainTemplateForecastStructure
# ---------------------------------------------------------------------------

class TestTrainTemplateForecastStructure:
    """Structural tests for train_template_forecast.py."""

    def test_engineer_features_exists(self):
        """File must contain engineer_features function definition."""
        text = _template_text()
        assert "def engineer_features" in text

    def test_engineer_features_starter_features(self):
        """engineer_features must use all four starter feature names."""
        text = _template_text()
        assert "lag_1" in text, "lag_1 feature missing"
        assert "lag_4" in text, "lag_4 feature missing"
        assert "yoy_growth" in text, "yoy_growth feature missing"
        assert "rolling_mean_4q" in text, "rolling_mean_4q feature missing"

    def test_shift_before_rolling(self):
        """shift(1) must appear before .rolling( in the file (shift-first pattern)."""
        text = _template_text()
        shift_pos = text.find(".shift(1)")
        rolling_pos = text.find(".rolling(")
        assert shift_pos != -1, ".shift(1) not found in template"
        assert rolling_pos != -1, ".rolling( not found in template"
        assert shift_pos < rolling_pos, (
            f".shift(1) appears at pos {shift_pos} but .rolling( at {rolling_pos} — "
            "shift must come first (shift-first pattern)"
        )

    def test_objective_calls_walk_forward(self):
        """walk_forward_evaluate must appear inside the objective function."""
        text = _template_text()
        # Find objective function and verify walk_forward_evaluate is present
        assert "def objective" in text, "objective function missing"
        assert "walk_forward_evaluate" in text, (
            "walk_forward_evaluate not called in template"
        )
        # Check it appears after objective definition
        obj_pos = text.find("def objective")
        wfe_pos = text.find("walk_forward_evaluate", obj_pos)
        assert wfe_pos != -1, (
            "walk_forward_evaluate not found after objective definition"
        )

    def test_optuna_create_study(self):
        """Template must contain create_study and at least one suggest_* call."""
        text = _template_text()
        assert "create_study" in text, "optuna.create_study not found"
        has_suggest = "suggest_float" in text or "suggest_int" in text or "suggest_categorical" in text
        assert has_suggest, "No trial.suggest_* calls found"

    def test_baselines_computed(self):
        """Template must call get_forecasting_baselines."""
        text = _template_text()
        assert "get_forecasting_baselines" in text, (
            "get_forecasting_baselines not called — baselines must be computed"
        )

    def test_structured_output(self):
        """Template must print metric_value: and json_output: lines."""
        text = _template_text()
        assert "metric_value:" in text, "metric_value: print line missing"
        assert "json_output:" in text, "json_output: print line missing"

    def test_json_output_baseline_keys(self):
        """json_output dict must include beats_naive and beats_seasonal_naive keys."""
        text = _template_text()
        assert "beats_naive" in text, "beats_naive key missing from json_output"
        assert "beats_seasonal_naive" in text, (
            "beats_seasonal_naive key missing from json_output"
        )

    def test_frozen_imports(self):
        """Template must use local imports (from forecast import ...), not automl package."""
        text = _template_text()
        assert "from forecast import" in text, (
            "Template must import from forecast (local), not automl.forecast"
        )

    def test_optuna_logging_suppressed(self):
        """Template must suppress optuna [I] log spam."""
        text = _template_text()
        assert "optuna.logging.set_verbosity" in text, (
            "optuna.logging.set_verbosity not found — Optuna log spam will flood run.log"
        )

    def test_imports_diagnose(self):
        """Template must import diagnose from forecast (local import)."""
        text = _template_text()
        # The 'from forecast import' line must contain 'diagnose'
        import re
        matches = re.findall(r"from forecast import[^\n]*", text)
        assert any("diagnose" in m for m in matches), (
            "diagnose not found in 'from forecast import' line — "
            "train_template_forecast.py must import diagnose from forecast"
        )

    def test_diagnose_called_after_evaluation(self):
        """diagnose() must be called after the final walk_forward_evaluate (not inside objective)."""
        text = _template_text()
        # Find the position of 'def objective' and the final walk_forward_evaluate outside it
        obj_end_pos = text.find("study.optimize")
        assert obj_end_pos != -1, "study.optimize not found — unexpected template structure"
        # diagnose( must appear after study.optimize (i.e., outside objective)
        diag_pos = text.find("diagnose(", obj_end_pos)
        assert diag_pos != -1, (
            "diagnose() not found after study.optimize — must be called outside objective, "
            "after final model evaluation"
        )

    def test_diagnostic_output_printed(self):
        """Template must print 'diagnostic_output:' as a structured output line."""
        text = _template_text()
        assert "diagnostic_output:" in text, (
            "'diagnostic_output:' prefix missing — template must print diagnose() result "
            "with this prefix for structured parsing"
        )


# ---------------------------------------------------------------------------
# TestClaudeForecastTemplate
# ---------------------------------------------------------------------------

class TestClaudeForecastTemplate:
    """Structural tests for claude_forecast.md.tmpl."""

    def test_dual_baseline_rule(self):
        """Template must describe beating both naive and seasonal-naive baselines."""
        text = _claude_forecast_text()
        text_lower = text.lower()
        # Look for dual baseline gate content
        has_naive = "naive" in text_lower
        has_seasonal = "seasonal" in text_lower or "seasonal_naive" in text_lower
        has_both = "both" in text_lower or "dual" in text_lower or (has_naive and has_seasonal)
        assert has_both, (
            "Dual-baseline gate rule missing — template must mention beating both "
            "naive and seasonal-naive baselines"
        )
        # More specific: beats_naive and beats_seasonal_naive or equivalent
        assert has_naive and has_seasonal, (
            "Template must mention both naive and seasonal_naive baselines"
        )

    def test_feature_cap_rule(self):
        """Template must mention the 15-feature cap."""
        text = _claude_forecast_text()
        assert "15" in text, (
            "15-feature cap rule missing from claude_forecast.md.tmpl"
        )

    def test_trial_budget_rule(self):
        """Template must document the min(50, 2*n_rows) trial budget cap."""
        text = _claude_forecast_text()
        has_cap = "min(50" in text or "2 * n_rows" in text or "2*n_rows" in text
        assert has_cap, (
            "Trial budget cap rule missing — template must state min(50, 2*n_rows)"
        )

    def test_shift_first_rule(self):
        """Template must state shift-first mandate for rolling stats."""
        text = _claude_forecast_text()
        assert "shift" in text.lower(), (
            "shift-first rule missing from claude_forecast.md.tmpl"
        )

    def test_mape_direction_rule(self):
        """Template must state that MAPE is lower-is-better."""
        text = _claude_forecast_text()
        text_lower = text.lower()
        has_mape = "mape" in text_lower
        has_lower = "lower" in text_lower or "lower is better" in text_lower or "minimize" in text_lower
        assert has_mape and has_lower, (
            "MAPE direction rule missing — template must state MAPE is lower-is-better"
        )

    def test_no_cv_loop_rule(self):
        """Template must state that agent should never write own CV loop."""
        text = _claude_forecast_text()
        text_lower = text.lower()
        # Check for CV loop prohibition
        has_never_cv = ("never" in text_lower and "cv" in text_lower) or \
                       ("never" in text_lower and "loop" in text_lower) or \
                       ("own cv" in text_lower) or \
                       ("own validation" in text_lower) or \
                       ("walk_forward_evaluate" in text_lower)
        assert has_never_cv, (
            "No-custom-CV-loop rule missing — template must prohibit writing own CV loop"
        )

    def test_frozen_files_rule(self):
        """Template must mention prepare.py and forecast.py as frozen."""
        text = _claude_forecast_text()
        assert "prepare.py" in text, "prepare.py not mentioned as frozen in template"
        assert "forecast.py" in text, "forecast.py not mentioned as frozen in template"

    def test_diag_rule_record_error_patterns(self):
        """Template must instruct agent to read diagnostic_output and record Error Patterns in experiments.md."""
        text = _claude_forecast_text()
        assert "diagnostic_output" in text, (
            "'diagnostic_output' missing — template must instruct agent to read the "
            "diagnostic_output line from run.log"
        )
        assert "experiments.md" in text, (
            "'experiments.md' missing — template must instruct agent to record patterns "
            "in experiments.md"
        )
        assert "Error Patterns" in text, (
            "'Error Patterns' section name missing — template must reference the "
            "Error Patterns section of experiments.md"
        )

    def test_journal_read_write_rule(self):
        """KNOW-02: experiments.md must be listed in Files with read and update instructions."""
        text = _claude_forecast_text()
        assert "experiments.md" in text, "experiments.md must appear in the template"
        # Check that read/update instructions exist near experiments.md
        idx = text.find("experiments.md")
        surrounding = text[max(0, idx - 200) : idx + 500]
        assert "read" in surrounding.lower() or "Read" in surrounding, (
            "'read' must appear near experiments.md mention"
        )
        assert "update" in surrounding.lower() or "Update" in surrounding, (
            "'update' must appear near experiments.md mention"
        )

    def test_diff_aware_rule(self):
        """PROT-01: Template must instruct git diff HEAD~1 and git log --oneline."""
        text = _claude_forecast_text()
        assert "git diff HEAD~1" in text, (
            "'git diff HEAD~1' missing — template must instruct diff-aware iteration"
        )
        assert "git log --oneline" in text, (
            "'git log --oneline' missing — template must instruct trajectory review"
        )

    def test_hypothesis_commit_rule(self):
        """PROT-02: Template must require a Hypothesis section in commit messages."""
        text = _claude_forecast_text()
        assert "Hypothesis" in text, (
            "'Hypothesis' missing — template must require hypothesis sections in commits"
        )
        idx = text.find("Hypothesis")
        surrounding = text[max(0, idx - 300) : idx + 300]
        assert "commit" in surrounding.lower(), (
            "'commit' must appear near 'Hypothesis' instruction"
        )

    def test_experiments_md_in_files_section(self):
        """PROT-03: experiments.md must appear in the Files section."""
        text = _claude_forecast_text()
        files_section_start = text.find("## Files")
        files_section_end = text.find("##", files_section_start + 1)
        files_section = text[files_section_start:files_section_end]
        assert "experiments.md" in files_section, (
            "experiments.md must be listed in the ## Files section"
        )
