"""Plugin discovery and explicit loading system."""

from __future__ import annotations

import importlib.metadata
import logging
from typing import TYPE_CHECKING, Any

from ..contracts import Classifier
from .base import PluginClassifierWrapper, PluginKind, PluginMeta

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..config.models import PluginsConfig

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "rewind.plugins"

# In-memory registry for programmatic or testing plugins
_MANUAL_REGISTRY: dict[str, tuple[PluginMeta, Callable[..., Any]]] = {}


def register_manual_plugin(meta: PluginMeta, factory: Callable[..., Any]) -> None:
    meta.validate_api_version()
    _MANUAL_REGISTRY[meta.name] = (meta, factory)


def clear_manual_plugins() -> None:
    _MANUAL_REGISTRY.clear()


def list_installed_plugins() -> list[PluginMeta]:
    """Discover all installed plugins without instantiating them."""
    installed: list[PluginMeta] = []

    # Check manual registry
    for meta, _ in _MANUAL_REGISTRY.values():
        installed.append(meta)

    # Check entry points
    try:
        eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
        for ep in eps:
            try:
                plugin_cls_or_factory = ep.load()
                ep_meta = getattr(plugin_cls_or_factory, "plugin_meta", None)
                if isinstance(ep_meta, PluginMeta):
                    installed.append(ep_meta)
                elif hasattr(plugin_cls_or_factory, "name") and hasattr(plugin_cls_or_factory, "version"):
                    kind = getattr(plugin_cls_or_factory, "kind", PluginKind.CLASSIFIER)
                    new_meta = PluginMeta(
                        name=ep.name,
                        version=getattr(plugin_cls_or_factory, "version", "1.0.0"),
                        kind=kind,
                        description=getattr(plugin_cls_or_factory, "__doc__", "") or "",
                    )
                    installed.append(new_meta)
            except Exception as e:
                logger.warning("Failed to inspect plugin entry point %s: %e", ep.name, e)
    except Exception as e:
        logger.debug("No entry points found for %s: %e", ENTRY_POINT_GROUP, e)

    return installed


def load_enabled_plugins(
    enabled_names: list[str],
    plugins_config: PluginsConfig | None = None,
) -> dict[str, Any]:
    """Load only the plugins explicitly listed in enabled_names.

    Installed but not enabled plugins are never loaded.
    """
    timeout = plugins_config.classifier_timeout_seconds if plugins_config else 2.0
    loaded: dict[str, Any] = {}

    for name in enabled_names:
        # Check manual registry first
        if name in _MANUAL_REGISTRY:
            meta, factory = _MANUAL_REGISTRY[name]
            meta.validate_api_version()
            instance = factory()
            if meta.kind == PluginKind.CLASSIFIER:
                instance = PluginClassifierWrapper(instance, timeout_seconds=timeout)
            loaded[name] = instance
            continue

        # Check entry points
        found = False
        try:
            eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
            for ep in eps:
                if ep.name == name:
                    plugin_factory = ep.load()
                    ep_meta = getattr(plugin_factory, "plugin_meta", None)
                    if isinstance(ep_meta, PluginMeta):
                        ep_meta.validate_api_version()
                    instance = plugin_factory() if callable(plugin_factory) else plugin_factory
                    if isinstance(instance, Classifier):
                        instance = PluginClassifierWrapper(instance, timeout_seconds=timeout)
                    loaded[name] = instance
                    found = True
                    break
        except Exception as e:
            raise RuntimeError(f"Error loading plugin {name!r}: {e}") from e

        if not found:
            raise ValueError(f"Plugin {name!r} is enabled in config but not installed or found")

    return loaded
