"""Tests for experiment directory scaffolding."""

import inspect
import json
import stat
import subprocess
from pathlib import Path

import pytest

from automl.scaffold import scaffold_experiment


class TestScaffoldCreatesAllFiles:
    """scaffold_experiment() creates output dir with all 7 required files."""

    def test_scaffold_creates_all_files(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )

        expected_files = [
            "prepare.py",
            "forecast.py",
            "train.py",
            "program.md",
            "CLAUDE.md",
            "experiments.md",
            ".gitignore",
            "pyproject.toml",
            sample_classification_csv.name,  # "data.csv"
        ]
        actual_files = [f.name for f in out.iterdir() if f.is_file()]
        for fname in expected_files:
            assert fname in actual_files, f"Missing file: {fname}"
        # 9 files + .claude/ dir = 10 top-level items
        assert len(list(out.iterdir())) == 10
        assert (out / ".claude").is_dir()


class TestScaffoldPrepare:
    """Copied prepare.py is byte-identical to installed source."""

    def test_scaffold_prepare_py_matches_source(self, sample_classification_csv, tmp_path):
        import automl.prepare as prepare_mod

        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )

        source_path = inspect.getfile(prepare_mod)
        source_bytes = Path(source_path).read_bytes()
        copied_bytes = (out / "prepare.py").read_bytes()
        assert copied_bytes == source_bytes


class TestScaffoldTrainConfig:
    """Generated train.py has correct config values."""

    def test_scaffold_train_py_config(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
            time_budget=120,
        )

        content = (out / "train.py").read_text()
        assert 'CSV_PATH = "data.csv"' in content
        assert 'TARGET_COLUMN = "target"' in content
        assert 'METRIC = "accuracy"' in content
        assert "TIME_BUDGET = 120" in content


class TestScaffoldProgramMd:
    """program.md contains dataset shape and baseline scores."""

    def test_scaffold_program_md_has_data_summary(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )

        content = (out / "program.md").read_text()
        # Must have real data info, not placeholders
        assert "200" in content  # 200 rows
        assert "7" in content or "shape" in content.lower()  # columns or shape info
        # Must have baseline scores
        assert "most_frequent" in content or "baseline" in content.lower()


class TestScaffoldPyproject:
    """pyproject.toml lists required ML dependencies."""

    def test_scaffold_pyproject_has_deps(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )

        content = (out / "pyproject.toml").read_text()
        for dep in ["scikit-learn", "pandas", "numpy", "xgboost", "lightgbm"]:
            assert dep in content, f"Missing dependency: {dep}"


class TestScaffoldGitignore:
    """.gitignore lists expected patterns."""

    def test_scaffold_gitignore(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )

        content = (out / ".gitignore").read_text()
        for pattern in ["results.tsv", "run.log", "__pycache__/", ".venv/", ".claude/settings.local.json"]:
            assert pattern in content, f"Missing .gitignore pattern: {pattern}"

    def test_scaffold_gitignore_includes_checkpoint_json(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )

        content = (out / ".gitignore").read_text()
        assert "checkpoint.json" in content, "Missing .gitignore pattern: checkpoint.json"

    def test_scaffold_gitignore_includes_checkpoint_json_tmp(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )

        content = (out / ".gitignore").read_text()
        assert "checkpoint.json.tmp" in content, "Missing .gitignore pattern: checkpoint.json.tmp"


