import sys

path = "src/rewind/web/team_app.py"
with open(path, "r") as f:
    content = f.read()

target = """    @app.post("/api/v1/approvals/simulate")"""

replacement = """    @app.post("/api/v1/demo/reset")
    def reset_demo_files_api(user=Depends(require_user)):
        import subprocess
        try:
            subprocess.run('mkdir -p demo && sqlite3 demo/production.db "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT); CREATE TABLE transactions (id INTEGER PRIMARY KEY, amount REAL);" && echo -e "id,name,role\\n1,Alice,Admin\\n2,Bob,User" > demo/important_data.csv && echo -e "{\\n  \\"database_url\\": \\"sqlite:///production.db\\",\\n  \\"secret_key\\": \\"super-secret-key-do-not-leak\\",\\n  \\"debug\\": false\\n}" > demo/config.json', shell=True)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @app.post("/api/v1/approvals/simulate")"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w") as f:
        f.write(content)
    print("Success team_app")
else:
    print("Target not found team_app")

