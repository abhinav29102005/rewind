"""Configuration system: ``rewind.yaml`` schema, loader, fail-closed validation."""

from __future__ import annotations

from .loader import (
    ConfigError,
    apply_overlay,
    check_file_permissions,
    config_hash,
    load_config,
    relaxations,
)
from .models import PolicyOverlay, RewindConfig

__all__ = [
    "ConfigError",
    "PolicyOverlay",
    "RewindConfig",
    "apply_overlay",
    "check_file_permissions",
    "config_hash",
    "load_config",
    "relaxations",
]