class TestScaffoldGitignoreSwarm:
    """.gitignore includes .swarm/ coordination file entries."""

    def test_gitignore_swarm_entries(self, sample_classification_csv, tmp_path):
        """_gitignore_content() includes .swarm/scoreboard.tsv and .swarm/claims/."""
        from automl.scaffold import _gitignore_content

        content = _gitignore_content()
        assert ".swarm/scoreboard.tsv" in content, "Missing .swarm/scoreboard.tsv"
        assert ".swarm/claims/" in content, "Missing .swarm/claims/"

    def test_gitignore_swarm_lock_entry(self, sample_classification_csv, tmp_path):
        """_gitignore_content() includes .swarm/scoreboard.lock."""
        from automl.scaffold import _gitignore_content

        content = _gitignore_content()
        assert ".swarm/scoreboard.lock" in content, "Missing .swarm/scoreboard.lock"

    def test_gitignore_swarm_config_entry(self, sample_classification_csv, tmp_path):
        """_gitignore_content() includes .swarm/config.json."""
        from automl.scaffold import _gitignore_content

        content = _gitignore_content()
        assert ".swarm/config.json" in content, "Missing .swarm/config.json"

    def test_gitignore_swarm_best_train_entry(self, sample_classification_csv, tmp_path):
        """_gitignore_content() includes .swarm/best_train.py."""
        from automl.scaffold import _gitignore_content

        content = _gitignore_content()
        assert ".swarm/best_train.py" in content, "Missing .swarm/best_train.py"


