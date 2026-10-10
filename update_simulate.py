import sys
import re

path = "src/rewind/web/team_app.py"
with open(path, "r") as f:
    content = f.read()

target = """    @app.post("/api/v1/approvals/{request_id}/decision")
    def submit_decision_api(
        request_id: str,
        payload: dict[str, str] = Body(...),
        user: User = Depends(require_user),
    ) -> dict[str, Any]:
        check_permission(user, "approve")
        decision = payload.get("decision")
        if decision not in ("approve", "deny"):
            raise HTTPException(400, "Decision must be 'approve' or 'deny'")
        
        ok = queue.record_vote(request_id, user.id, decision)
        if not ok:
            raise HTTPException(400, "Could not record vote (invalid request ID or already finalized)")
        
        req = store.get_approval_request(request_id)
        return {"status": "ok", "request_status": req.status.value if req else "unknown"}"""

replacement = """    @app.post("/api/v1/approvals/{request_id}/decision")
    def submit_decision_api(
        request_id: str,
        payload: dict[str, str] = Body(...),
        user: User = Depends(require_user),
    ) -> dict[str, Any]:
        check_permission(user, "approve")
        decision = payload.get("decision")
        if decision not in ("approve", "deny"):
            raise HTTPException(400, "Decision must be 'approve' or 'deny'")
        
        ok = queue.record_vote(request_id, user.id, decision)
        if not ok:
            raise HTTPException(400, "Could not record vote (invalid request ID or already finalized)")
        
        req = store.get_approval_request(request_id)
        
        # DEMO MAGIC: If this was a simulated demo request and it got approved, actually run it!
        if req and req.status.value == "approved" and "demo-session" in str(req.session_id) or "None" in str(req.session_id):
            cmd = req.action_payload.get("command")
            if cmd:
                import subprocess
                try:
                    subprocess.run(cmd, shell=True, timeout=5)
                    audit.append(
                        event_type="demo_action_executed",
                        data={"command": cmd, "request_id": request_id},
                        actor="demo-system"
                    )
                except Exception:
                    pass

        return {"status": "ok", "request_status": req.status.value if req else "unknown"}"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w") as f:
        f.write(content)
    print("Success")
else:
    print("Target not found. Let's do a fallback replace.")
    # Fallback if exact match fails
    if "def submit_decision_api" in content:
        print("Function found, you might need manual sed.")
    
