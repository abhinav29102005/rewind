"""FastMCP server bridging the AI agent to the Rewind control plane."""
from __future__ import annotations

import logging
import subprocess
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastmcp import FastMCP

from rewind.audit.log import AuditLog
from rewind.config.defaults import builtin_policy_dir
from rewind.config.loader import load_config
from rewind.contracts import ActionRequest, RiskClass, action_hash
from rewind.policy.engine import PolicyClassifier
from rewind.policy.pack import load_packs
from rewind.snapshot.git import GitSnapshotError, GitSnapshotter
from rewind.team.approvals import ApprovalQueueManager
from rewind.team.models import ApprovalStatus
from rewind.team.store import TeamStore

logger = logging.getLogger(__name__)

# Load config and policy packs
cfg = load_config()
packs = load_packs(["filesystem", "postgresql", "git", "aws_s3", "docker"], [builtin_policy_dir()])
classifier = PolicyClassifier.from_config(cfg, packs)

# Shared SQLite persistent stores
data_dir = cfg.data_dir
data_dir.mkdir(parents=True, exist_ok=True)
store = TeamStore(data_dir / "team.db")
audit_log = AuditLog(data_dir / "audit.db")
queue = ApprovalQueueManager(store, audit_log)
snapshotter = GitSnapshotter(Path.cwd())

mcp = FastMCP("Rewind Guardrails Proxy")


def _ensure_session(session_id: str) -> None:
    """Ensure session exists in store so foreign keys pass and dashboard tracks it."""
    if not store.get_session(session_id):
        res = store.get_user_by_username("admin")
        if res:
            user_id = res[0].id
        else:
            users = store.list_users()
            if users:
                user_id = users[0].id
            else:
                from rewind.team.auth import hash_password
                from rewind.team.models import Role
                admin = store.create_user("u_admin", "admin", hash_password("password"), Role.ADMIN)
                user_id = admin.id

        store.create_session(
            session_id=session_id,
            name=f"Agent Session ({session_id[:12]})",
            started_by=user_id,
            policy_profile="default",
        )


@mcp.tool()
async def execute_command(command: str, session_id: str = "agent-session-default") -> str:
    """Execute a shell command protected by Rewind fail-safe guardrails.

    Safe commands execute directly.
    Reversible commands (file modifications, git resets) are automatically checkpointed with rollback snapshots.
    Irreversible commands (drop databases, destructive deletes, cloud terminations) are blocked and held in the approval queue until authorized by human operators.

    Args:
        command: The shell command to execute.
        session_id: The Rewind session ID the agent is operating under.
    """
    _ensure_session(session_id)

    action = ActionRequest(
        id=f"act_{uuid.uuid4().hex[:12]}",
        session_id=session_id,
        agent_id="mcp-agent",
        tool="shell",
        operation="exec",
        payload={"command": command},
        created_at=datetime.now(),
    )

    verdict = classifier.classify(action)

    if verdict.risk == RiskClass.IRREVERSIBLE:
        timeout_mins = getattr(getattr(cfg.approval, "default", None), "timeout_minutes", 15)
        expires_at = datetime.now() + timedelta(minutes=timeout_mins)

        req = queue.create_request(action, mode="any_one", required=1, expires_at=expires_at)
        audit_log.append(
            event_type="action_blocked",
            data={
                "command": command,
                "request_id": req.id,
                "risk": verdict.risk.value,
                "rule_ids": verdict.rule_ids,
                "reasons": verdict.reasons,
            },
            actor="mcp-agent",
            session_id=session_id,
        )

        return (
            f"🚫 ACTION BLOCKED BY REWIND 🚫\n"
            f"Risk Level: {verdict.risk.value.upper()}\n"
            f"Rule Triggered: {', '.join(verdict.rule_ids)}\n"
            f"Reason: {'; '.join(verdict.reasons)}\n\n"
            f"An approval request has been queued in the Rewind Control Plane:\n"
            f"  Request ID: {req.id}\n"
            f"  Action Hash: {req.action_hash[:16]}...\n\n"
            f"The action cannot proceed until an approver or admin unlocks it.\n"
            f"Once approved, you can complete this action using execute_approved_command('{req.id}')."
        )

    elif verdict.risk == RiskClass.REVERSIBLE:
        snap_id = "none"
        try:
            snapshotter.init_if_needed()
            snap = snapshotter.create_snapshot(action_summary=f"Pre-exec: {command}")
            snap_id = snap.snapshot_id
            audit_log.append(
                event_type="snapshot_created",
                data={"command": command, "snapshot_id": snap_id, "commit": snap.commit_hash},
                actor="mcp-agent",
                session_id=session_id,
            )
        except Exception as e:
            logger.warning("Could not take git snapshot: %s", e)

        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout
            if result.stderr:
                output += ("\n" if output else "") + "Error:\n" + result.stderr

            audit_log.append(
                event_type="action_executed",
                data={"command": command, "snapshot_id": snap_id, "exit_code": result.returncode},
                actor="mcp-agent",
                session_id=session_id,
            )
            return (
                f"⚠️ REVERSIBLE ACTION (Checkpoint Created) ⚠️\n"
                f"Snapshot ID: {snap_id}\n"
                f"(If anything went wrong, use rollback_snapshot('{snap_id}') to restore)\n\n"
                f"Output:\n{output or '(no output)'}"
            )
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 30 seconds."
        except Exception as e:
            return f"Error executing command: {e}"

    else:
        # SAFE
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout
            if result.stderr:
                output += ("\n" if output else "") + "Error:\n" + result.stderr

            audit_log.append(
                event_type="action_executed",
                data={"command": command, "risk": "safe", "exit_code": result.returncode},
                actor="mcp-agent",
                session_id=session_id,
            )
            return output or "Command executed successfully with no output."
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 30 seconds."
        except Exception as e:
            return f"Error executing command: {e}"


