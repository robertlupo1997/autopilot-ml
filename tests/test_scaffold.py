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
            "train.py",
            "program.md",
            "CLAUDE.md",
            ".gitignore",
            "pyproject.toml",
            sample_classification_csv.name,  # "data.csv"
        ]
        actual_files = [f.name for f in out.iterdir() if f.is_file()]
        for fname in expected_files:
            assert fname in actual_files, f"Missing file: {fname}"
        # 7 files + .claude/ dir = 8 top-level items
        assert len(list(out.iterdir())) == 8
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
        assert deny == ["Edit(prepare.py)", "Write(prepare.py)"]

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
