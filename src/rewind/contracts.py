"""
Shared contracts between Phase 1 (core) and Phase 2/3 (ecosystem, team).

This module is a contract. Changes must be additive; any breaking change must
be logged in ``CONTRACT_CHANGES.md`` and announced to the other workstreams.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

#: Plugin API version. Plugins declaring a different *major* version are rejected.
REWIND_API_VERSION = "1.0"


class RiskClass(StrEnum):
    SAFE = "safe"
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"


_ORDER = {RiskClass.SAFE: 0, RiskClass.REVERSIBLE: 1, RiskClass.IRREVERSIBLE: 2}


def stricter(a: RiskClass, b: RiskClass) -> RiskClass:
    return a if _ORDER[a] >= _ORDER[b] else b


def risk_rank(r: RiskClass) -> int:
    """Numeric strictness of a risk class (higher is stricter)."""
    return _ORDER[r]


class ActionRequest(BaseModel):
    id: str
    session_id: str | None = None
    agent_id: str
    tool: str  # "sql" | "fs" | "git" | "aws_s3" | "aws_iam" | "docker" | "k8s" | "mcp" | ...
    operation: str
    payload: dict[str, Any]
    created_at: datetime


def action_hash(action: ActionRequest) -> str:
    """SHA-256 of the canonical, security-relevant parts of an action.

    Bound into approval votes; any change to tool/operation/payload/session
    produces a different hash and therefore needs a fresh approval.
    """
    canonical = json.dumps(
        {
            "id": action.id,
            "session_id": action.session_id,
            "agent_id": action.agent_id,
            "tool": action.tool,
            "operation": action.operation,
            "payload": action.payload,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Classification(BaseModel):
    action_id: str
    risk: RiskClass
    reasons: list[str]
    rule_ids: list[str] = []  # which policy rules fired (new in Phase 2)
    risk_score: float = Field(ge=0, le=1, default=0.0)


@runtime_checkable
class Classifier(Protocol):
    name: str

    def supports(self, action: ActionRequest) -> bool: ...
    def classify(self, action: ActionRequest) -> Classification: ...


@runtime_checkable
class SnapshotBackend(Protocol):
    name: str

    def supports(self, action: ActionRequest) -> bool: ...
    def capture(self, action: ActionRequest) -> str: ...  # returns snapshot id
    def preview_restore(self, snapshot_id: str) -> dict[str, Any]: ...
    def restore(self, snapshot_id: str, force: bool = False) -> dict[str, Any]: ...


class NotificationEventType(StrEnum):
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECIDED = "approval_decided"
    ACTION_BLOCKED = "action_blocked"
    DELETION_PENDING = "deletion_pending"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    CONFIG_CHANGED = "config_changed"
    AUDIT_CHAIN_FAILURE = "audit_chain_failure"


class NotificationEvent(BaseModel):
    """An event fanned out to notification channels.

    ``untrusted`` holds agent-supplied text (SQL, paths, reasons). Channels must
    escape and truncate it and present it as untrusted. Never put one-time
    approval codes in a NotificationEvent destined for a shared channel.
    """

    id: str
    type: NotificationEventType
    created_at: datetime
    summary: str  # trusted, Rewind-generated text
    severity: str = "info"  # info | warning | critical
    request_id: str | None = None
    session_id: str | None = None
    action_id: str | None = None
    risk: RiskClass | None = None
    link: str | None = None
    untrusted: dict[str, str] = {}
    # Direct-delivery only: id of the single user this event is addressed to.
    recipient_user_id: str | None = None


@runtime_checkable
class ApprovalChannel(Protocol):
    name: str

    def notify(self, event: NotificationEvent) -> None: ...  # must not raise; return normally or log


@runtime_checkable
class AuditLog(Protocol):
    def append(
        self,
        event_type: str,
        data: dict[str, Any],
        actor: str | None = None,
        session_id: str | None = None,
    ) -> str: ...  # returns entry hash

    def verify(self) -> tuple[bool, str | None]: ...  # (ok, first_bad_entry)
    def query(self, **filters: Any) -> list[dict[str, Any]]: ...


@runtime_checkable
class TokenBroker(Protocol):
    def revoke_session(self, session_id: str) -> int: ...  # returns number of tokens revoked
