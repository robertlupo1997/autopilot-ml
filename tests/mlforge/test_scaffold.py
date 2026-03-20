"""Tests for mlforge.scaffold -- experiment directory scaffolding."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from mlforge.config import Config
from mlforge.scaffold import scaffold_experiment


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    """Create a minimal CSV dataset file."""
    ds = tmp_path / "data.csv"
    ds.write_text("feature,target\n1,0\n2,1\n3,0\n")
    return ds


@pytest.fixture
def target_dir(tmp_path: Path) -> Path:
    """Return a non-existent target directory path."""
    return tmp_path / "experiment"


@pytest.fixture
def config() -> Config:
    """Return a default Config."""
    return Config()


class TestScaffoldCreatesDirectory:
    """scaffold_experiment creates target directory if it does not exist."""

    def test_creates_target_dir(self, config, dataset, target_dir):
        result = scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        assert target_dir.exists()
        assert target_dir.is_dir()

    def test_returns_target_dir(self, config, dataset, target_dir):
        result = scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        assert result == target_dir


class TestScaffoldCopiesDataset:
    """scaffold_experiment copies dataset file to target directory."""

    def test_dataset_copied(self, config, dataset, target_dir):
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        copied = target_dir / "data.csv"
        assert copied.exists()
        assert copied.read_text() == dataset.read_text()


class TestScaffoldPluginFiles:
    """scaffold_experiment calls plugin.scaffold() to create domain-specific files."""

    def test_prepare_py_created(self, config, dataset, target_dir):
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        assert (target_dir / "prepare.py").exists()

    def test_train_py_created(self, config, dataset, target_dir):
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        assert (target_dir / "train.py").exists()


class TestScaffoldTemplates:
    """scaffold_experiment renders CLAUDE.md and experiments.md."""

    def test_claude_md_created(self, config, dataset, target_dir):
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        assert (target_dir / "CLAUDE.md").exists()
        content = (target_dir / "CLAUDE.md").read_text()
        assert len(content) > 0

    def test_experiments_md_created(self, config, dataset, target_dir):
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        assert (target_dir / "experiments.md").exists()
        content = (target_dir / "experiments.md").read_text()
        assert len(content) > 0


class TestScaffoldHookFiles:
    """scaffold_experiment writes hook files for frozen enforcement."""

    def test_settings_json_created(self, config, dataset, target_dir):
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        settings_path = target_dir / ".claude" / "settings.json"
        assert settings_path.exists()

    def test_settings_json_has_deny_rules(self, config, dataset, target_dir):
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        settings_path = target_dir / ".claude" / "settings.json"
        settings = json.loads(settings_path.read_text())
        deny = settings["permissions"]["deny"]
        # Should have deny rules for frozen files
        assert len(deny) > 0

    def test_guard_script_created(self, config, dataset, target_dir):
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        guard = target_dir / ".claude" / "hooks" / "guard-frozen.sh"
        assert guard.exists()

    def test_guard_script_is_executable(self, config, dataset, target_dir):
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        guard = target_dir / ".claude" / "hooks" / "guard-frozen.sh"
        assert os.access(guard, os.X_OK)


class TestScaffoldConfigToml:
    """scaffold_experiment writes mlforge.config.toml with current config."""

    def test_config_toml_created(self, config, dataset, target_dir):
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        config_path = target_dir / "mlforge.config.toml"
        assert config_path.exists()

    def test_config_toml_contains_domain(self, config, dataset, target_dir):
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        config_path = target_dir / "mlforge.config.toml"
        content = config_path.read_text()
        assert 'domain = "tabular"' in content


class TestScaffoldValidation:
    """scaffold_experiment raises on invalid inputs and configs."""

    def setup_method(self):
        """Clear plugin registry before each test."""
        from mlforge.plugins import _registry
        _registry.clear()

    def test_nonexistent_dataset_raises(self, config, target_dir):
        with pytest.raises(FileNotFoundError):
            scaffold_experiment(
                config=config,
                dataset_path=Path("/nonexistent/data.csv"),
                target_dir=target_dir,
                run_id="run-1",
            )

    def test_rejects_invalid_tabular_metric(self, dataset, target_dir):
        cfg = Config(domain="tabular", metric="nonexistent")
        with pytest.raises(ValueError, match=r"Invalid config.*tabular"):
            scaffold_experiment(config=cfg, dataset_path=dataset, target_dir=target_dir, run_id="run-1")

    def test_rejects_ft_without_model_name(self, dataset, target_dir):
        cfg = Config(domain="finetuning", metric="perplexity")
        with pytest.raises(ValueError, match="model_name"):
            scaffold_experiment(config=cfg, dataset_path=dataset, target_dir=target_dir, run_id="run-1")

    def test_rejects_dl_invalid_task(self, dataset, target_dir):
        cfg = Config(domain="deeplearning", metric="accuracy", plugin_settings={"task": "invalid_task"})
        with pytest.raises(ValueError, match="Unknown deeplearning task"):
            scaffold_experiment(config=cfg, dataset_path=dataset, target_dir=target_dir, run_id="run-1")

    def test_valid_config_scaffolds_ok(self, dataset, target_dir):
        cfg = Config(domain="tabular")
        result = scaffold_experiment(config=cfg, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        assert result == target_dir


class TestTaskTypeMapping:
    """_map_task_for_domain maps profiler task types to domain-specific types."""

    def setup_method(self):
        """Clear plugin registry before each test."""
        from mlforge.plugins import _registry
        _registry.clear()

    def test_dl_classification_mapped_to_image_classification(self, dataset, target_dir):
        cfg = Config(domain="deeplearning", metric="accuracy", plugin_settings={"task": "classification"})
        scaffold_experiment(config=cfg, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        assert cfg.plugin_settings["task"] == "image_classification"

    def test_dl_regression_mapped_to_custom(self, dataset, target_dir):
        cfg = Config(domain="deeplearning", metric="accuracy", plugin_settings={"task": "regression"})
        scaffold_experiment(config=cfg, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        assert cfg.plugin_settings["task"] == "custom"

    def test_dl_native_task_not_remapped(self, dataset, target_dir):
        cfg = Config(domain="deeplearning", metric="accuracy", plugin_settings={"task": "text_classification"})
        scaffold_experiment(config=cfg, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        assert cfg.plugin_settings["task"] == "text_classification"

    def test_tabular_task_passthrough(self, dataset, target_dir):
        cfg = Config(domain="tabular", plugin_settings={"task": "classification"})
        scaffold_experiment(config=cfg, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        assert cfg.plugin_settings["task"] == "classification"

    def test_ft_task_no_mapping(self, dataset, target_dir):
        cfg = Config(domain="finetuning", metric="perplexity", plugin_settings={"task": "classification", "model_name": "test/model"})
        scaffold_experiment(config=cfg, dataset_path=dataset, target_dir=target_dir, run_id="run-1")
        assert cfg.plugin_settings["task"] == "classification"


class TestPluginRegistrationDispatch:
    """_ensure_plugin_registered dispatches registration by domain string."""

    def setup_method(self):
        """Clear plugin registry before each test."""
        from mlforge.plugins import _registry
        _registry.clear()

    def test_deeplearning_registered(self):
        from mlforge.scaffold import _ensure_plugin_registered
        from mlforge.plugins import get_plugin

        _ensure_plugin_registered("deeplearning")
        plugin = get_plugin("deeplearning")
        assert plugin.name == "deeplearning"

    def test_finetuning_registered(self):
        from mlforge.scaffold import _ensure_plugin_registered
        from mlforge.plugins import get_plugin

        _ensure_plugin_registered("finetuning")
        plugin = get_plugin("finetuning")
        assert plugin.name == "finetuning"

    def test_tabular_registered(self):
        from mlforge.scaffold import _ensure_plugin_registered
        from mlforge.plugins import get_plugin

        _ensure_plugin_registered("tabular")
        plugin = get_plugin("tabular")
        assert plugin.name == "tabular"

    def test_unknown_domain_noop(self):
        from mlforge.scaffold import _ensure_plugin_registered

        # Should not raise for unknown domain
        _ensure_plugin_registered("unknown_domain_xyz")

    def test_idempotent_registration(self):
        from mlforge.scaffold import _ensure_plugin_registered
        from mlforge.plugins import get_plugin

        _ensure_plugin_registered("deeplearning")
        plugin1 = get_plugin("deeplearning")
        _ensure_plugin_registered("deeplearning")
        plugin2 = get_plugin("deeplearning")
        assert plugin1 is plugin2


class TestScaffoldDomainDispatch:
    """scaffold_experiment dispatches registration by config.domain."""

    def setup_method(self):
        """Clear plugin registry before each test."""
        from mlforge.plugins import _registry
        _registry.clear()

    def test_scaffold_deeplearning_domain(self, dataset, target_dir):
        from mlforge.plugins import get_plugin

        config = Config(domain="deeplearning")
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-dl")
        plugin = get_plugin("deeplearning")
        assert plugin.name == "deeplearning"

    def test_scaffold_finetuning_domain(self, dataset, target_dir):
        from mlforge.plugins import get_plugin

        config = Config(domain="finetuning", metric="perplexity", plugin_settings={"model_name": "test/model"})
        scaffold_experiment(config=config, dataset_path=dataset, target_dir=target_dir, run_id="run-ft")
        plugin = get_plugin("finetuning")
        assert plugin.name == "finetuning"
