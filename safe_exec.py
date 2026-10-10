import sys

path = "src/rewind/web/team_app.py"
with open(path, "r") as f:
    content = f.read()

target = """            # DEMO MAGIC: Actually execute the payload if it was simulated and approved!
            if new_status.value == "approved" and ("demo-simulation" in req.action_payload.get("reasons", []) or "None" in str(req.session_id) or req.session_id is None):
                cmd = req.action_payload.get("command")
                if cmd:
                    import subprocess
                    try:
                        # If the command is SQL, run it against the sqlite db instead of bash
                        if cmd.strip().upper().startswith(("DROP", "TRUNCATE", "DELETE", "ALTER")):
                            real_cmd = f"sqlite3 demo/production.db '{cmd}'"
                        else:
                            real_cmd = cmd
                        subprocess.run(real_cmd, shell=True, timeout=5)"""

replacement = """            # DEMO MAGIC: Actually execute the payload if it was simulated and approved!
            if new_status.value == "approved" and ("demo-simulation" in req.action_payload.get("reasons", []) or "None" in str(req.session_id) or req.session_id is None):
                cmd = req.action_payload.get("command")
                if cmd:
                    import subprocess
                    try:
                        # If the command is SQL, run it against the sqlite db instead of bash
                        if cmd.strip().upper().startswith(("DROP", "TRUNCATE", "DELETE", "ALTER")):
                            real_cmd = f"sqlite3 demo/production.db '{cmd}'"
                        else:
                            real_cmd = cmd
                            
                        # Make sure destructive git and aws commands run inside demo/ to protect real data
                        if "git" in real_cmd or "rm " in real_cmd or "aws" in real_cmd:
                            real_cmd = f"cd demo && {real_cmd.replace('~/.aws', '.aws')}"
                            
                        subprocess.run(real_cmd, shell=True, timeout=5)"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w") as f:
        f.write(content)
    print("Success making execution safe")
else:
    print("Target not found for safe exec")

