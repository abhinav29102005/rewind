import sys
import os

path = "src/rewind/web/team_app.py"
with open(path, "r") as f:
    content = f.read()

target = """    @app.post("/api/v1/approvals/{request_id}/decision")"""

replacement = """    @app.post("/api/v1/approvals/simulate")
    def simulate_approval_api(
        payload: dict[str, Any] = Body(...),
        user: User = Depends(require_user),
    ) -> dict[str, Any]:
        check_permission(user, "approve")
        command = payload.get("command", "rm -rf /")
        
        # Create a dummy action request simulating an AI agent
        import uuid
        from rewind.contracts import ActionRequest
        from datetime import datetime
        from datetime import timedelta
        
        action = ActionRequest(
            id=f"act_{uuid.uuid4().hex[:12]}",
            session_id="demo-session",
            agent_id="mcp-agent",
            tool="shell",
            operation="exec",
            payload={"command": command},
            created_at=datetime.now(),
        )
        
        timeout_mins = getattr(getattr(config.approval, "default", None), "timeout_minutes", 15)
        expires_at = datetime.now() + timedelta(minutes=timeout_mins)
        req = queue.create_request(action, mode="any_one", required=1, expires_at=expires_at)
        
        audit.append(
            event_type="action_blocked",
            data={
                "command": command,
                "request_id": req.id,
                "risk": "irreversible",
                "rule_ids": ["demo-simulation"],
                "reasons": ["Simulated from VS Code extension for demo purposes"],
            },
            actor="demo-user",
        )
        return {"status": "created", "request_id": req.id}

    @app.post("/api/v1/approvals/{request_id}/decision")"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w") as f:
        f.write(content)
    print("Success")
else:
    print("Target not found")
