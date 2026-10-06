"""Built-in defaults and helpers to locate shipped resources."""

from __future__ import annotations

from pathlib import Path

from .models import RewindConfig

#: The global default when no policy pack covers a tool. Fail closed.
GLOBAL_DEFAULT_RISK = "irreversible"


def default_config() -> RewindConfig:
    return RewindConfig()


def builtin_policy_dir() -> Path:
    """Directory of shipped policy packs.

    Wheels include them as ``rewind/_policies``; in a source checkout they
    live in the repository's top-level ``policies/`` directory.
    """
    pkg_dir = Path(__file__).resolve().parent.parent / "_policies"
    if pkg_dir.is_dir():
        return pkg_dir
    return Path(__file__).resolve().parents[3] / "policies"
