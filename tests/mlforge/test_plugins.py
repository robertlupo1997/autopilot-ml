"""Tests for DomainPlugin protocol and plugin registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from mlforge.config import Config
from mlforge.plugins import DomainPlugin, get_plugin, list_plugins, register_plugin


class MockTabularPlugin:
    """A mock plugin that conforms to DomainPlugin protocol."""

    name: str = "tabular"
    frozen_files: list[str] = ["prepare.py"]

    def scaffold(self, target_dir: Path, config: Config) -> None:
        (target_dir / "train.py").write_text("# train stub\n")

    def template_context(self, config: Config) -> dict:
        return {
            "domain_rules": [
                "Use scikit-learn for modeling",
                "Do not modify prepare.py",
            ],
            "extra_sections": [],
        }

    def validate_config(self, config: Config) -> list[str]:
        errors = []
        if config.metric not in ("accuracy", "f1", "rmse", "mape"):
            errors.append(f"Unknown metric: {config.metric}")
        return errors


class MockForecastPlugin:
    """A second mock plugin for list_plugins testing."""

    name: str = "forecast"
    frozen_files: list[str] = ["prepare.py", "forecast.py"]

    def scaffold(self, target_dir: Path, config: Config) -> None:
        pass

    def template_context(self, config: Config) -> dict:
        return {"domain_rules": ["Use walk-forward CV"], "extra_sections": []}

    def validate_config(self, config: Config) -> list[str]:
        return []


class TestDomainPluginProtocol:
    """Verify structural subtyping via Protocol."""

    def test_mock_plugin_isinstance(self):
        plugin = MockTabularPlugin()
        assert isinstance(plugin, DomainPlugin)

    def test_non_conforming_object_fails_isinstance(self):
        """An object missing required methods does not satisfy Protocol."""
        assert not isinstance("not a plugin", DomainPlugin)


class TestPluginRegistry:
    """Verify register/get/list operations."""

    @pytest.fixture(autouse=True)
    def _clear_registry(self):
        """Clear the registry before each test."""
        import mlforge.plugins as mod
        mod._registry.clear()

    def test_register_and_get_plugin(self):
        plugin = MockTabularPlugin()
        register_plugin(plugin)
        retrieved = get_plugin("tabular")
        assert retrieved is plugin

    def test_register_invalid_plugin_raises(self):
        with pytest.raises(ValueError, match="does not conform"):
            register_plugin("not a plugin")  # type: ignore

    def test_get_unknown_plugin_raises(self):
        with pytest.raises(KeyError):
            get_plugin("nonexistent")

    def test_list_plugins(self):
        register_plugin(MockTabularPlugin())
        register_plugin(MockForecastPlugin())
        names = list_plugins()
        assert names == ["forecast", "tabular"]

    def test_plugin_validate_config(self):
        plugin = MockTabularPlugin()
        config = Config()
        errors = plugin.validate_config(config)
        assert errors == []

    def test_plugin_validate_config_reports_errors(self):
        plugin = MockTabularPlugin()
        config = Config(metric="unknown_metric")
        errors = plugin.validate_config(config)
        assert len(errors) == 1
        assert "Unknown metric" in errors[0]
