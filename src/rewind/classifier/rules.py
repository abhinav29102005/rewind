"""
Rule-based action classifier.

Uses pattern matching on tool names, methods, and raw command text to
classify actions. Rules are loaded from YAML policy files or defined
programmatically.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

from .engine import ActionRequest, ActionRisk, Classification, Classifier

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    """A single classification rule."""

    name: str
    risk: ActionRisk
    reason_template: str
    # Matching criteria (all are optional; at least one should be set)
    tool_pattern: str | None = None
    method_pattern: str | None = None
    command_patterns: list[str] = field(default_factory=list)
    arg_patterns: dict[str, str] = field(default_factory=dict)

    def matches(self, action: ActionRequest) -> bool:
        """Check if this rule matches the given action."""
        if self.tool_pattern and not re.search(self.tool_pattern, action.tool_name, re.IGNORECASE):
            return False
        if self.method_pattern and not re.search(
            self.method_pattern, action.method, re.IGNORECASE
        ):
            return False
        if self.command_patterns:
            text = action.raw_command or ""
            if not any(re.search(p, text, re.IGNORECASE) for p in self.command_patterns):
                return False
        if self.arg_patterns:
            for key, pattern in self.arg_patterns.items():
                val = str(action.arguments.get(key, ""))
                if not re.search(pattern, val, re.IGNORECASE):
                    return False
        return True


# ── Built-in rules ──────────────────────────────────────────────────────────

_BUILTIN_IRREVERSIBLE_COMMANDS = [
    r"\bDROP\s+(TABLE|DATABASE|SCHEMA|INDEX)\b",
    r"\bTRUNCATE\s+TABLE\b",
    r"\bDELETE\s+FROM\b(?!.*\bWHERE\b)",  # DELETE without WHERE
    r"\brm\s+(-rf?|--recursive)\b",
    r"\brmdir\b",
    r"\bmkfs\b",
    r"\bformat\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bkill\s+-9\b",
    r"\bgit\s+push\s+.*--force\b",
    r"\bgit\s+branch\s+-[dD]\b",
    r"\baws\s+s3\s+rb\b",
    r"\baws\s+s3\s+rm\b.*--recursive",
    r"\baws\s+iam\s+delete-",
    r"\bkubectl\s+delete\b",
    r"\bdocker\s+rm\b",
    r"\bdocker\s+system\s+prune\b",
]

_BUILTIN_REVERSIBLE_COMMANDS = [
    r"\bUPDATE\b.*\bSET\b",
    r"\bINSERT\s+INTO\b",
    r"\bALTER\s+TABLE\b",
    r"\bgit\s+commit\b",
    r"\bgit\s+push\b(?!.*--force)",
    r"\bcp\b",
    r"\bmv\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\baws\s+s3\s+cp\b",
    r"\baws\s+s3\s+mv\b",
]

_BUILTIN_SAFE_COMMANDS = [
    r"\bSELECT\b",
    r"\bSHOW\b",
    r"\bDESCRIBE\b",
    r"\bEXPLAIN\b",
    r"\bls\b",
    r"\bcat\b",
    r"\bhead\b",
    r"\btail\b",
    r"\bgrep\b",
    r"\bfind\b",
    r"\bwc\b",
    r"\becho\b",
    r"\bpwd\b",
    r"\bwhoami\b",
    r"\baws\s+s3\s+ls\b",
    r"\bkubectl\s+get\b",
    r"\bdocker\s+ps\b",
    r"\bgit\s+status\b",
    r"\bgit\s+log\b",
    r"\bgit\s+diff\b",
]


def _build_builtin_rules() -> list[Rule]:
    """Create the built-in rule set."""
    rules: list[Rule] = []

    for pattern in _BUILTIN_IRREVERSIBLE_COMMANDS:
        rules.append(
            Rule(
                name=f"builtin:irreversible:{pattern[:40]}",
                risk=ActionRisk.IRREVERSIBLE,
                reason_template=f"Command matches destructive pattern: {pattern}",
                command_patterns=[pattern],
            )
        )

    for pattern in _BUILTIN_REVERSIBLE_COMMANDS:
        rules.append(
            Rule(
                name=f"builtin:reversible:{pattern[:40]}",
                risk=ActionRisk.REVERSIBLE,
                reason_template=f"Command matches reversible pattern: {pattern}",
                command_patterns=[pattern],
            )
        )

    for pattern in _BUILTIN_SAFE_COMMANDS:
        rules.append(
            Rule(
                name=f"builtin:safe:{pattern[:40]}",
                risk=ActionRisk.SAFE,
                reason_template=f"Command matches safe/read-only pattern: {pattern}",
                command_patterns=[pattern],
            )
        )

    return rules


class RuleClassifier(Classifier):
    """
    Classifies actions using ordered rules.

    Rules are checked in order: irreversible first, then reversible, then safe.
    This ensures the most dangerous classification wins when multiple rules match.
    """

    def __init__(self, *, include_builtins: bool = True) -> None:
        self._rules: list[Rule] = []
        if include_builtins:
            self._rules.extend(_build_builtin_rules())
        # Sort: irreversible first, then reversible, then safe
        self._sort_rules()

    def _sort_rules(self) -> None:
        priority = {ActionRisk.IRREVERSIBLE: 0, ActionRisk.REVERSIBLE: 1, ActionRisk.SAFE: 2}
        self._rules.sort(key=lambda r: priority.get(r.risk, 1))

    def add_rule(self, rule: Rule) -> None:
        """Add a custom rule and re-sort."""
        self._rules.append(rule)
        self._sort_rules()

    def load_policy_file(self, path: Path) -> int:
        """
        Load rules from a YAML policy file.
        Returns the number of rules loaded.
        """
        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        count = 0
        for rule_data in data.get("rules", []):
            risk_str = rule_data.get("risk", "irreversible").upper()
            try:
                risk = ActionRisk(risk_str.lower())
            except ValueError:
                logger.warning("Unknown risk level %r in %s, skipping", risk_str, path)
                continue

            rule = Rule(
                name=rule_data.get("name", f"policy:{path.stem}:{count}"),
                risk=risk,
                reason_template=rule_data.get("reason", f"Matched policy rule in {path.name}"),
                tool_pattern=rule_data.get("tool_pattern"),
                method_pattern=rule_data.get("method_pattern"),
                command_patterns=rule_data.get("command_patterns", []),
                arg_patterns=rule_data.get("arg_patterns", {}),
            )
            self.add_rule(rule)
            count += 1

        logger.info("Loaded %d rules from %s", count, path)
        return count

    def classify(self, action: ActionRequest) -> Classification | None:
        """Classify an action using the first matching rule."""
        for rule in self._rules:
            if rule.matches(action):
                return Classification(
                    risk=rule.risk,
                    reason=rule.reason_template,
                    tool_name=action.tool_name,
                    action_summary=action.summary,
                    matched_rule=rule.name,
                )
        return None
