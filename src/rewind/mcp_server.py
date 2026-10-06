"""FastMCP server bridging the AI agent to the Rewind control plane."""
import logging
import subprocess
from pathlib import Path
from datetime import datetime

from fastmcp import FastMCP

from rewind.config.loader import load_config
from rewind.plugins.loader import load_policy_packs
from rewind.policy.engine import PolicyClassifier
from rewind.team.store import TeamStore
from rewind.team.approvals import ApprovalQueueManager
from rewind.contracts import ActionRequest, RiskClass
from rewind.stubs.audit import StubAuditLog
from rewind.stubs.snapshot import StubSnapshotBackend

logger = logging.getLogger(__name__)

# Load real components
cfg = load_config()
packs = load_policy_packs(cfg)
classifier = PolicyClassifier.from_config(cfg, packs)

data_dir = cfg.data_dir
data_dir.mkdir(parents=True, exist_ok=True)
store = TeamStore(data_dir / "team.db")
audit_log = StubAuditLog()
queue = ApprovalQueueManager(store, audit_log, cfg.security.approval_expiration_mins)
snapshotter = StubSnapshotBackend()

mcp = FastMCP("Rewind Proxy")

@mcp.tool()
async def execute_command(command: str, session_id: str = "agent-session-default") -> str:
    """Execute a shell command, protected by Rewind guardrails.

    Args:
        command: The shell command to execute.
        session_id: The Rewind session ID the agent is operating under.
    """
    action = ActionRequest(
        session_id=session_id,
        agent_id="mcp-agent",
        tool="shell",
        operation="exec",
        payload={"command": command},
        created_at=datetime.now()
    )

    verdict = classifier.classify(action)

    if verdict.risk == RiskClass.IRREVERSIBLE:
        req_id = queue.create_request(session_id, action, rule=verdict.rule, threshold=1)
        
        audit_log.log(
            event_type="action_blocked",
            actor=session_id,
            data=f"Blocked {command}. Req ID: {req_id}"
        )
        return (
            f"囓 ACTION BLOCKED BY REWIND 囓\n"
            f"Risk: {verdict.risk.value}\n"
            f"Reason: {verdict.reason}\n"
            f"An approval request ({req_id}) has been generated in the Control Plane.\n"
            f"You cannot execute this until an Admin unlocks it.\n"
            f"Once approved, you can execute it by calling execute_approved_command."
        )

    elif verdict.risk == RiskClass.REVERSIBLE:
        # Take snapshot
        snap_id = snapshotter.capture(action)
        audit_log.log("snapshot_taken", actor=session_id, data=f"Snapshot ID {snap_id} for {command}")
        
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout
            if result.stderr:
                output += "\nErrorr:\n" + result.stderr
            return f"⚠️ REVERSIBLE ACTION ⚠️\nSnapshot ID: {snap_id}\n\nOutput:\n{output}"
        except Exception as e:
            return f"Error executing command: {str(e)}"

    else:
        # SAFE
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout
            if result.stderr:
                output += "\nErrorr:\n" + result.stderr
            return output or "Command executed successfully with no output."
        except Exception as e:
            return f"Error executing command: {str(e)}"

@mcp.tool()
async def execute_approved_command(request_id: str) -> str:
    """Execute a previously blocked IRREVERSIBLE command after it has been approved.
    
    Args:
        request_id: The REQ-... ID that was returned when the action was blocked.
    """
    req = store.get_approval_request(request_id)
    if not req:
        return f"Error: Request {request_id} not found."
    
    if req.status != "approved":
        return f"Error: Request {request_id} is currently {req.status}. It must be 'approved' to execute."
        
    command = req.action_data.get("command")
    if not command:
        return "Error: Could not extract command from request payload."
        
    audit_log.log("action_executed", actor="mcp-agent", data=f"Executing approved request {request_id}: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout
        if result.stderr:
            output += "\nErrorr:\n" + result.stderr
        
        # Mark as consumed/executed
        with store._get_conn() as conn:
            conn.execute("UPDATE approval_requests SET status = 'executed' WHERE id = ?", (request_id,))
            conn.commit()
            
        return f"✅ APPROVED COMMAND EXECUTED ✅\nOutput:\n{output}"
    except Exception as e:
        return f"Error: executing command: {str(e)}"


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Rewind MCP Server with Full Failsafe Pipeline...")
    mcp.run()

if __name__ == "__main__":
    main()
