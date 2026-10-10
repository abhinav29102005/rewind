import sys

path = "src/rewind/web/team_app.py"
with open(path, "r") as f:
    content = f.read()

target = """            return {"request_id": request_id, "status": new_status.value, "message": msg}"""

replacement = """            
            # DEMO MAGIC: Actually execute the payload if it was simulated and approved!
            if new_status.value == "approved" and ("demo-simulation" in req.action_payload.get("reasons", []) or "None" in str(req.session_id) or req.session_id is None):
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
            
            return {"request_id": request_id, "status": new_status.value, "message": msg}"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w") as f:
        f.write(content)
    print("Success")
else:
    print("Target not found.")
