"""Shared approval queues supporting any-one and N-of-M voting.

Enforces:
- Action-hash binding (approvals cannot be reused if action modified).
- Separation of duties (session starter cannot vote on own actions).
- Distinct approvers (no double voting).
- Exactly-once execution via atomic transactions.
- Auto-expiration.
"""

from __future__ import annotations

import contextlib
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from ..contracts import ActionRequest, AuditLog, action_hash
from ..stubs.approval_codes import StubApprovalCodes
from .models import (
    ApprovalRequest,
    ApprovalStatus,
    Role,
    User,
    VoteDecision,
)

if TYPE_CHECKING:
    from .store import TeamStore

logger = logging.getLogger(__name__)


class ApprovalError(Exception):
    """Approval request or voting error."""


class ApprovalQueueManager:
    """Manages multi-user approval queue with N-of-M consensus and strict checks."""

    def __init__(
        self,
        store: TeamStore,
        audit_log: AuditLog | None = None,
        codes: StubApprovalCodes | None = None,
    ) -> None:
        self.store = store
        self.audit_log = audit_log
        self.codes = codes or StubApprovalCodes()

    def create_request(
        self,
        action: ActionRequest,
        mode: str,
        required: int,
        expires_at: datetime,
    ) -> ApprovalRequest:
        req_id = "apr_" + uuid.uuid4().hex[:12]
        h = action_hash(action)
        req = self.store.create_approval_request(
            request_id=req_id,
            action_id=action.id,
            session_id=action.session_id,
            action_hash=h,
            mode=mode,
            required=required,
            expires_at=expires_at,
        )
        if self.audit_log:
            self.audit_log.append(
                "approval_requested",
                {"request_id": req_id, "action_id": action.id, "mode": mode, "required": required},
                session_id=action.session_id,
            )
        return req

    def issue_code_for_approver(self, request_id: str, approver_id: str) -> str:
        """Issue a private, one-time code for a specific approver."""
        return self.codes.issue(request_id, approver_id)

    def vote(
        self,
        request_id: str,
        approver: User,
        decision: VoteDecision,
        current_action: ActionRequest,
        one_time_code: str | None = None,
        separation_of_duties: bool = True,
        veto: bool = True,
    ) -> tuple[ApprovalStatus, str]:
        """Cast a vote on an approval request inside an atomic transaction.

        Returns (new_status, reason).
        """
        # 1. Role eligibility
        if approver.role not in (Role.ADMIN, Role.APPROVER):
            raise ApprovalError(f"User {approver.username} with role {approver.role.value} is not eligible to vote")

        # 2. Recompute action hash and verify exact action binding
        current_hash = action_hash(current_action)

        # 3. One-time code verification if provided
        if one_time_code:
            valid_code = self.codes.consume(request_id, approver.id, one_time_code)
            if not valid_code:
                raise ApprovalError("Invalid, expired, or already-consumed one-time approval code")

        now = datetime.now()
        vote_id = "v_" + uuid.uuid4().hex[:12]

        with self.store._lock:
            cur = self.store._conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            try:
                # Fetch fresh request
                cur.execute("SELECT * FROM approval_requests WHERE id = ?", (request_id,))
                req_row = cur.fetchone()
                if not req_row:
                    raise ApprovalError(f"Approval request {request_id} not found")

                req_status = ApprovalStatus(req_row["status"])
                req_expires = datetime.fromisoformat(req_row["expires_at"])
                expected_hash = req_row["action_hash"]
                mode = req_row["mode"]
                required = req_row["required"]
                session_id = req_row["session_id"]

                # Expiry check
                if now > req_expires or req_status == ApprovalStatus.EXPIRED:
                    cur.execute(
                        "UPDATE approval_requests SET status = ?, decided_at = ? WHERE id = ?",
                        (ApprovalStatus.EXPIRED.value, now.isoformat(), request_id),
                    )
                    cur.execute("COMMIT")
                    if self.audit_log:
                        self.audit_log.append("approval_expired", {"request_id": request_id}, session_id=session_id)
                    raise ApprovalError(f"Approval request {request_id} has expired")

                if req_status != ApprovalStatus.PENDING:
                    cur.execute("COMMIT")
                    raise ApprovalError(f"Approval request {request_id} has already been {req_status.value}")

                # Action hash binding
                if current_hash != expected_hash:
                    cur.execute("COMMIT")
                    raise ApprovalError("Action has been modified since approval request was created; vote rejected")

                # Separation of duties: session starter cannot vote
                if separation_of_duties and session_id:
                    cur.execute("SELECT started_by FROM sessions WHERE id = ?", (session_id,))
                    s_row = cur.fetchone()
                    if s_row and s_row["started_by"] == approver.id:
                        cur.execute("COMMIT")
                        raise ApprovalError("Separation of duties: session initiator cannot cast a vote on actions in this session")

                # Insert vote (UNIQUE constraint prevents duplicate votes)
                try:
                    cur.execute(
                        """INSERT INTO approval_votes (id, request_id, approver_id, decision, action_hash, voted_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (vote_id, request_id, approver.id, decision.value, current_hash, now.isoformat()),
                    )
                except sqlite3.IntegrityError as e:
                    cur.execute("COMMIT")
                    raise ApprovalError(f"User {approver.username} has already voted on request {request_id}") from e

                # Determine new status
                cur.execute("SELECT approver_id, decision FROM approval_votes WHERE request_id = ?", (request_id,))
                votes = cur.fetchall()

                new_status = ApprovalStatus.PENDING

                if decision == VoteDecision.DENY and veto:
                    new_status = ApprovalStatus.DENIED
                else:
                    approvals = [v for v in votes if v["decision"] == VoteDecision.APPROVE.value]
                    if mode == "any_one" and len(approvals) >= 1 or mode == "n_of_m" and len(approvals) >= required:
                        new_status = ApprovalStatus.APPROVED

                if new_status != ApprovalStatus.PENDING:
                    cur.execute(
                        "UPDATE approval_requests SET status = ?, decided_at = ? WHERE id = ?",
                        (new_status.value, now.isoformat(), request_id),
                    )

                cur.execute("COMMIT")

                if self.audit_log:
                    self.audit_log.append(
                        "approval_voted",
                        {
                            "request_id": request_id,
                            "approver_id": approver.id,
                            "decision": decision.value,
                            "result_status": new_status.value,
                        },
                        actor=approver.id,
                        session_id=session_id,
                    )

                return new_status, f"Vote recorded, request is now {new_status.value}"

            except Exception:
                if self.store._conn.in_transaction:
                    with contextlib.suppress(Exception):
                        cur.execute("ROLLBACK")
                raise
