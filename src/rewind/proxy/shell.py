"""
Shell Command Proxy.

Intercepts shell commands from agents, classifies them, and applies
the Rewind pipeline (classify → snapshot → approve → execute → log).

Usage:
    rewind exec -- rm -rf /important/data
    rewind exec -- psql -c "DROP TABLE users"
"""

from __future__ import annotations

import logging
import subprocess
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..audit.log import AuditEvent, AuditLog, EventType
from ..classifier.engine import ActionRequest, ActionRisk, ClassificationEngine

if TYPE_CHECKING:
    from ..approval.queue import ApprovalQueue

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of executing (or blocking) a shell command."""

    action_id: str
    command: str
    risk: str
    status: str  # "executed", "blocked", "pending_approval"
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    snapshot_id: str | None = None
    approval_request_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "command": self.command,
            "risk": self.risk,
            "status": self.status,
            "exit_code": self.exit_code,
            "snapshot_id": self.snapshot_id,
            "approval_request_id": self.approval_request_id,
        }


class ShellProxy:
    """
    Intercepts and guards shell commands.

    Flow:
    1. Classify the command
    2. If safe → execute + log
    3. If reversible → snapshot → execute + log
    4. If irreversible → hold for approval
    """

    def __init__(
        self,
        classifier: ClassificationEngine,
        audit_log: AuditLog,
        approval_queue: ApprovalQueue | None = None,
        working_dir: str | None = None,
    ) -> None:
        self._classifier = classifier
        self._audit = audit_log
        self._approval_queue = approval_queue
        self._working_dir = working_dir

    def execute(self, command: str, timeout: int = 60) -> ExecutionResult:
        """
        Process a shell command through the Rewind pipeline.
        """
        action_id = f"act_{uuid.uuid4().hex[:12]}"

        # Build action request
        action = ActionRequest(
            tool_name="shell",
            method="exec",
            raw_command=command,
        )

        # Log receipt
        self._audit.log(AuditEvent(
            event_type=EventType.ACTION_RECEIVED,
            data={"action_id": action_id, "command": command},
        ))

        # Classify
        classification = self._classifier.classify(action)
        self._audit.log(AuditEvent(
            event_type=EventType.ACTION_CLASSIFIED,
            data={
                "action_id": action_id,
                "risk": classification.risk.value,
                "reason": classification.reason,
                "matched_rule": classification.matched_rule,
            },
        ))

        # Route based on risk
        if classification.risk == ActionRisk.SAFE:
            return self._execute_command(action_id, command, timeout)

        elif classification.risk == ActionRisk.REVERSIBLE:
            # TODO: Create snapshot before execution (Phase 1D integration)
            return self._execute_command(action_id, command, timeout)

        elif classification.risk == ActionRisk.IRREVERSIBLE:
            return self._block_for_approval(action_id, command, action, classification)

        # Should never reach here due to fail-safe classification
        return self._block_for_approval(action_id, command, action, classification)

    def _execute_command(
        self, action_id: str, command: str, timeout: int
    ) -> ExecutionResult:
        """Execute a command and log the result."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._working_dir,
            )
            exec_result = ExecutionResult(
                action_id=action_id,
                command=command,
                risk="safe",
                status="executed",
                exit_code=result.returncode,
                stdout=result.stdout[:4096],
                stderr=result.stderr[:4096],
            )
        except subprocess.TimeoutExpired:
            exec_result = ExecutionResult(
                action_id=action_id,
                command=command,
                risk="safe",
                status="timeout",
                exit_code=-1,
                stderr="Command timed out",
            )

        self._audit.log(AuditEvent(
            event_type=EventType.ACTION_EXECUTED,
            data=exec_result.to_dict(),
        ))
        return exec_result

    def _block_for_approval(
        self,
        action_id: str,
        command: str,
        action: ActionRequest,
        classification: Any,
    ) -> ExecutionResult:
        """Block an irreversible action and queue it for approval."""
        logger.warning(
            "BLOCKED irreversible action %s: %s (reason: %s)",
            action_id,
            command[:80],
            classification.reason,
        )

        self._audit.log(AuditEvent(
            event_type=EventType.ACTION_BLOCKED,
            data={
                "action_id": action_id,
                "command": command,
                "reason": classification.reason,
            },
        ))

        approval_request_id = None
        if self._approval_queue:
            request = self._approval_queue.enqueue(
                action=action,
                classification=classification,
                approval_code="",  # Will be set by the approval flow
            )
            approval_request_id = request.request_id
            self._audit.log(AuditEvent(
                event_type=EventType.APPROVAL_REQUESTED,
                data={
                    "action_id": action_id,
                    "request_id": request.request_id,
                },
            ))

        return ExecutionResult(
            action_id=action_id,
            command=command,
            risk="irreversible",
            status="blocked",
            approval_request_id=approval_request_id,
        )