class TestScaffoldFailsIfDirExists:
    """Raises FileExistsError when output_dir already exists."""

    def test_scaffold_fails_if_dir_exists(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        out.mkdir()

        with pytest.raises(FileExistsError):
            scaffold_experiment(
                data_path=sample_classification_csv,
                target_column="target",
                metric="accuracy",
                goal="Predict target class",
                output_dir=out,
            )


class TestScaffoldDefaultOutputDir:
    """When output_dir=None, creates experiment-{csv_stem} directory."""

    def test_scaffold_default_output_dir(self, sample_classification_csv, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
        )

        assert result.name == f"experiment-{sample_classification_csv.stem}"
        assert result.exists()


class TestScaffoldCsvCopied:
    """CSV file is copied into the experiment directory."""

    def test_scaffold_csv_copied(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )

        copied_csv = out / sample_classification_csv.name
        assert copied_csv.exists()
        assert copied_csv.read_bytes() == sample_classification_csv.read_bytes()


class TestScaffoldDotClaude:
    """.claude/ directory is created with settings.json and hook script."""

    @pytest.fixture
    def scaffolded(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )
        return out

    def test_scaffold_creates_dot_claude_dir(self, scaffolded):
        assert (scaffolded / ".claude").is_dir()

    def test_scaffold_settings_json_valid(self, scaffolded):
        settings_path = scaffolded / ".claude" / "settings.json"
        assert settings_path.exists()
        data = json.loads(settings_path.read_text())
        assert isinstance(data, dict)

    def test_scaffold_settings_permissions(self, scaffolded):
        settings_path = scaffolded / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text())
        allow = data["permissions"]["allow"]
        expected = [
            "Bash(*)",
            "Edit(*)",
            "Write(*)",
            "Read",
            "Glob",
            "Grep",
        ]
        assert allow == expected

    def test_scaffold_settings_deny(self, scaffolded):
        settings_path = scaffolded / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text())
        deny = data["permissions"]["deny"]
        assert deny == [
            "Edit(prepare.py)",
            "Write(prepare.py)",
            "Edit(forecast.py)",
            "Write(forecast.py)",
        ]

    def test_scaffold_settings_hooks(self, scaffolded):
        settings_path = scaffolded / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text())
        hooks_list = data["hooks"]["PreToolUse"]
        assert len(hooks_list) == 1
        entry = hooks_list[0]
        assert entry["matcher"] == "Edit|Write"
        assert entry["hooks"][0]["type"] == "command"

    def test_scaffold_hook_script_exists_and_executable(self, scaffolded):
        hook_path = scaffolded / ".claude" / "hooks" / "guard-frozen.sh"
        assert hook_path.exists()
        mode = hook_path.stat().st_mode
        assert mode & stat.S_IXUSR != 0, "guard-frozen.sh is not executable"

    def test_scaffold_hook_denies_prepare_py(self, scaffolded):
        hook_path = scaffolded / ".claude" / "hooks" / "guard-frozen.sh"
        input_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": "/some/experiment/prepare.py"},
        })
        result = subprocess.run(
            ["bash", str(hook_path)],
            input=input_json,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        output = result.stdout.strip()
        assert output, "Hook should output deny JSON for prepare.py"
        deny_data = json.loads(output)
        hook_output = deny_data["hookSpecificOutput"]
        assert hook_output["permissionDecision"] == "deny"

    def test_scaffold_hook_allows_train_py(self, scaffolded):
        hook_path = scaffolded / ".claude" / "hooks" / "guard-frozen.sh"
        input_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": "/some/experiment/train.py"},
        })
        result = subprocess.run(
            ["bash", str(hook_path)],
            input=input_json,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", "Hook should output nothing for train.py"

    def test_settings_deny_forecast(self, scaffolded):
        settings_path = scaffolded / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text())
        deny = data["permissions"]["deny"]
        assert "Edit(forecast.py)" in deny, f"Missing Edit(forecast.py) in deny list: {deny}"
        assert "Write(forecast.py)" in deny, f"Missing Write(forecast.py) in deny list: {deny}"

    def test_scaffold_hook_denies_forecast_py(self, scaffolded):
        hook_path = scaffolded / ".claude" / "hooks" / "guard-frozen.sh"
        input_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": "/some/experiment/forecast.py"},
        })
        result = subprocess.run(
            ["bash", str(hook_path)],
            input=input_json,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        output = result.stdout.strip()
        assert output, "Hook should output deny JSON for forecast.py"
        deny_data = json.loads(output)
        hook_output = deny_data["hookSpecificOutput"]
        assert hook_output["permissionDecision"] == "deny"


class TestScaffoldForecasting:
    """Tests for forecasting scaffold path (date_col branch)."""

    def test_forecast_scaffold_creates_all_files(self, sample_forecast_csv, tmp_path):
        """scaffold with date_col='date' creates all expected files."""
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_forecast_csv,
            target_column="revenue",
            metric="mape",
            goal="Forecast quarterly revenue",
            output_dir=out,
            date_col="date",
        )
        expected_files = [
            "prepare.py",
            "forecast.py",
            "train.py",
            "program.md",
            "CLAUDE.md",
            ".gitignore",
            "pyproject.toml",
            sample_forecast_csv.name,
        ]
        actual_files = [f.name for f in out.iterdir() if f.is_file()]
        for fname in expected_files:
            assert fname in actual_files, f"Missing file: {fname}"

    def test_forecast_train_uses_forecast_template(self, sample_forecast_csv, tmp_path):
        """Generated train.py contains forecast-template markers."""
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_forecast_csv,
            target_column="revenue",
            metric="mape",
            goal="Forecast quarterly revenue",
            output_dir=out,
            date_col="date",
        )
        content = (out / "train.py").read_text()
        assert "from forecast import" in content
        assert "walk_forward_evaluate" in content

    def test_forecast_train_date_column_substituted(self, sample_forecast_csv, tmp_path):
        """Generated train.py has DATE_COLUMN substituted with the actual date column name."""
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_forecast_csv,
            target_column="revenue",
            metric="mape",
            goal="Forecast quarterly revenue",
            output_dir=out,
            date_col="date",
        )
        content = (out / "train.py").read_text()
        assert 'DATE_COLUMN = "date"' in content

    def test_forecast_claude_md_uses_forecast_template(self, sample_forecast_csv, tmp_path):
        """Generated CLAUDE.md uses the forecast template (not the standard one)."""
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_forecast_csv,
            target_column="revenue",
            metric="mape",
            goal="Forecast quarterly revenue",
            output_dir=out,
            date_col="date",
        )
        content = (out / "CLAUDE.md").read_text()
        # claude_forecast.md.tmpl contains forecasting-specific text
        assert any(kw in content for kw in ["dual-baseline", "seasonal", "walk_forward"])

    def test_forecast_program_md_time_range(self, sample_forecast_csv, tmp_path):
        """Generated program.md contains the date range of the dataset."""
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_forecast_csv,
            target_column="revenue",
            metric="mape",
            goal="Forecast quarterly revenue",
            output_dir=out,
            date_col="date",
        )
        content = (out / "program.md").read_text()
        assert "2015" in content
        assert "2024" in content

    def test_forecast_program_md_frequency(self, sample_forecast_csv, tmp_path):
        """Generated program.md contains the inferred frequency."""
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_forecast_csv,
            target_column="revenue",
            metric="mape",
            goal="Forecast quarterly revenue",
            output_dir=out,
            date_col="date",
        )
        content = (out / "program.md").read_text()
        assert "QS" in content or "frequency" in content.lower()

    def test_forecast_program_md_naive_mape(self, sample_forecast_csv, tmp_path):
        """Generated program.md contains Naive MAPE score."""
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_forecast_csv,
            target_column="revenue",
            metric="mape",
            goal="Forecast quarterly revenue",
            output_dir=out,
            date_col="date",
        )
        content = (out / "program.md").read_text()
        assert "Naive MAPE" in content
        # Check a decimal number is present
        import re
        assert re.search(r"\d+\.\d+", content), "No decimal number found in program.md"

    def test_forecast_program_md_seasonal_naive_mape(self, sample_forecast_csv, tmp_path):
        """Generated program.md contains Seasonal Naive MAPE score."""
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_forecast_csv,
            target_column="revenue",
            metric="mape",
            goal="Forecast quarterly revenue",
            output_dir=out,
            date_col="date",
        )
        content = (out / "program.md").read_text()
        assert "Seasonal Naive MAPE" in content

    def test_forecast_program_md_direction(self, sample_forecast_csv, tmp_path):
        """Generated program.md says 'minimize' and does NOT say 'higher is always better'."""
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_forecast_csv,
            target_column="revenue",
            metric="mape",
            goal="Forecast quarterly revenue",
            output_dir=out,
            date_col="date",
        )
        content = (out / "program.md").read_text()
        assert "minimize" in content
        assert "higher is always better" not in content.lower()


