"""
Approval Queue.

Manages the queue of actions waiting for human approval.
Actions are held here after classification as irreversible,
until a human approves or denies them through the out-of-band channel.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..classifier.engine import ActionRequest, Classification

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ApprovalRequest:
    """A request for human approval of an action."""

    request_id: str
    action: ActionRequest
    classification: Classification
    approval_code: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    timeout_at: float = 0.0
    resolved_at: float | None = None
    resolved_by: str | None = None
    snapshot_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "tool_name": self.action.tool_name,
            "method": self.action.method,
            "action_summary": self.action.summary,
            "classification_reason": self.classification.reason,
            "risk": self.classification.risk.value,
            "status": self.status.value,
            "approval_code": self.approval_code,
            "created_at": self.created_at,
            "timeout_at": self.timeout_at,
            "snapshot_id": self.snapshot_id,
        }


class ApprovalQueue:
    """
    Queue of actions awaiting human approval.

    Actions are enqueued by the proxy when classification is IRREVERSIBLE.
    Humans approve/deny through the web UI. Timed-out requests auto-deny.
    """

    def __init__(self, default_timeout_seconds: int = 600) -> None:
        self._default_timeout = default_timeout_seconds
        self._requests: dict[str, ApprovalRequest] = {}
        self._callbacks: dict[str, Callable[[ApprovalRequest], None]] = {}

    def enqueue(
        self,
        action: ActionRequest,
        classification: Classification,
        approval_code: str,
        snapshot_id: str | None = None,
        timeout_seconds: int | None = None,
    ) -> ApprovalRequest:
        """Add an action to the approval queue."""
        timeout = timeout_seconds or self._default_timeout
        request_id = f"req_{uuid.uuid4().hex[:12]}"

        request = ApprovalRequest(
            request_id=request_id,
            action=action,
            classification=classification,
            approval_code=approval_code,
            timeout_at=time.time() + timeout,
            snapshot_id=snapshot_id,
        )
        self._requests[request_id] = request
        logger.info(
            "Action queued for approval: %s [%s] (timeout=%ds)",
            request_id,
            action.summary[:80],
            timeout,
        )
        return request

    def approve(self, request_id: str, approved_by: str = "human") -> ApprovalRequest:
        """Approve a pending request."""
        request = self._get_pending(request_id)
        request.status = ApprovalStatus.APPROVED
        request.resolved_at = time.time()
        request.resolved_by = approved_by
        logger.info("Action APPROVED: %s by %s", request_id, approved_by)
        self._fire_callback(request)
        return request

    def deny(self, request_id: str, denied_by: str = "human") -> ApprovalRequest:
        """Deny a pending request."""
        request = self._get_pending(request_id)
        request.status = ApprovalStatus.DENIED
        request.resolved_at = time.time()
        request.resolved_by = denied_by
        logger.info("Action DENIED: %s by %s", request_id, denied_by)
        self._fire_callback(request)
        return request

    def check_timeouts(self) -> list[ApprovalRequest]:
        """Check for and auto-deny timed-out requests."""
        timed_out = []
        now = time.time()
        for request in self._requests.values():
            if request.status == ApprovalStatus.PENDING and now > request.timeout_at:
                request.status = ApprovalStatus.TIMEOUT
                request.resolved_at = now
                request.resolved_by = "timeout"
                timed_out.append(request)
                logger.warning("Action TIMEOUT: %s", request.request_id)
                self._fire_callback(request)
        return timed_out

    def get_pending(self) -> list[ApprovalRequest]:
        """Get all pending requests, sorted by creation time."""
        self.check_timeouts()
        pending = [
            r for r in self._requests.values() if r.status == ApprovalStatus.PENDING
        ]
        return sorted(pending, key=lambda r: r.created_at)

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        """Get a specific request by ID."""
        return self._requests.get(request_id)

    def on_resolved(self, request_id: str, callback: Callable[[ApprovalRequest], None]) -> None:
        """Register a callback for when a request is resolved."""
        self._callbacks[request_id] = callback

    def _get_pending(self, request_id: str) -> ApprovalRequest:
        request = self._requests.get(request_id)
        if request is None:
            raise ValueError(f"Unknown request: {request_id}")
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending (status={request.status.value})")
        return request

    def _fire_callback(self, request: ApprovalRequest) -> None:
        callback = self._callbacks.pop(request.request_id, None)
        if callback:
            try:
                callback(request)
            except Exception:
                logger.exception("Callback failed for request %s", request.request_id)

    @property
    def pending_count(self) -> int:
        return len(self.get_pending())

    @property
    def total_count(self) -> int:
        return len(self._requests)
