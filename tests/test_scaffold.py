"""Tests for experiment directory scaffolding."""

import inspect
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
        assert len(list(out.iterdir())) == 7


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
        for pattern in ["results.tsv", "run.log", "__pycache__/", ".venv/"]:
            assert pattern in content, f"Missing .gitignore pattern: {pattern}"


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
