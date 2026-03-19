"""DomainPlugin Protocol and plugin registry.

Defines the structural subtyping contract for ML domain plugins.
Plugins provide domain-specific scaffolding, template context, and
config validation without requiring inheritance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from mlforge.config import Config


@runtime_checkable
class DomainPlugin(Protocol):
    """Protocol defining the interface for ML domain plugins.

    Any class with these attributes and methods satisfies this protocol
    via structural subtyping (no inheritance required).
    """

    name: str
    frozen_files: list[str]

    def scaffold(self, target_dir: Path, config: Config) -> None:
        """Create domain-specific files in the target directory."""
        ...

    def template_context(self, config: Config) -> dict:
        """Return template variables for Jinja2 CLAUDE.md rendering.

        Must include at minimum:
        - domain_rules: list[str] - domain-specific protocol rules
        - extra_sections: list[dict] - optional extra template sections
        """
        ...

    def validate_config(self, config: Config) -> list[str]:
        """Validate config for this domain, return list of error messages.

        Returns empty list if config is valid.
        """
        ...


# Module-level plugin registry
_registry: dict[str, DomainPlugin] = {}


def register_plugin(plugin: DomainPlugin) -> None:
    """Register a plugin in the global registry.

    Args:
        plugin: An object conforming to DomainPlugin protocol.

    Raises:
        ValueError: If the plugin does not conform to DomainPlugin.
    """
    if not isinstance(plugin, DomainPlugin):
        msg = f"{plugin!r} does not conform to DomainPlugin protocol"
        raise ValueError(msg)
    _registry[plugin.name] = plugin


def get_plugin(name: str) -> DomainPlugin:
    """Retrieve a registered plugin by name.

    Args:
        name: The plugin name (matches plugin.name attribute).

    Returns:
        The registered DomainPlugin instance.

    Raises:
        KeyError: If no plugin with the given name is registered.
    """
    return _registry[name]


def list_plugins() -> list[str]:
    """Return sorted list of registered plugin names."""
    return sorted(_registry.keys())
