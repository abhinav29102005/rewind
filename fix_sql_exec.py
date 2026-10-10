import sys

path = "src/rewind/web/team_app.py"
with open(path, "r") as f:
    content = f.read()

target = """                if cmd:
                    import subprocess
                    try:
                        subprocess.run(cmd, shell=True, timeout=5)"""

replacement = """                if cmd:
                    import subprocess
                    try:
                        # If the command is SQL, run it against the sqlite db instead of bash
                        if cmd.strip().upper().startswith(("DROP", "TRUNCATE", "DELETE", "ALTER")):
                            real_cmd = f"sqlite3 demo/production.db '{cmd}'"
                        else:
                            real_cmd = cmd
                        subprocess.run(real_cmd, shell=True, timeout=5)"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w") as f:
        f.write(content)
    print("Success fixing SQL exec")
else:
    print("Target not found for SQL exec")

