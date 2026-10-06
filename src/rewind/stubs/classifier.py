"""Stub base classifier (Phase 1 stand-in)."""

from __future__ import annotations

import re

from ..contracts import ActionRequest, Classification, RiskClass

_SQL_BAD = re.compile(r"\b(DROP|TRUNCATE)\b", re.IGNORECASE)
_SQL_DELETE = re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE)
_SQL_WHERE = re.compile(r"\bWHERE\b", re.IGNORECASE)
_RM_RF = re.compile(r"\brm\s+-[a-zA-Z]*[rR][a-zA-Z]*f|\brm\s+-[a-zA-Z]*f[a-zA-Z]*[rR]")


class StubBaseClassifier:
    """DROP, TRUNCATE, unscoped DELETE and ``rm -rf`` are irreversible; else safe.

    # DECISION: regex is acceptable here only because this is a dev stub; the
    # real policy engine (rewind.policy) never regexes SQL.
    """

    name = "stub_base"

    def supports(self, action: ActionRequest) -> bool:
        return True

    def classify(self, action: ActionRequest) -> Classification:
        text = str(action.payload.get("statement") or action.payload.get("command") or "")
        risk = RiskClass.SAFE
        reasons = ["stub: no destructive pattern"]
        if _SQL_BAD.search(text) or _RM_RF.search(text) or (
            _SQL_DELETE.search(text) and not _SQL_WHERE.search(text)
        ):
            risk = RiskClass.IRREVERSIBLE
            reasons = ["stub: destructive pattern"]
        return Classification(action_id=action.id, risk=risk, reasons=reasons, rule_ids=["stub"])