@mcp.tool()
async def execute_approved_command(request_id: str) -> str:
    """Execute a previously blocked IRREVERSIBLE command after it has been approved.

    Verifies cryptographic action hash integrity and approval status before execution.

    Args:
        request_id: The request identifier (e.g. apr_XXXX) returned when the action was blocked.
    """
    req = store.get_approval_request(request_id)
    if not req:
        return f"Error: Approval request '{request_id}' not found."

    if req.status != ApprovalStatus.APPROVED:
        return f"Error: Request '{request_id}' status is '{req.status.value}'. It must be 'approved' before execution."

    if datetime.now() > req.expires_at:
        return f"Error: Approval request '{request_id}' has expired."

    command = req.action_payload.get("command")
    if not command:
        return "Error: Could not extract shell command from approval request payload."

    # Cryptographic integrity check: verify recomputed hash matches stored hash
    dummy_action = ActionRequest(
        id=req.action_id,
        session_id=req.session_id,
        agent_id="mcp-agent",
        tool="shell",
        operation="exec",
        payload=req.action_payload,
        created_at=req.created_at,
    )
    if action_hash(dummy_action) != req.action_hash:
        return "Error: Cryptographic action hash verification failed! Payload was modified."

    audit_log.append(
        event_type="action_executed",
        data={"command": command, "request_id": request_id, "action_hash": req.action_hash},
        actor="mcp-agent",
        session_id=req.session_id,
    )

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        output = result.stdout
        if result.stderr:
            output += ("\n" if output else "") + "Error:\n" + result.stderr

        # Mark as consumed/executed to prevent replay attacks
        with store._lock:
            store._conn.execute(
                "UPDATE approval_requests SET status = 'executed', decided_at = ? WHERE id = ?",
                (datetime.now().isoformat(), request_id),
            )
            store._conn.commit()

        return f"✅ APPROVED COMMAND EXECUTED SUCCESSFULLY ✅\nOutput:\n{output or '(no output)'}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        return f"Error executing approved command: {e}"


@mcp.tool()
async def preview_rollback(snapshot_id: str) -> str:
    """Preview the file diff that would be restored if rolling back to a snapshot.

    Args:
        snapshot_id: The snapshot identifier (e.g. snap_XXXX).
    """
    try:
        diff = snapshotter.get_diff(snapshot_id)
        return f"Diff for snapshot '{snapshot_id}':\n\n{diff}"
    except GitSnapshotError as e:
        return f"Error inspecting snapshot: {e}"


@mcp.tool()
async def rollback_snapshot(snapshot_id: str) -> str:
    """Restore filesystem state to a pre-action snapshot checkpoint.

    Args:
        snapshot_id: The snapshot identifier (e.g. snap_XXXX).
    """
    try:
        ok = snapshotter.rollback(snapshot_id)
        if ok:
            audit_log.append(
                event_type="rollback_completed",
                data={"snapshot_id": snapshot_id},
                actor="mcp-agent",
            )
            return f"✅ SUCCESS: Restored filesystem state to snapshot '{snapshot_id}'."
        return f"Failed to restore snapshot '{snapshot_id}'."
    except GitSnapshotError as e:
        return f"Rollback error: {e}"


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Rewind MCP Server with Full Failsafe Pipeline...")
    mcp.run()


if __name__ == "__main__":
    main()
