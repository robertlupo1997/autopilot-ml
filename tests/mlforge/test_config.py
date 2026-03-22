"""Tests for mlforge.config — Config dataclass with TOML loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from mlforge.config import CONFIG_FILENAME, Config


class TestConfigDefaults:
    """Config.load() with no file returns sensible defaults."""

    def test_default_domain(self):
        config = Config.load()
        assert config.domain == "tabular"

    def test_default_metric(self):
        config = Config.load()
        assert config.metric == "accuracy"

    def test_default_direction(self):
        config = Config.load()
        assert config.direction == "maximize"

    def test_default_budget_minutes(self):
        config = Config.load()
        assert config.budget_minutes == 60

    def test_default_budget_experiments(self):
        config = Config.load()
        assert config.budget_experiments == 50

    def test_default_frozen_files(self):
        config = Config.load()
        assert config.frozen_files == ["prepare.py"]

    def test_default_mutable_files(self):
        config = Config.load()
        assert config.mutable_files == ["train.py"]

    def test_default_plugin_settings(self):
        config = Config.load()
        assert config.plugin_settings == {}


class TestConfigFromToml:
    """Config.load(path) reads a valid mlforge.config.toml."""

    def test_full_toml_loads_all_fields(self, tmp_dir: Path, sample_config_toml: str):
        config_path = tmp_dir / CONFIG_FILENAME
        config_path.write_text(sample_config_toml)
        config = Config.load(config_path)
        assert config.domain == "tabular"
        assert config.metric == "rmse"
        assert config.direction == "minimize"
        assert config.budget_minutes == 120
        assert config.budget_experiments == 100
        assert config.frozen_files == ["prepare.py", "evaluate.py"]
        assert config.mutable_files == ["train.py", "features.py"]
        assert config.plugin_settings == {"model_families": ["sklearn", "xgboost"]}

    def test_partial_toml_fills_defaults(self, tmp_dir: Path):
        config_path = tmp_dir / CONFIG_FILENAME
        config_path.write_text('domain = "forecasting"\n')
        config = Config.load(config_path)
        assert config.domain == "forecasting"
        assert config.metric == "accuracy"  # default
        assert config.budget_minutes == 60  # default

    def test_missing_file_returns_defaults(self, tmp_dir: Path):
        config_path = tmp_dir / "nonexistent.toml"
        config = Config.load(config_path)
        assert config.domain == "tabular"
        assert config.metric == "accuracy"


class TestConfigValidation:
    """Config validates direction values."""

    def test_invalid_direction_raises(self, tmp_dir: Path):
        config_path = tmp_dir / CONFIG_FILENAME
        config_path.write_text("""\
[metric]
name = "accuracy"
direction = "sideways"
""")
        with pytest.raises(ValueError, match="direction"):
            Config.load(config_path)

    def test_maximize_is_valid(self, tmp_dir: Path):
        config_path = tmp_dir / CONFIG_FILENAME
        config_path.write_text("""\
[metric]
direction = "maximize"
""")
        config = Config.load(config_path)
        assert config.direction == "maximize"

    def test_minimize_is_valid(self, tmp_dir: Path):
        config_path = tmp_dir / CONFIG_FILENAME
        config_path.write_text("""\
[metric]
direction = "minimize"
""")
        config = Config.load(config_path)
        assert config.direction == "minimize"