class TestScaffoldStandardPathUnchanged:
    """Ensure date_col=None preserves the v1.0 scaffold path exactly."""

    def test_standard_scaffold_unchanged(self, sample_classification_csv, tmp_path):
        """scaffold with date_col=None produces standard train.py and CLAUDE.md."""
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
            date_col=None,
        )
        train_content = (out / "train.py").read_text()
        claude_content = (out / "CLAUDE.md").read_text()
        # Standard template uses prepare module imports (not forecast imports)
        assert "from prepare import" in train_content
        # Standard CLAUDE.md should NOT contain forecast-specific text
        assert "walk_forward" not in claude_content
        assert "seasonal" not in claude_content.lower() or "Forecasting" not in claude_content


class TestRenderExperimentsMd:
    """Tests for render_experiments_md template function."""

    def test_render_experiments_md_returns_string(self):
        from automl.templates import render_experiments_md

        result = render_experiments_md(
            dataset_name="iris",
            data_summary="- **Shape:** 150 rows x 4 columns",
            baselines="- **Naive:** 0.3333",
        )
        assert isinstance(result, str)

    def test_render_experiments_md_has_dataset_name_header(self):
        from automl.templates import render_experiments_md

        result = render_experiments_md(
            dataset_name="iris",
            data_summary="- **Shape:** 150 rows x 4 columns",
            baselines="- **Naive:** 0.3333",
        )
        assert "# Experiment Journal: iris" in result

    def test_render_experiments_md_has_what_works_section(self):
        from automl.templates import render_experiments_md

        result = render_experiments_md(
            dataset_name="iris",
            data_summary="- **Shape:** 150 rows x 4 columns",
            baselines="- **Naive:** 0.3333",
        )
        assert "## What Works" in result

    def test_render_experiments_md_has_what_doesnt_section(self):
        from automl.templates import render_experiments_md

        result = render_experiments_md(
            dataset_name="iris",
            data_summary="summary text",
            baselines="baseline text",
        )
        assert "## What Doesn't" in result

    def test_render_experiments_md_has_hypotheses_queue_section(self):
        from automl.templates import render_experiments_md

        result = render_experiments_md(
            dataset_name="iris",
            data_summary="summary text",
            baselines="baseline text",
        )
        assert "## Hypotheses Queue" in result

    def test_render_experiments_md_has_error_patterns_section(self):
        from automl.templates import render_experiments_md

        result = render_experiments_md(
            dataset_name="iris",
            data_summary="summary text",
            baselines="baseline text",
        )
        assert "## Error Patterns" in result

    def test_render_experiments_md_has_dataset_context_section(self):
        from automl.templates import render_experiments_md

        result = render_experiments_md(
            dataset_name="iris",
            data_summary="- **Shape:** 150 rows x 4 columns",
            baselines="- **Naive MAPE:** 0.3333",
        )
        assert "## Dataset Context" in result

    def test_render_experiments_md_contains_data_summary(self):
        from automl.templates import render_experiments_md

        result = render_experiments_md(
            dataset_name="iris",
            data_summary="- **Shape:** 150 rows x 4 columns",
            baselines="baseline text",
        )
        assert "- **Shape:** 150 rows x 4 columns" in result

    def test_render_experiments_md_contains_baselines(self):
        from automl.templates import render_experiments_md

        result = render_experiments_md(
            dataset_name="iris",
            data_summary="summary text",
            baselines="- **Naive MAPE:** 0.3333",
        )
        assert "- **Naive MAPE:** 0.3333" in result


