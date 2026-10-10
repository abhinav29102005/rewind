import sys

path = "src/rewind/web/team_app.py"
with open(path, "r") as f:
    content = f.read()

target = """                        # Make sure destructive git and aws commands run inside demo/ to protect real data
                        if "git" in real_cmd or "rm " in real_cmd or "aws" in real_cmd:
                            real_cmd = f"cd demo && {real_cmd.replace('~/.aws', '.aws')}"
                            
                        subprocess.run(real_cmd, shell=True, timeout=5)"""

replacement = """                        # Make sure destructive git and aws commands run inside demo/ to protect real data
                        if "git" in real_cmd or "aws" in real_cmd:
                            real_cmd = f"cd demo && {real_cmd.replace('~/.aws', '.aws')}"
                            
                        subprocess.run(real_cmd, shell=True, timeout=5)"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w") as f:
        f.write(content)
    print("Success fixing sandbox")
else:
    print("Target not found for fix sandbox")

