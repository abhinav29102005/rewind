"""
MCP (Model Context Protocol) Proxy Adapter.

Acts as a drop-in MCP server that wraps any downstream MCP tool server.
All tool calls pass through Rewind's classification and approval pipeline
before being forwarded to the real server.

This is the primary integration point — the agent connects to Rewind
as if it were the real MCP server, and Rewind forwards approved actions
to the actual server while holding back dangerous ones.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..audit.log import AuditEvent, AuditLog, EventType
from ..classifier.engine import ActionRequest, ActionRisk, ClassificationEngine

if TYPE_CHECKING:
    from ..approval.queue import ApprovalQueue

logger = logging.getLogger(__name__)


@dataclass
class MCPToolCall:
    """Represents an incoming MCP tool call."""

    tool_name: str
    arguments: dict[str, Any]
    call_id: str = ""

    def to_action_request(self) -> ActionRequest:
        """Convert to an ActionRequest for classification."""
        # Build a human-readable command from the tool call
        raw = f"{self.tool_name}({json.dumps(self.arguments, default=str)[:200]})"
        return ActionRequest(
            tool_name=self.tool_name,
            method="call",
            arguments=self.arguments,
            raw_command=raw,
        )


@dataclass
class MCPProxyResult:
    """Result of processing an MCP tool call through the proxy."""

    allowed: bool
    risk: str
    reason: str
    original_call: MCPToolCall
    result: Any = None  # Result from downstream server, if allowed
    approval_request_id: str | None = None

    def to_mcp_response(self) -> dict[str, Any]:
        """Format as an MCP-compatible response."""
        if self.allowed:
            return {
                "content": [{"type": "text", "text": json.dumps(self.result, default=str)}],
                "isError": False,
            }
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"⛔ Action blocked by Rewind.\n"
                            f"Risk: {self.risk}\n"
                            f"Reason: {self.reason}\n"
                            f"This action requires human approval. "
                            f"Request ID: {self.approval_request_id or 'N/A'}"
                        ),
                    }
                ],
                "isError": True,
            }


class MCPProxy:
    """
    MCP proxy that intercepts tool calls and applies Rewind's pipeline.

    The proxy sits between the agent's MCP client and the real MCP server.
    It classifies each tool call and blocks irreversible ones until approved.
    """

    def __init__(
        self,
        classifier: ClassificationEngine,
        audit_log: AuditLog,
        approval_queue: ApprovalQueue | None = None,
    ) -> None:
        self._classifier = classifier
        self._audit = audit_log
        self._approval_queue = approval_queue
        self._downstream_handler: Any = None  # Will be set when connecting to downstream

    def process_tool_call(self, call: MCPToolCall) -> MCPProxyResult:
        """
        Process an incoming MCP tool call through the Rewind pipeline.

        1. Convert to ActionRequest
        2. Classify
        3. Route: safe→allow, reversible→snapshot+allow, irreversible→block
        """
        action = call.to_action_request()

        # Log receipt
        self._audit.log(AuditEvent(
            event_type=EventType.ACTION_RECEIVED,
            data={
                "tool_name": call.tool_name,
                "arguments": {k: str(v)[:100] for k, v in call.arguments.items()},
                "call_id": call.call_id,
            },
        ))

        # Classify
        classification = self._classifier.classify(action)
        self._audit.log(AuditEvent(
            event_type=EventType.ACTION_CLASSIFIED,
            data={
                "tool_name": call.tool_name,
                "risk": classification.risk.value,
                "reason": classification.reason,
                "matched_rule": classification.matched_rule,
            },
        ))

        if classification.risk == ActionRisk.SAFE:
            return MCPProxyResult(
                allowed=True,
                risk="safe",
                reason=classification.reason,
                original_call=call,
            )

        elif classification.risk == ActionRisk.REVERSIBLE:
            # TODO: Create snapshot before allowing (Phase 1D)
            return MCPProxyResult(
                allowed=True,
                risk="reversible",
                reason=classification.reason,
                original_call=call,
            )

        else:  # IRREVERSIBLE
            approval_request_id = None
            if self._approval_queue:
                request = self._approval_queue.enqueue(
                    action=action,
                    classification=classification,
                    approval_code="",
                )
                approval_request_id = request.request_id

            self._audit.log(AuditEvent(
                event_type=EventType.ACTION_BLOCKED,
                data={
                    "tool_name": call.tool_name,
                    "risk": "irreversible",
                    "reason": classification.reason,
                    "approval_request_id": approval_request_id,
                },
            ))

            logger.warning(
                "BLOCKED MCP call: %s (%s)",
                call.tool_name,
                classification.reason,
            )

            return MCPProxyResult(
                allowed=False,
                risk="irreversible",
                reason=classification.reason,
                original_call=call,
                approval_request_id=approval_request_id,
            )
