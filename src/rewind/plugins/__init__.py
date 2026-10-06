"""Rewind plugin architecture."""

from __future__ import annotations

from .base import (
    PluginClassifierWrapper,
    PluginKind,
    PluginMeta,
)
from .loader import (
    clear_manual_plugins,
    list_installed_plugins,
    load_enabled_plugins,
    register_manual_plugin,
)
from .testing import (
    assert_approval_channel_conformance,
    assert_classifier_conformance,
    assert_snapshot_backend_conformance,
)

__all__ = [
    "PluginClassifierWrapper",
    "PluginKind",
    "PluginMeta",
    "assert_approval_channel_conformance",
    "assert_classifier_conformance",
    "assert_snapshot_backend_conformance",
    "clear_manual_plugins",
    "list_installed_plugins",
    "load_enabled_plugins",
    "register_manual_plugin",
]
