"""
Action Classification Engine.

Classifies every tool call as safe, reversible, or irreversible.
The classification drives the entire Rewind pipeline: safe actions execute
immediately, reversible ones get a snapshot first, and irreversible ones
require out-of-band human approval.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger(__name__)


class ActionRisk(enum.Enum):
    """Risk classification for an agent action."""

    SAFE = "safe"
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"


@dataclass(frozen=True)
class Classification:
    """Result of classifying a single action."""

    risk: ActionRisk
    reason: str
    tool_name: str
    action_summary: str
    matched_rule: str | None = None
    confidence: float = 1.0

    def __str__(self) -> str:
        return f"[{self.risk.value}] {self.tool_name}: {self.reason}"


@dataclass(frozen=True)
class ActionRequest:
    """An incoming action from an agent, to be classified before execution."""

    tool_name: str
    method: str
    arguments: dict[str, object] = field(default_factory=dict)
    raw_command: str = ""
    context: dict[str, object] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        if self.raw_command:
            return f"{self.tool_name}.{self.method}: {self.raw_command[:120]}"
        return f"{self.tool_name}.{self.method}({', '.join(f'{k}={v!r}' for k, v in list(self.arguments.items())[:3])})"


class Classifier(Protocol):
    """Interface for action classifiers (rule-based, LLM, or plugin-provided)."""

    def classify(self, action: ActionRequest) -> Classification | None:
        """
        Classify an action. Return None if this classifier has no opinion.
        The engine tries classifiers in order and uses the first non-None result.
        """
        ...


class ClassificationEngine:
    """
    Orchestrates multiple classifiers in priority order.

    Fail-safe: if no classifier has an opinion, the action is classified
    as IRREVERSIBLE (deny-by-default).
    """

    def __init__(self, classifiers: list[Classifier] | None = None) -> None:
        self._classifiers: list[Classifier] = classifiers or []

    def add_classifier(self, classifier: Classifier, *, priority: int = -1) -> None:
        """Add a classifier. Lower priority index = checked first."""
        if priority < 0 or priority >= len(self._classifiers):
            self._classifiers.append(classifier)
        else:
            self._classifiers.insert(priority, classifier)

    def classify(self, action: ActionRequest) -> Classification:
        """Classify an action through the chain of classifiers."""
        for classifier in self._classifiers:
            try:
                result = classifier.classify(action)
                if result is not None:
                    logger.info("Action classified: %s", result)
                    return result
            except Exception:
                logger.exception(
                    "Classifier %s raised an exception; skipping",
                    type(classifier).__name__,
                )

        # Fail-safe: unknown actions are treated as irreversible.
        fallback = Classification(
            risk=ActionRisk.IRREVERSIBLE,
            reason="No classifier recognized this action; fail-safe to IRREVERSIBLE",
            tool_name=action.tool_name,
            action_summary=action.summary,
            matched_rule="__fail_safe__",
            confidence=0.0,
        )
        logger.warning("Fail-safe classification applied: %s", fallback)
        return fallback
