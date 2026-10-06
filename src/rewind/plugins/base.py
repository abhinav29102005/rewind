"""
Plugin interface for Rewind.

Plugins can provide:
- Custom action classifiers
- Custom snapshot backends
- Custom approval channels (Slack, email, etc.)
- Custom policy rules
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..classifier.engine import ActionRequest, Classification, Classifier


class RewindPlugin(ABC):
    """Base class for all Rewind plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable plugin name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version string."""
        ...

    @property
    def description(self) -> str:
        """Optional description."""
        return ""

    def on_load(self, config: dict[str, Any]) -> None:
        """Called when the plugin is loaded. Override to initialize."""
        return None

    def on_unload(self) -> None:
        """Called when the plugin is unloaded. Override to clean up."""
        return None

    def get_classifiers(self) -> list[Classifier]:
        """Return any classifiers this plugin provides."""
        return []


class ClassifierPlugin(RewindPlugin):
    """A plugin that provides a custom classifier."""

    @abstractmethod
    def classify(self, action: ActionRequest) -> Classification | None:
        """Classify an action. Return None to defer to the next classifier."""
        ...

    def get_classifiers(self) -> list[Classifier]:
        return [self]