class TestScaffoldExperimentsMd:
    """experiments.md is created by scaffold_experiment in both paths."""

    def test_scaffold_creates_experiments_md(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )
        assert (out / "experiments.md").exists(), "experiments.md not found in scaffold output"

    def test_experiments_md_has_four_sections(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )
        content = (out / "experiments.md").read_text()
        assert "## What Works" in content
        assert "## What Doesn't" in content
        assert "## Hypotheses Queue" in content
        assert "## Error Patterns" in content

    def test_experiments_md_has_dataset_context(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )
        content = (out / "experiments.md").read_text()
        # Dataset context section should exist and have real data
        assert "## Dataset Context" in content
        # Should contain data summary (200 rows in fixture)
        assert "200" in content
        # Should contain baselines
        assert "baseline" in content.lower() or "most_frequent" in content or "Baselines" in content

    def test_forecast_scaffold_creates_experiments_md(self, sample_forecast_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_forecast_csv,
            target_column="revenue",
            metric="mape",
            goal="Forecast quarterly revenue",
            output_dir=out,
            date_col="date",
        )
        assert (out / "experiments.md").exists(), "experiments.md not found in forecast scaffold output"
        content = (out / "experiments.md").read_text()
        assert "## What Works" in content
        assert "## What Doesn't" in content
        assert "## Hypotheses Queue" in content
        assert "## Error Patterns" in content
        assert "## Dataset Context" in content
        # Should contain forecast baselines (MAPE values)
        assert "Naive MAPE" in content or "MAPE" in content


class TestScaffoldForecast:
    """Tests for forecast.py copy and optuna dependency."""

    def test_scaffold_pyproject_has_optuna(self, sample_classification_csv, tmp_path):
        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )
        content = (out / "pyproject.toml").read_text()
        assert "optuna" in content, "Missing optuna dependency in pyproject.toml"

    def test_scaffold_copies_forecast_py(self, sample_classification_csv, tmp_path):
        import automl.forecast as forecast_mod

        out = tmp_path / "experiment"
        scaffold_experiment(
            data_path=sample_classification_csv,
            target_column="target",
            metric="accuracy",
            goal="Predict target class",
            output_dir=out,
        )
        assert (out / "forecast.py").exists(), "forecast.py not found in experiment directory"
        source_path = inspect.getfile(forecast_mod)
        source_bytes = Path(source_path).read_bytes()
        copied_bytes = (out / "forecast.py").read_bytes()
        assert copied_bytes == source_bytes, "forecast.py in experiment dir does not match installed source"
