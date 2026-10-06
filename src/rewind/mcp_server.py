import logging

from fastmcp import FastMCP

from rewind.audit.log import AuditLog
from rewind.classifier.engine import ActionRequest, ActionRisk, ClassificationEngine
from rewind.classifier.rules import RuleClassifier

logger = logging.getLogger(__name__)

# Initialize Rewind components
classifier = RuleClassifier()
engine = ClassificationEngine([classifier])
audit_log = AuditLog("rewind_audit.db")

mcp = FastMCP("Rewind Proxy")

@mcp.tool()
async def execute_command(command: str) -> str:
    """Execute a shell command, protected by Rewind guardrails.

    Args:
        command: The shell command to execute.
    """
    action = ActionRequest(
        tool_name="shell",
        method="exec",
        raw_command=command,
        arguments={"command": command}
    )

    classification = engine.classify(action)

    if classification.risk == ActionRisk.IRREVERSIBLE:
        return (
            f"⛔ ACTION BLOCKED BY REWIND ⛔\n"
            f"Risk: {classification.risk.value}\n"
            f"Reason: {classification.reason}\n"
            f"Matched Rule: {classification.matched_rule}\n\n"
            f"This action requires human approval before it can be executed."
        )

    elif classification.risk == ActionRisk.REVERSIBLE:
        return (
            f"⚠️ REVERSIBLE ACTION ⚠️\n"
            f"Rewind would take a snapshot here, then execute: {command}\n"
            f"(Snapshotting not fully integrated in this demo)"
        )

    else:
        # SAFE
        import subprocess
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout
            if result.stderr:
                output += "\nErrors:\n" + result.stderr
            return output or "Command executed successfully with no output."
        except Exception as e:
            return f"Error executing command: {str(e)}"

def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Rewind MCP Server...")
    mcp.run()

if __name__ == "__main__":
    main()
